"""
Batch least-squares orbit refinement for UCTP Lab.

Iterative weighted least-squares (WLS) differential correction
using a two-body dynamics model. Refines an initial state estimate
from IOD against the full set of angular observations in a cluster.
"""

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..config import RefinementConfig
from ..iod.base import IODResult
from .base import AbstractRefiner


class BatchLeastSquaresRefiner(AbstractRefiner):
    """
    Iterative batch WLS using two-body propagation with finite-difference
    partials for the observation-state Jacobian.
    """

    MU = 398600.4418  # km^3/s^2

    def refine(
        self, initial_orbit: IODResult, observations: pd.DataFrame
    ) -> Optional[IODResult]:
        if len(observations) < 3:
            return None

        try:
            return self._iterate(initial_orbit, observations)
        except Exception as e:
            logger.warning(f"BatchLeastSquares failed: {e}")
            return None

    def _iterate(
        self, initial_orbit: IODResult, observations: pd.DataFrame
    ) -> Optional[IODResult]:
        obs = observations.sort_values("ob_time").reset_index(drop=True)
        epoch = pd.to_datetime(initial_orbit.epoch)
        state = initial_orbit.state.copy()

        for iteration in range(self.config.max_iterations):
            # Compute residuals and Jacobian
            residuals, H = self._compute_residuals_jacobian(state, epoch, obs)
            if residuals is None:
                return None

            # Weighted least squares normal equations: (H^T W H) dx = H^T W r
            W = np.eye(len(residuals))  # unit weights
            HtW = H.T @ W
            N = HtW @ H

            # Regularise for numerical stability
            N += 1e-10 * np.eye(6)

            try:
                dx = np.linalg.solve(N, HtW @ residuals)
            except np.linalg.LinAlgError:
                logger.debug("BatchLeastSquares: Singular normal equations")
                return None

            state += dx

            if np.linalg.norm(dx[:3]) < self.config.convergence_tol:
                # Converged – compute covariance
                rms = np.sqrt(np.mean(residuals ** 2))
                cov_matrix = self._covariance_from_normal(N, residuals)
                return IODResult(
                    state=state,
                    epoch=initial_orbit.epoch,
                    observation_ids=initial_orbit.observation_ids,
                    covariance=cov_matrix,
                    method="batch_least_squares",
                    iterations=iteration + 1,
                    residual=float(rms),
                )

        # Did not converge – return best estimate
        rms = np.sqrt(np.mean(residuals ** 2)) if residuals is not None else 0.0
        return IODResult(
            state=state,
            epoch=initial_orbit.epoch,
            observation_ids=initial_orbit.observation_ids,
            method="batch_least_squares",
            iterations=self.config.max_iterations,
            residual=float(rms),
        )

    def _compute_residuals_jacobian(
        self,
        state: np.ndarray,
        epoch: pd.Timestamp,
        obs: pd.DataFrame,
    ):
        """Compute observation residuals and the Jacobian H matrix."""
        n_obs = len(obs)
        residuals = np.zeros(2 * n_obs)
        H = np.zeros((2 * n_obs, 6))
        step = 1e-4  # finite-difference step

        for idx, (_, row) in enumerate(obs.iterrows()):
            dt = (pd.to_datetime(row["ob_time"]) - epoch).total_seconds()
            prop_state = self._propagate_twobody(state, dt)
            if prop_state is None:
                return None, None

            ra_pred, dec_pred = self._state_to_radec(prop_state)
            ra_obs = float(row["ra"])
            dec_obs = float(row["declination"])

            residuals[2 * idx] = ra_obs - ra_pred
            residuals[2 * idx + 1] = dec_obs - dec_pred

            # Wrap RA residual to [-180, 180]
            if residuals[2 * idx] > 180.0:
                residuals[2 * idx] -= 360.0
            elif residuals[2 * idx] < -180.0:
                residuals[2 * idx] += 360.0

            # Convert residuals to radians for consistency
            residuals[2 * idx] = np.deg2rad(residuals[2 * idx])
            residuals[2 * idx + 1] = np.deg2rad(residuals[2 * idx + 1])

            # Numerical Jacobian via central differences
            for j in range(6):
                s_plus = state.copy()
                s_minus = state.copy()
                delta = step if j < 3 else step * 1e-3
                s_plus[j] += delta
                s_minus[j] -= delta

                p_plus = self._propagate_twobody(s_plus, dt)
                p_minus = self._propagate_twobody(s_minus, dt)
                if p_plus is None or p_minus is None:
                    return None, None

                ra_p, dec_p = self._state_to_radec(p_plus)
                ra_m, dec_m = self._state_to_radec(p_minus)

                H[2 * idx, j] = np.deg2rad(ra_p - ra_m) / (2 * delta)
                H[2 * idx + 1, j] = np.deg2rad(dec_p - dec_m) / (2 * delta)

        return residuals, H

    @staticmethod
    def _state_to_radec(state: np.ndarray):
        """Convert ECI position to RA/Dec in degrees."""
        x, y, z = state[:3]
        r = np.sqrt(x ** 2 + y ** 2 + z ** 2)
        dec = np.rad2deg(np.arcsin(z / r))
        ra = np.rad2deg(np.arctan2(y, x)) % 360.0
        return ra, dec

    def _propagate_twobody(self, state: np.ndarray, dt: float) -> Optional[np.ndarray]:
        """Simple two-body Kepler propagation using universal variables."""
        r0 = state[:3]
        v0 = state[3:]
        r0_mag = np.linalg.norm(r0)

        if r0_mag < 10.0 or dt == 0.0:
            return state.copy() if dt == 0.0 else None

        # Simple Euler integration for short arcs (< 1 orbit)
        # For production, replace with a universal-variable solver
        n_steps = max(int(abs(dt) / 10.0), 1)
        h = dt / n_steps
        r = r0.copy()
        v = v0.copy()

        for _ in range(n_steps):
            r_mag = np.linalg.norm(r)
            if r_mag < 10.0:
                return None
            a = -self.MU / (r_mag ** 3) * r
            v = v + a * h
            r = r + v * h

        return np.concatenate([r, v])

    @staticmethod
    def _covariance_from_normal(N: np.ndarray, residuals: np.ndarray):
        """Compute 21-element upper-triangle covariance from normal equations."""
        try:
            n_obs = len(residuals)
            sigma2 = np.sum(residuals ** 2) / max(n_obs - 6, 1)
            cov_full = sigma2 * np.linalg.inv(N)
            # Extract upper triangle (row-major)
            upper = []
            for i in range(6):
                for j in range(i, 6):
                    upper.append(float(cov_full[i, j]))
            return upper
        except np.linalg.LinAlgError:
            return None
