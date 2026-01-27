"""
Extended / Unscented Kalman filter orbit refinement for UCTP Lab.

Processes angular observations sequentially to refine the state and
produce a covariance estimate.  Uses two-body dynamics as the state
transition model.
"""

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..config import RefinementConfig
from ..iod.base import IODResult
from .base import AbstractRefiner


class EKFRefiner(AbstractRefiner):
    """
    Extended Kalman filter (first-order linearised) refinement.

    State: [x, y, z, vx, vy, vz]  (km, km/s)
    Measurements: [RA, Dec]  (radians)
    """

    MU = 398600.4418  # km^3/s^2

    def refine(
        self, initial_orbit: IODResult, observations: pd.DataFrame
    ) -> Optional[IODResult]:
        if len(observations) < 2:
            return None
        try:
            return self._run_filter(initial_orbit, observations)
        except Exception as e:
            logger.warning(f"EKF refinement failed: {e}")
            return None

    def _run_filter(
        self, initial_orbit: IODResult, observations: pd.DataFrame
    ) -> Optional[IODResult]:
        obs = observations.sort_values("ob_time").reset_index(drop=True)
        epoch = pd.to_datetime(initial_orbit.epoch)

        x = initial_orbit.state.copy()

        # Initial covariance
        P = np.diag([100.0, 100.0, 100.0, 0.1, 0.1, 0.1])

        # Process noise
        q_pos = self.config.process_noise_pos_km ** 2
        q_vel = self.config.process_noise_vel_km_s ** 2
        Q_base = np.diag([q_pos, q_pos, q_pos, q_vel, q_vel, q_vel])

        # Measurement noise (arcsecond-level)
        sigma_ra = np.deg2rad(5.0 / 3600.0)   # 5 arcsec
        sigma_dec = np.deg2rad(5.0 / 3600.0)
        R = np.diag([sigma_ra ** 2, sigma_dec ** 2])

        prev_time = epoch

        for _, row in obs.iterrows():
            cur_time = pd.to_datetime(row["ob_time"])
            dt = (cur_time - prev_time).total_seconds()

            # --- Predict ---
            if abs(dt) > 0.01:
                F = self._state_transition_jacobian(x, dt)
                x = self._propagate_twobody(x, dt)
                if x is None:
                    return None
                Q = Q_base * abs(dt)
                P = F @ P @ F.T + Q
            prev_time = cur_time

            # --- Update ---
            ra_obs = np.deg2rad(float(row["ra"]))
            dec_obs = np.deg2rad(float(row["declination"]))
            z_meas = np.array([ra_obs, dec_obs])

            z_pred, H = self._measurement_and_jacobian(x)
            y_innov = z_meas - z_pred

            # Wrap RA innovation to [-pi, pi]
            y_innov[0] = (y_innov[0] + np.pi) % (2 * np.pi) - np.pi

            S = H @ P @ H.T + R
            try:
                K = P @ H.T @ np.linalg.inv(S)
            except np.linalg.LinAlgError:
                continue

            x = x + K @ y_innov
            P = (np.eye(6) - K @ H) @ P

        # Build covariance upper triangle (21 elements)
        cov_upper = []
        for i in range(6):
            for j in range(i, 6):
                cov_upper.append(float(P[i, j]))

        # Compute residual using final state
        rms = self._compute_rms(x, epoch, obs)

        return IODResult(
            state=x,
            epoch=initial_orbit.epoch,
            observation_ids=initial_orbit.observation_ids,
            covariance=cov_upper,
            method="ekf",
            iterations=len(obs),
            residual=rms,
        )

    def _propagate_twobody(self, state: np.ndarray, dt: float) -> Optional[np.ndarray]:
        r = state[:3].copy()
        v = state[3:].copy()
        n_steps = max(int(abs(dt) / 10.0), 1)
        h = dt / n_steps

        for _ in range(n_steps):
            r_mag = np.linalg.norm(r)
            if r_mag < 10.0:
                return None
            a = -self.MU / (r_mag ** 3) * r
            v = v + a * h
            r = r + v * h

        return np.concatenate([r, v])

    def _state_transition_jacobian(self, state: np.ndarray, dt: float) -> np.ndarray:
        """Numerical Jacobian of the state transition via finite differences."""
        F = np.eye(6)
        eps = 1e-4

        for j in range(6):
            s_plus = state.copy()
            s_minus = state.copy()
            delta = eps if j < 3 else eps * 1e-3
            s_plus[j] += delta
            s_minus[j] -= delta

            sp = self._propagate_twobody(s_plus, dt)
            sm = self._propagate_twobody(s_minus, dt)
            if sp is not None and sm is not None:
                F[:, j] = (sp - sm) / (2 * delta)

        return F

    @staticmethod
    def _measurement_and_jacobian(state: np.ndarray):
        """Compute predicted [RA, Dec] in radians and the 2x6 Jacobian H."""
        x, y, z = state[:3]
        r = np.sqrt(x ** 2 + y ** 2 + z ** 2)
        rxy = np.sqrt(x ** 2 + y ** 2)

        ra = np.arctan2(y, x) % (2 * np.pi)
        dec = np.arcsin(z / r)

        z_pred = np.array([ra, dec])

        H = np.zeros((2, 6))
        # d(RA)/d(x,y,z)
        if rxy > 1e-10:
            H[0, 0] = -y / (rxy ** 2)
            H[0, 1] = x / (rxy ** 2)
        # d(Dec)/d(x,y,z)
        if r > 1e-10:
            H[1, 0] = -x * z / (r ** 2 * rxy) if rxy > 1e-10 else 0.0
            H[1, 1] = -y * z / (r ** 2 * rxy) if rxy > 1e-10 else 0.0
            H[1, 2] = rxy / (r ** 2)

        return z_pred, H

    def _compute_rms(
        self, state: np.ndarray, epoch: pd.Timestamp, obs: pd.DataFrame
    ) -> float:
        residuals_sq = []
        for _, row in obs.iterrows():
            dt = (pd.to_datetime(row["ob_time"]) - epoch).total_seconds()
            prop = self._propagate_twobody(state, dt)
            if prop is None:
                continue
            z_pred, _ = self._measurement_and_jacobian(prop)
            ra_obs = np.deg2rad(float(row["ra"]))
            dec_obs = np.deg2rad(float(row["declination"]))
            dra = (ra_obs - z_pred[0] + np.pi) % (2 * np.pi) - np.pi
            ddec = dec_obs - z_pred[1]
            residuals_sq.append(dra ** 2 + ddec ** 2)
        return float(np.sqrt(np.mean(residuals_sq))) if residuals_sq else 0.0


class UKFRefiner(AbstractRefiner):
    """
    Unscented Kalman filter refinement.

    Uses sigma-point propagation instead of Jacobian linearisation,
    which can provide better accuracy for highly nonlinear dynamics.
    """

    MU = 398600.4418

    def refine(
        self, initial_orbit: IODResult, observations: pd.DataFrame
    ) -> Optional[IODResult]:
        if len(observations) < 2:
            return None
        try:
            return self._run_filter(initial_orbit, observations)
        except Exception as e:
            logger.warning(f"UKF refinement failed: {e}")
            return None

    def _run_filter(
        self, initial_orbit: IODResult, observations: pd.DataFrame
    ) -> Optional[IODResult]:
        obs = observations.sort_values("ob_time").reset_index(drop=True)
        epoch = pd.to_datetime(initial_orbit.epoch)

        n = 6  # state dimension
        alpha = 1e-3
        beta = 2.0
        kappa = 0.0
        lam = alpha ** 2 * (n + kappa) - n

        # Weights
        Wm = np.full(2 * n + 1, 1.0 / (2 * (n + lam)))
        Wc = np.full(2 * n + 1, 1.0 / (2 * (n + lam)))
        Wm[0] = lam / (n + lam)
        Wc[0] = lam / (n + lam) + (1 - alpha ** 2 + beta)

        x = initial_orbit.state.copy()
        P = np.diag([100.0, 100.0, 100.0, 0.1, 0.1, 0.1])

        q_pos = self.config.process_noise_pos_km ** 2
        q_vel = self.config.process_noise_vel_km_s ** 2
        Q_base = np.diag([q_pos, q_pos, q_pos, q_vel, q_vel, q_vel])

        sigma_ra = np.deg2rad(5.0 / 3600.0)
        sigma_dec = np.deg2rad(5.0 / 3600.0)
        R = np.diag([sigma_ra ** 2, sigma_dec ** 2])

        prev_time = epoch

        for _, row in obs.iterrows():
            cur_time = pd.to_datetime(row["ob_time"])
            dt = (cur_time - prev_time).total_seconds()

            # --- Predict via sigma points ---
            if abs(dt) > 0.01:
                sqrt_P = np.linalg.cholesky((n + lam) * P)
                sigma_pts = np.zeros((2 * n + 1, n))
                sigma_pts[0] = x
                for i in range(n):
                    sigma_pts[i + 1] = x + sqrt_P[i]
                    sigma_pts[n + i + 1] = x - sqrt_P[i]

                # Propagate sigma points
                prop_pts = np.zeros_like(sigma_pts)
                valid = True
                for i in range(2 * n + 1):
                    sp = self._propagate_twobody(sigma_pts[i], dt)
                    if sp is None:
                        valid = False
                        break
                    prop_pts[i] = sp

                if not valid:
                    return None

                x = np.sum(Wm[:, None] * prop_pts, axis=0)
                P = Q_base * abs(dt)
                for i in range(2 * n + 1):
                    diff = prop_pts[i] - x
                    P += Wc[i] * np.outer(diff, diff)

            prev_time = cur_time

            # --- Update ---
            sqrt_P = np.linalg.cholesky((n + lam) * P)
            sigma_pts = np.zeros((2 * n + 1, n))
            sigma_pts[0] = x
            for i in range(n):
                sigma_pts[i + 1] = x + sqrt_P[i]
                sigma_pts[n + i + 1] = x - sqrt_P[i]

            # Predicted measurements
            z_pts = np.zeros((2 * n + 1, 2))
            for i in range(2 * n + 1):
                z_pts[i] = self._state_to_radec(sigma_pts[i])

            z_pred = np.sum(Wm[:, None] * z_pts, axis=0)

            Pzz = R.copy()
            Pxz = np.zeros((n, 2))
            for i in range(2 * n + 1):
                dz = z_pts[i] - z_pred
                dz[0] = (dz[0] + np.pi) % (2 * np.pi) - np.pi
                dx = sigma_pts[i] - x
                Pzz += Wc[i] * np.outer(dz, dz)
                Pxz += Wc[i] * np.outer(dx, dz)

            ra_obs = np.deg2rad(float(row["ra"]))
            dec_obs = np.deg2rad(float(row["declination"]))
            y_innov = np.array([ra_obs, dec_obs]) - z_pred
            y_innov[0] = (y_innov[0] + np.pi) % (2 * np.pi) - np.pi

            try:
                K = Pxz @ np.linalg.inv(Pzz)
            except np.linalg.LinAlgError:
                continue

            x = x + K @ y_innov
            P = P - K @ Pzz @ K.T

        cov_upper = []
        for i in range(6):
            for j in range(i, 6):
                cov_upper.append(float(P[i, j]))

        return IODResult(
            state=x,
            epoch=initial_orbit.epoch,
            observation_ids=initial_orbit.observation_ids,
            covariance=cov_upper,
            method="ukf",
            iterations=len(obs),
        )

    def _propagate_twobody(self, state: np.ndarray, dt: float) -> Optional[np.ndarray]:
        r = state[:3].copy()
        v = state[3:].copy()
        n_steps = max(int(abs(dt) / 10.0), 1)
        h = dt / n_steps
        for _ in range(n_steps):
            r_mag = np.linalg.norm(r)
            if r_mag < 10.0:
                return None
            a = -self.MU / (r_mag ** 3) * r
            v = v + a * h
            r = r + v * h
        return np.concatenate([r, v])

    @staticmethod
    def _state_to_radec(state: np.ndarray) -> np.ndarray:
        x, y, z = state[:3]
        r = np.sqrt(x ** 2 + y ** 2 + z ** 2)
        ra = np.arctan2(y, x) % (2 * np.pi)
        dec = np.arcsin(z / r)
        return np.array([ra, dec])
