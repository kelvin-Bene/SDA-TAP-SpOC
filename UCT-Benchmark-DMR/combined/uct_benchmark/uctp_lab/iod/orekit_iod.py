"""
Orekit Gooding IOD wrapper for UCTP Lab.

Uses Orekit's Gooding angles-only IOD when the JVM is available.
Falls back gracefully when Orekit is not running.
"""

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..config import IODConfig
from .base import AbstractIOD, IODResult


class OrekitGoodingIOD(AbstractIOD):
    """
    Gooding angles-only IOD via Orekit (JPype bridge).

    Requires orekit-jpype to be installed and the JVM to be initialised.
    If unavailable, determine_orbit() returns None.
    """

    def __init__(self, config: IODConfig):
        super().__init__(config)
        self._available: Optional[bool] = None

    @property
    def available(self) -> bool:
        if self._available is None:
            try:
                import orekit  # noqa: F401

                self._available = True
            except ImportError:
                self._available = False
                logger.warning("Orekit is not installed – OrekitGoodingIOD disabled")
        return self._available

    def determine_orbit(self, observations: pd.DataFrame) -> Optional[IODResult]:
        if not self.available:
            return None

        if len(observations) < self.config.min_observations:
            logger.debug(
                f"OrekitGoodingIOD: Need {self.config.min_observations} obs, "
                f"got {len(observations)}"
            )
            return None

        try:
            return self._run_gooding(observations)
        except Exception as e:
            logger.warning(f"OrekitGoodingIOD failed: {e}")
            return None

    def _run_gooding(self, observations: pd.DataFrame) -> Optional[IODResult]:
        import orekit
        from org.orekit.estimation.iod import IodGooding
        from org.orekit.frames import FramesFactory
        from org.orekit.time import AbsoluteDate, TimeScalesFactory
        from org.orekit.bodies import OneAxisEllipsoid, GeodeticPoint
        from org.orekit.utils import IERSConventions
        from org.hipparchus.geometry.euclidean.threed import Vector3D

        obs = observations.sort_values("ob_time").reset_index(drop=True)

        utc = TimeScalesFactory.getUTC()
        j2000 = FramesFactory.getEME2000()
        mu = 398600.4418e9  # m^3/s^2 (Orekit uses SI)

        # Need exactly 3 observations for Gooding
        n = len(obs)
        indices = [0, n // 2, n - 1]

        # Parse observation times
        dates = []
        for i in indices:
            dt = pd.to_datetime(obs.iloc[i]["ob_time"])
            orekit_date = AbsoluteDate(
                dt.year, dt.month, dt.day,
                dt.hour, dt.minute, float(dt.second + dt.microsecond / 1e6),
                utc,
            )
            dates.append(orekit_date)

        # Line-of-sight vectors
        los_vectors = []
        for i in indices:
            ra_rad = np.deg2rad(float(obs.iloc[i]["ra"]))
            dec_rad = np.deg2rad(float(obs.iloc[i]["declination"]))
            x = np.cos(dec_rad) * np.cos(ra_rad)
            y = np.cos(dec_rad) * np.sin(ra_rad)
            z = np.sin(dec_rad)
            los_vectors.append(Vector3D(float(x), float(y), float(z)))

        # Observer position (if sensor data available)
        if all(c in obs.columns for c in ["senlon", "senlat", "senalt"]):
            itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, True)
            earth = OneAxisEllipsoid(
                6378137.0, 1.0 / 298.257223563, itrf
            )
            positions = []
            for i in indices:
                gp = GeodeticPoint(
                    np.deg2rad(float(obs.iloc[i]["senlat"])),
                    np.deg2rad(float(obs.iloc[i]["senlon"])),
                    float(obs.iloc[i]["senalt"]),
                )
                topo = earth.transform(gp)
                pos_j2000 = itrf.getTransformTo(j2000, dates[indices.index(i)]).transformPosition(topo)
                positions.append(pos_j2000)
        else:
            # Default geocentric observer
            positions = [Vector3D.ZERO, Vector3D.ZERO, Vector3D.ZERO]

        # Run Gooding IOD
        gooding = IodGooding(j2000, mu)
        orbit = gooding.estimate(
            positions[0], positions[1], positions[2],
            los_vectors[0], dates[0],
            los_vectors[1], dates[1],
            los_vectors[2], dates[2],
            7000.0e3, 7000.0e3,  # initial range estimates (m)
        )

        if orbit is None:
            logger.debug("OrekitGoodingIOD: Gooding returned None")
            return None

        # Extract state in km, km/s
        pv = orbit.getPVCoordinates(dates[1], j2000)
        pos = pv.getPosition()
        vel = pv.getVelocity()

        state = np.array([
            pos.getX() / 1000.0, pos.getY() / 1000.0, pos.getZ() / 1000.0,
            vel.getX() / 1000.0, vel.getY() / 1000.0, vel.getZ() / 1000.0,
        ])

        if np.linalg.norm(state[:3]) < 100.0:
            logger.debug("OrekitGoodingIOD: Degenerate state")
            return None

        epoch_mid = str(pd.to_datetime(obs.iloc[indices[1]]["ob_time"]))

        return IODResult(
            state=state,
            epoch=epoch_mid,
            observation_ids=observations["id"].tolist(),
            method="orekit_gooding",
            iterations=0,
        )
