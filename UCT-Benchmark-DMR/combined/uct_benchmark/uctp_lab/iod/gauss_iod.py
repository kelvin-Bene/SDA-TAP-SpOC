"""
Gauss IOD wrapper for UCTP Lab.

Wraps the existing gauss.py module from uct_benchmark/simulation/gauss.py,
adapting its interface for the UCTP Lab pipeline.
"""

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..config import IODConfig
from .base import AbstractIOD, IODResult


class GaussIOD(AbstractIOD):
    """
    Gauss angles-only IOD using the existing gauss() implementation.

    Requires at least 3 observations with RA, Dec, and sensor location data.
    Falls back to a simplified version if sensor location data is unavailable.
    """

    def determine_orbit(self, observations: pd.DataFrame) -> Optional[IODResult]:
        """
        Run Gauss IOD on the provided observations.

        If sensor location columns (senlon, senlat, senalt) are present,
        uses the full gauss() from uct_benchmark.simulation.gauss.
        Otherwise, uses a simplified three-body angles-only approach.
        """
        if len(observations) < self.config.min_observations:
            logger.debug(
                f"GaussIOD: Need {self.config.min_observations} obs, got {len(observations)}"
            )
            return None

        has_sensor_data = all(
            col in observations.columns for col in ["senlon", "senlat", "senalt"]
        )

        if has_sensor_data:
            return self._run_full_gauss(observations)
        else:
            return self._run_simplified_gauss(observations)

    def _run_full_gauss(self, observations: pd.DataFrame) -> Optional[IODResult]:
        """Run full Gauss IOD using the existing gauss module."""
        try:
            from uct_benchmark.simulation.gauss import gauss, cullStates

            # Prepare data in the format expected by gauss()
            obs_df = observations.copy()
            # Ensure required columns exist with expected names
            if "satNo" not in obs_df.columns:
                obs_df["satNo"] = 0  # Placeholder for unknown objects
            if "obTime" not in obs_df.columns and "ob_time" in obs_df.columns:
                obs_df["obTime"] = obs_df["ob_time"].astype(str)

            obs_df = obs_df.reset_index(drop=True)

            # Run Gauss
            states = gauss(obs_df)
            if states is None or states.empty:
                logger.debug("GaussIOD: No states returned from gauss()")
                return None

            # Cull outlier states
            if self.config.cull_states and len(states) > 1:
                states = cullStates(states)
                if states.empty:
                    logger.debug("GaussIOD: All states culled")
                    return None

            # Use the best state (first after culling)
            best = states.iloc[0]
            state_vec = np.array(best["state"])
            epoch = best["obTime"][1] if isinstance(best["obTime"], list) else str(best["obTime"])

            return IODResult(
                state=state_vec,
                epoch=epoch,
                observation_ids=observations["id"].tolist(),
                method="gauss_full",
                iterations=int(best.get("itCount", 0)),
            )

        except Exception as e:
            logger.warning(f"GaussIOD full gauss failed: {e}")
            return self._run_simplified_gauss(observations)

    def _run_simplified_gauss(self, observations: pd.DataFrame) -> Optional[IODResult]:
        """
        Simplified Gauss-like IOD without sensor location data.

        Uses three observations to estimate a preliminary orbit assuming
        a geocentric observer. This is approximate but works for initial
        pipeline testing.
        """
        try:
            from ..transforms import radec_to_unit_vector

            obs = observations.sort_values("ob_time").reset_index(drop=True)

            # Select three observations: first, middle, last
            n = len(obs)
            indices = [0, n // 2, n - 1]
            if indices[0] == indices[1] or indices[1] == indices[2]:
                # Too few unique indices
                if n >= 3:
                    indices = [0, 1, 2]
                else:
                    return None

            # Line-of-sight vectors
            los = np.array([
                radec_to_unit_vector(obs.iloc[i]["ra"], obs.iloc[i]["declination"])
                for i in indices
            ])

            # Time extraction
            times = pd.to_datetime(obs.iloc[indices[0]:indices[2] + 1]["ob_time"])
            epoch_mid = obs.iloc[indices[1]]["ob_time"]

            # Simplified orbit estimate: assume circular orbit at ~7000 km
            # Place object along middle LOS direction at estimated range
            mu = 398600.4418  # km^3/s^2
            r_est = 7000.0  # km, default estimate

            r_vec = los[1] * r_est

            # Estimate velocity from angular motion
            dt01 = (times.iloc[1] - times.iloc[0]).total_seconds()
            dt12 = (times.iloc[2] - times.iloc[1]).total_seconds()

            if dt01 > 0 and dt12 > 0:
                # Finite difference velocity estimate
                r0 = los[0] * r_est
                r2 = los[2] * r_est
                dt_total = dt01 + dt12
                v_vec = (r2 - r0) / dt_total
            else:
                # Circular orbit velocity perpendicular to position
                speed = np.sqrt(mu / r_est)
                # Create perpendicular direction
                v_dir = np.cross(np.array([0, 0, 1]), r_vec)
                v_norm = np.linalg.norm(v_dir)
                if v_norm > 1e-10:
                    v_dir = v_dir / v_norm
                else:
                    v_dir = np.array([0, 1, 0])
                v_vec = v_dir * speed

            state = np.concatenate([r_vec, v_vec])

            return IODResult(
                state=state,
                epoch=str(epoch_mid),
                observation_ids=observations["id"].tolist(),
                method="gauss_simplified",
                iterations=0,
            )

        except Exception as e:
            logger.warning(f"GaussIOD simplified failed: {e}")
            return None
