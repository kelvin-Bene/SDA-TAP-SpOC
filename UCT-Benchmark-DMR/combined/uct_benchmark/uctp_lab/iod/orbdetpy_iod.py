"""
orbdetpy Laplace IOD wrapper for UCTP Lab.

Uses orbdetpy's angular-data IOD (Laplace method) when the library is
installed.  Falls back gracefully when orbdetpy is unavailable.
"""

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..config import IODConfig
from .base import AbstractIOD, IODResult


class OrbdetpyLaplaceIOD(AbstractIOD):
    """
    Laplace angles-only IOD via orbdetpy.

    Requires orbdetpy to be installed.  If unavailable, determine_orbit()
    returns None so the pipeline can fall back.
    """

    def __init__(self, config: IODConfig):
        super().__init__(config)
        self._available: Optional[bool] = None

    @property
    def available(self) -> bool:
        if self._available is None:
            try:
                import orbdetpy  # noqa: F401

                self._available = True
            except ImportError:
                self._available = False
                logger.warning("orbdetpy is not installed – OrbdetpyLaplaceIOD disabled")
        return self._available

    def determine_orbit(self, observations: pd.DataFrame) -> Optional[IODResult]:
        if not self.available:
            return None

        if len(observations) < self.config.min_observations:
            logger.debug(
                f"OrbdetpyLaplaceIOD: Need {self.config.min_observations} obs, "
                f"got {len(observations)}"
            )
            return None

        try:
            return self._run_laplace(observations)
        except Exception as e:
            logger.warning(f"OrbdetpyLaplaceIOD failed: {e}")
            return None

    def _run_laplace(self, observations: pd.DataFrame) -> Optional[IODResult]:
        from orbdetpy import configure, DetermineOrbit
        from orbdetpy.conversion import get_J2000_epoch_offset

        obs = observations.sort_values("ob_time").reset_index(drop=True)

        # Build measurement array expected by orbdetpy
        # Each measurement: [time_offset_s, ra_rad, dec_rad]
        epoch_dt = pd.to_datetime(obs.iloc[0]["ob_time"])
        measurements = []
        for _, row in obs.iterrows():
            t = (pd.to_datetime(row["ob_time"]) - epoch_dt).total_seconds()
            ra_rad = np.deg2rad(float(row["ra"]))
            dec_rad = np.deg2rad(float(row["declination"]))
            measurements.append([t, ra_rad, dec_rad])

        # Configure orbdetpy IOD
        cfg = configure(
            prop_start=0.0,
            prop_end=measurements[-1][0],
            prop_step=60.0,
        )

        # Sensor location (if available)
        if all(c in obs.columns for c in ["senlon", "senlat", "senalt"]):
            cfg["Station"] = [{
                "Latitude": float(obs.iloc[0]["senlat"]),
                "Longitude": float(obs.iloc[0]["senlon"]),
                "Altitude": float(obs.iloc[0]["senalt"]),
            }]

        cfg["Measurements"] = [{
            "Time": m[0],
            "RightAscension": m[1],
            "Declination": m[2],
        } for m in measurements]

        # Run orbit determination
        result = DetermineOrbit(cfg)

        if result is None or len(result) == 0:
            logger.debug("OrbdetpyLaplaceIOD: No result returned")
            return None

        # Extract the estimated state vector
        est = result[0] if isinstance(result, list) else result
        state = np.array([
            est.get("x", 0.0), est.get("y", 0.0), est.get("z", 0.0),
            est.get("xDot", 0.0), est.get("yDot", 0.0), est.get("zDot", 0.0),
        ])

        # Check for degenerate result
        if np.linalg.norm(state[:3]) < 100.0:
            logger.debug("OrbdetpyLaplaceIOD: Degenerate state (r < 100 km)")
            return None

        # Extract covariance if provided (21 upper-triangle elements)
        covariance = None
        if "Covariance" in est and est["Covariance"]:
            cov_flat = est["Covariance"]
            if len(cov_flat) >= 21:
                covariance = cov_flat[:21]

        return IODResult(
            state=state,
            epoch=str(epoch_dt),
            observation_ids=observations["id"].tolist(),
            covariance=covariance,
            method="orbdetpy_laplace",
            iterations=int(est.get("Iterations", 0)),
            residual=float(est.get("RMS", 0.0)),
        )
