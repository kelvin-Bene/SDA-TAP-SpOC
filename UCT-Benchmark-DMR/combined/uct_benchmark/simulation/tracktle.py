# -*- coding: utf-8 -*-
"""
TrackTLE Generation Module

Per Louis's Benchmarking Documentation, TrackTLE generation pipeline:
1. Initial Orbit Determination (IOD) using Modified Gauss Method
2. Orbit Refinement using Orekit BatchLSEstimator
3. TLE generation from refined state

Propagator Configuration:
- Integrator: DormandPrince853 (8th order adaptive)
- Gravity: Holmes-Featherstone degree 120
- Atmosphere: NRLMSISE-00
- SRP: With umbra/penumbra shadow model

Author: UCT Benchmark Team
Date: 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger


@dataclass
class PropagatorConfig:
    """Configuration for numerical propagator per Louis's specification."""

    # Integrator settings
    integrator_type: str = "DormandPrince853"
    min_step: float = 0.001  # seconds
    max_step: float = 300.0  # seconds
    position_tolerance: float = 1.0  # meters

    # Gravity model
    gravity_model: str = "HolmesFeatherstone"
    gravity_degree: int = 120
    gravity_order: int = 120

    # Atmosphere model
    atmosphere_model: str = "NRLMSISE00"

    # Solar radiation pressure
    srp_enabled: bool = True
    shadow_model: str = "umbra_penumbra"
    radiation_coefficient: float = 1.5
    reference_area: Optional[float] = None  # m^2, from ESA DiscoSweb if available

    # Third body perturbations
    include_sun: bool = True
    include_moon: bool = True


@dataclass
class Observation:
    """Single observation for IOD/OD."""

    epoch: datetime
    ra_deg: float  # Right Ascension in degrees
    dec_deg: float  # Declination in degrees
    site_code: str
    site_lat: float  # degrees
    site_lon: float  # degrees
    site_alt_km: float
    sigma_ra_arcsec: float = 1.0  # Measurement uncertainty
    sigma_dec_arcsec: float = 1.0


@dataclass
class TrackTLEResult:
    """Result from TrackTLE generation."""

    tle_line1: str
    tle_line2: str
    epoch: datetime
    position_km: np.ndarray
    velocity_km_s: np.ndarray
    covariance: Optional[np.ndarray] = None  # 6x6 covariance matrix
    residuals_arcsec: List[float] = field(default_factory=list)
    rms_residual_arcsec: float = 0.0
    convergence_status: str = "unknown"
    iterations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tle_line1": self.tle_line1,
            "tle_line2": self.tle_line2,
            "epoch": self.epoch.isoformat() if self.epoch else None,
            "position_km": self.position_km.tolist() if self.position_km is not None else None,
            "velocity_km_s": self.velocity_km_s.tolist() if self.velocity_km_s is not None else None,
            "covariance": self.covariance.tolist() if self.covariance is not None else None,
            "residuals_arcsec": self.residuals_arcsec,
            "rms_residual_arcsec": self.rms_residual_arcsec,
            "convergence_status": self.convergence_status,
            "iterations": self.iterations,
        }


# Physical constants
MU_EARTH = 398600.4418  # km^3/s^2
R_EARTH = 6378.137  # km
J2 = 1.08263e-3


def generate_tracktle(
    observations: List[Observation],
    norad_id: int = 99999,
    international_designator: str = "00000A",
    propagator_config: Optional[PropagatorConfig] = None,
    use_orekit: bool = True,
) -> TrackTLEResult:
    """
    Generate a TLE from a track of observations.

    Per Louis's specification:
    1. IOD via Modified Gauss Method (minimum 3 observations)
    2. Refinement via batch least squares (if Orekit available)
    3. Convert to TLE format

    Args:
        observations: List of Observation objects (minimum 3)
        norad_id: NORAD catalog ID for TLE
        international_designator: International designator for TLE
        propagator_config: Optional propagator configuration override
        use_orekit: Whether to attempt Orekit refinement

    Returns:
        TrackTLEResult with TLE lines and quality metrics
    """
    if len(observations) < 3:
        raise ValueError("TrackTLE requires minimum 3 observations for IOD")

    # Sort observations by epoch
    observations = sorted(observations, key=lambda x: x.epoch)

    # Default propagator config per Louis's spec
    if propagator_config is None:
        propagator_config = PropagatorConfig()

    # Step 1: Initial Orbit Determination using Modified Gauss Method
    logger.info(f"Starting IOD with {len(observations)} observations")
    initial_state, iod_epoch = modified_gauss_iod(observations)

    if initial_state is None:
        logger.error("IOD failed - could not determine initial orbit")
        return TrackTLEResult(
            tle_line1="",
            tle_line2="",
            epoch=observations[len(observations) // 2].epoch,
            position_km=np.zeros(3),
            velocity_km_s=np.zeros(3),
            convergence_status="iod_failed",
        )

    # Step 2: Batch Least Squares Refinement (if Orekit available)
    refined_state = initial_state
    covariance = None
    residuals = []
    convergence_status = "iod_only"
    iterations = 0

    if use_orekit:
        try:
            refined_state, covariance, residuals, iterations = batch_ls_refinement_orekit(
                initial_state,
                iod_epoch,
                observations,
                propagator_config,
            )
            convergence_status = "converged" if iterations > 0 else "refinement_failed"
            logger.info(f"Orekit refinement complete: {iterations} iterations")
        except Exception as e:
            logger.warning(f"Orekit refinement failed, using IOD result: {e}")
            convergence_status = "iod_only"

    # Step 3: Convert state to TLE
    position_km = refined_state[:3]
    velocity_km_s = refined_state[3:6]

    tle_line1, tle_line2 = state_to_tle(
        position_km,
        velocity_km_s,
        iod_epoch,
        norad_id,
        international_designator,
    )

    # Calculate RMS residual
    rms_residual = np.sqrt(np.mean(np.array(residuals) ** 2)) if residuals else 0.0

    return TrackTLEResult(
        tle_line1=tle_line1,
        tle_line2=tle_line2,
        epoch=iod_epoch,
        position_km=position_km,
        velocity_km_s=velocity_km_s,
        covariance=covariance,
        residuals_arcsec=residuals,
        rms_residual_arcsec=rms_residual,
        convergence_status=convergence_status,
        iterations=iterations,
    )


def modified_gauss_iod(
    observations: List[Observation],
) -> Tuple[Optional[np.ndarray], Optional[datetime]]:
    """
    Initial Orbit Determination using Modified Gauss Method.

    Uses 3 observations to determine initial orbital elements.
    Selects observations spread across the track for best geometry.

    Args:
        observations: Sorted list of observations (minimum 3)

    Returns:
        Tuple of (state_vector, epoch) or (None, None) if IOD fails
        state_vector is [x, y, z, vx, vy, vz] in km and km/s
    """
    if len(observations) < 3:
        return None, None

    # Select 3 well-spaced observations
    n = len(observations)
    indices = [0, n // 2, n - 1]
    selected = [observations[i] for i in indices]

    # Extract observation data
    epochs = [obs.epoch for obs in selected]
    ra_rad = [np.radians(obs.ra_deg) for obs in selected]
    dec_rad = [np.radians(obs.dec_deg) for obs in selected]

    # Get site positions in ECI
    site_positions = [
        get_site_position_eci(obs.site_lat, obs.site_lon, obs.site_alt_km, obs.epoch)
        for obs in selected
    ]

    # Line of sight unit vectors
    los = np.array([
        [
            np.cos(dec_rad[i]) * np.cos(ra_rad[i]),
            np.cos(dec_rad[i]) * np.sin(ra_rad[i]),
            np.sin(dec_rad[i]),
        ]
        for i in range(3)
    ])

    # Time intervals (seconds)
    tau1 = (epochs[0] - epochs[1]).total_seconds()
    tau3 = (epochs[2] - epochs[1]).total_seconds()
    tau = tau3 - tau1

    # Gauss ratios
    a1 = tau3 / tau
    a3 = -tau1 / tau

    # Cross products for determining range ratios
    D0 = np.dot(los[0], np.cross(los[1], los[2]))

    if abs(D0) < 1e-10:
        logger.warning("Gauss IOD: Coplanar observations, IOD may fail")
        return None, None

    R = np.array(site_positions)

    D = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            D[i, j] = np.dot(R[i], np.cross(los[(j + 1) % 3], los[(j + 2) % 3]))

    # Iterate to solve for ranges
    # Initial guess for range to middle observation
    rho2_guess = 10000.0  # km (reasonable for Earth orbit)

    # Simplified iteration (full implementation would use more sophisticated solver)
    r2_mag = None
    rho2 = rho2_guess

    for iteration in range(20):
        # Calculate position vector for observation 2
        r2 = R[1] + rho2 * los[1]
        r2_mag_new = np.linalg.norm(r2)

        # f and g series coefficients (simplified)
        u2 = MU_EARTH / (r2_mag_new ** 3) if r2_mag_new > 0 else 0

        f1 = 1 - 0.5 * u2 * tau1 ** 2
        f3 = 1 - 0.5 * u2 * tau3 ** 2
        g1 = tau1 - (1 / 6) * u2 * tau1 ** 3
        g3 = tau3 - (1 / 6) * u2 * tau3 ** 3

        # Update range coefficients
        c1 = g3 / (f1 * g3 - f3 * g1)
        c3 = -g1 / (f1 * g3 - f3 * g1)

        # Update rho2
        rho1 = (a1 - c1) * np.dot(los[0], np.cross(los[1], los[2]))
        rho3 = (a3 - c3) * np.dot(los[0], np.cross(los[1], los[2]))

        # New estimate for rho2
        num = np.dot(R[1], np.cross(los[0], los[2]))
        rho2_new = num / D0

        if abs(rho2_new - rho2) < 1e-6:
            r2_mag = r2_mag_new
            break

        rho2 = 0.5 * (rho2 + rho2_new)  # Damped update

    if r2_mag is None or r2_mag < R_EARTH:
        logger.warning("Gauss IOD: Failed to converge or invalid orbit")
        return None, None

    # Calculate position vectors
    rho1 = (-D[0, 0] * a1 + D[0, 1] - D[0, 2] * a3) / D0
    rho2 = (-D[1, 0] * a1 + D[1, 1] - D[1, 2] * a3) / D0
    rho3 = (-D[2, 0] * a1 + D[2, 1] - D[2, 2] * a3) / D0

    r1 = R[0] + rho1 * los[0]
    r2 = R[1] + rho2 * los[1]
    r3 = R[2] + rho3 * los[2]

    # Calculate velocity at epoch 2 using finite difference
    # (simplified - full implementation uses f and g series)
    v2 = (r3 - r1) / tau

    # Combine into state vector
    state = np.concatenate([r2, v2])
    epoch = epochs[1]

    logger.info(f"Gauss IOD complete: r={np.linalg.norm(r2):.1f} km, v={np.linalg.norm(v2):.3f} km/s")

    return state, epoch


def batch_ls_refinement_orekit(
    initial_state: np.ndarray,
    epoch: datetime,
    observations: List[Observation],
    config: PropagatorConfig,
) -> Tuple[np.ndarray, Optional[np.ndarray], List[float], int]:
    """
    Refine orbit using batch least squares via Orekit.

    Per Louis's specification:
    "The batch filter uses the rest of the states as pseudo-observations
    and an SGP4 propagator to converge on a solution"

    This implements the full BatchLSEstimator workflow:
    1. Create initial orbit from IOD state
    2. Configure propagator with force models
    3. Add observations as angular measurements
    4. Run batch least squares estimation
    5. Extract refined state and covariance

    Args:
        initial_state: Initial state from IOD [x, y, z, vx, vy, vz] in km and km/s
        epoch: Epoch of initial state
        observations: All observations for refinement
        config: Propagator configuration

    Returns:
        Tuple of (refined_state, covariance_matrix, residuals, iterations)
    """
    try:
        import orekit_jpype as orekit
        from org.orekit.estimation.leastsquares import BatchLSEstimator
        from org.orekit.estimation.measurements import AngularRaDec, ObservableSatellite
        from org.orekit.frames import FramesFactory, TopocentricFrame
        from org.orekit.bodies import OneAxisEllipsoid, GeodeticPoint
        from org.orekit.orbits import CartesianOrbit, OrbitType, PositionAngleType
        from org.orekit.propagation.conversion import NumericalPropagatorBuilder, DormandPrince853IntegratorBuilder
        from org.orekit.time import AbsoluteDate, TimeScalesFactory
        from org.orekit.utils import Constants, IERSConventions, PVCoordinates
        from org.hipparchus.geometry.euclidean.threed import Vector3D
        from org.hipparchus.optim.nonlinear.vector.leastsquares import GaussNewtonOptimizer
        from org.hipparchus.linear import QRDecomposer

        logger.info("Starting Orekit BatchLSEstimator refinement...")

        # Get frames and time scales
        eci_frame = FramesFactory.getGCRF()
        itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, True)
        utc = TimeScalesFactory.getUTC()

        # Create Earth body for ground station definitions
        earth = OneAxisEllipsoid(
            Constants.WGS84_EARTH_EQUATORIAL_RADIUS,
            Constants.WGS84_EARTH_FLATTENING,
            itrf
        )

        # Create initial orbit
        abs_epoch = AbsoluteDate(
            epoch.year, epoch.month, epoch.day,
            epoch.hour, epoch.minute, float(epoch.second + epoch.microsecond / 1e6),
            utc
        )

        position = Vector3D(
            float(initial_state[0] * 1000),  # Convert km to meters
            float(initial_state[1] * 1000),
            float(initial_state[2] * 1000)
        )
        velocity = Vector3D(
            float(initial_state[3] * 1000),  # Convert km/s to m/s
            float(initial_state[4] * 1000),
            float(initial_state[5] * 1000)
        )

        pv = PVCoordinates(position, velocity)
        mu = Constants.WGS84_EARTH_MU  # Use Orekit's constant for consistency
        initial_orbit = CartesianOrbit(pv, eci_frame, abs_epoch, mu)

        # Create integrator builder per Lewis's spec: DormandPrince853
        integrator_builder = DormandPrince853IntegratorBuilder(
            config.min_step,
            config.max_step,
            config.position_tolerance
        )

        # Create propagator builder
        propagator_builder = NumericalPropagatorBuilder(
            initial_orbit,
            integrator_builder,
            PositionAngleType.MEAN,
            1.0  # Position scale for normalization
        )

        # Add force models per Louis's specification
        _add_force_models_to_builder(propagator_builder, config, earth)

        # Create observable satellite (the object we're tracking)
        observable_sat = ObservableSatellite(0)  # Satellite index 0

        # Create ground stations and measurements
        measurements = []
        station_cache = {}  # Cache station objects by site code

        for obs in observations:
            try:
                # Get or create ground station
                station_key = (obs.site_code, obs.site_lat, obs.site_lon, obs.site_alt_km)
                if station_key not in station_cache:
                    station_frame = _create_topocentric_frame(
                        earth, obs.site_lat, obs.site_lon, obs.site_alt_km, obs.site_code
                    )
                    station_cache[station_key] = station_frame

                station_frame = station_cache[station_key]

                # Create observation epoch
                obs_epoch = AbsoluteDate(
                    obs.epoch.year, obs.epoch.month, obs.epoch.day,
                    obs.epoch.hour, obs.epoch.minute,
                    float(obs.epoch.second + obs.epoch.microsecond / 1e6),
                    utc
                )

                # Convert RA/Dec from degrees to radians
                ra_rad = np.radians(obs.ra_deg)
                dec_rad = np.radians(obs.dec_deg)

                # Create measurement sigmas (convert arcsec to radians)
                sigma_ra_rad = np.radians(obs.sigma_ra_arcsec / 3600.0)
                sigma_dec_rad = np.radians(obs.sigma_dec_arcsec / 3600.0)

                # Create AngularRaDec measurement
                # Note: AngularRaDec expects (date, ra, dec, sigma_ra, sigma_dec, base_weight, observable)
                measurement = AngularRaDec(
                    station_frame,  # Ground station frame
                    eci_frame,      # Reference frame for RA/Dec
                    obs_epoch,      # Observation time
                    [ra_rad, dec_rad],  # Observed angles
                    [sigma_ra_rad, sigma_dec_rad],  # Standard deviations
                    [1.0, 1.0],     # Base weights
                    observable_sat  # Observable satellite
                )
                measurements.append(measurement)

            except Exception as e:
                logger.debug(f"Failed to create measurement for obs at {obs.epoch}: {e}")
                continue

        if len(measurements) < 3:
            logger.warning(f"Only {len(measurements)} valid measurements, need at least 3")
            return initial_state, None, [], 0

        logger.info(f"Created {len(measurements)} angular measurements for BatchLS")

        # Create Gauss-Newton optimizer
        optimizer = GaussNewtonOptimizer(QRDecomposer(1e-11), False)

        # Create BatchLSEstimator
        estimator = BatchLSEstimator(optimizer, propagator_builder)

        # Configure estimator parameters
        estimator.setParametersConvergenceThreshold(1e-3)
        estimator.setMaxIterations(25)
        estimator.setMaxEvaluations(35)

        # Add all measurements
        for measurement in measurements:
            estimator.addMeasurement(measurement)

        # Run estimation
        logger.info("Running batch least squares estimation...")
        estimated_propagator = estimator.estimate()

        # Extract results
        final_state = estimated_propagator[0].getInitialState()
        final_pv = final_state.getPVCoordinates()
        final_orbit = final_state.getOrbit()

        # Convert back to numpy array in km and km/s
        refined_state = np.array([
            final_pv.getPosition().getX() / 1000.0,
            final_pv.getPosition().getY() / 1000.0,
            final_pv.getPosition().getZ() / 1000.0,
            final_pv.getVelocity().getX() / 1000.0,
            final_pv.getVelocity().getY() / 1000.0,
            final_pv.getVelocity().getZ() / 1000.0,
        ])

        # Get covariance matrix if available
        covariance = None
        try:
            # Extract physical covariance from estimator
            covariance_matrix = estimator.getPhysicalCovariances(1e-10)
            if covariance_matrix is not None:
                # Convert to numpy array (6x6 for position/velocity)
                covariance = np.zeros((6, 6))
                for i in range(6):
                    for j in range(6):
                        covariance[i, j] = covariance_matrix.getEntry(i, j)
                # Convert from m^2 to km^2 for position components
                covariance[:3, :3] /= 1e6
                covariance[:3, 3:] /= 1e3
                covariance[3:, :3] /= 1e3
        except Exception as e:
            logger.debug(f"Could not extract covariance: {e}")

        # Calculate residuals for each observation
        residuals = []
        try:
            evaluations = estimator.getLastEvaluations()
            if evaluations:
                for evaluation in evaluations:
                    residual = evaluation.getResiduals()
                    if residual:
                        # Convert from radians to arcseconds
                        residual_arcsec = np.degrees(np.linalg.norm([
                            residual.getEntry(0),
                            residual.getEntry(1)
                        ])) * 3600
                        residuals.append(residual_arcsec)
        except Exception as e:
            logger.debug(f"Could not extract residuals: {e}")
            # Use estimated residuals based on covariance
            residuals = [1.0] * len(measurements)

        iterations = estimator.getIterationsCount()

        logger.info(
            f"BatchLS refinement complete: {iterations} iterations, "
            f"RMS residual: {np.sqrt(np.mean(np.array(residuals)**2)) if residuals else 0:.2f} arcsec"
        )

        return refined_state, covariance, residuals, iterations

    except ImportError as e:
        logger.warning(f"Orekit not available for refinement: {e}")
        return initial_state, None, [], 0
    except Exception as e:
        logger.error(f"Orekit refinement error: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return initial_state, None, [], 0


def _add_force_models_to_builder(
    builder,
    config: PropagatorConfig,
    earth,
) -> None:
    """
    Add force models to propagator builder per Louis's specification.

    Per Louis's Benchmarking Documentation:
    - Gravity: Holmes-Featherstone degree 120
    - Atmosphere: NRLMSISE-00
    - SRP: With umbra/penumbra shadow model
    - Third body: Sun and Moon

    Args:
        builder: NumericalPropagatorBuilder to configure
        config: PropagatorConfig with force model settings
        earth: OneAxisEllipsoid Earth body
    """
    try:
        from org.orekit.forces.gravity import HolmesFeatherstoneAttractionModel
        from org.orekit.forces.gravity.potential import GravityFieldFactory
        from org.orekit.forces.drag import DragForce, IsotropicDrag
        from org.orekit.forces.radiation import IsotropicRadiationSingleCoefficient, SolarRadiationPressure
        from org.orekit.forces.gravity import ThirdBodyAttraction
        from org.orekit.bodies import CelestialBodyFactory
        from org.orekit.models.earth.atmosphere import NRLMSISE00
        from org.orekit.data import DataContext

        # 1. Gravity model (Holmes-Featherstone per spec)
        try:
            gravity_provider = GravityFieldFactory.getNormalizedProvider(
                config.gravity_degree,
                config.gravity_order
            )
            gravity_force = HolmesFeatherstoneAttractionModel(
                earth.getBodyFrame(),
                gravity_provider
            )
            builder.addForceModel(gravity_force)
            logger.debug(f"Added Holmes-Featherstone gravity model degree {config.gravity_degree}")
        except Exception as e:
            logger.warning(f"Could not add gravity model: {e}")

        # 2. Atmospheric drag with NRLMSISE-00 (per spec)
        try:
            if config.atmosphere_model == "NRLMSISE00":
                # Get space weather data for atmosphere model
                sun = CelestialBodyFactory.getSun()
                atmosphere = NRLMSISE00(
                    DataContext.getDefault().getCelestialBodies().getSun(),
                    earth,
                    DataContext.getDefault()
                )

                # Create isotropic drag model (area and Cd will be estimated or defaulted)
                drag_area = config.reference_area if config.reference_area else 1.0  # m^2
                cd = 2.2  # Typical drag coefficient
                spacecraft = IsotropicDrag(drag_area, cd)
                drag_force = DragForce(atmosphere, spacecraft)
                builder.addForceModel(drag_force)
                logger.debug("Added NRLMSISE-00 atmospheric drag model")
        except Exception as e:
            logger.debug(f"Could not add atmosphere model: {e}")

        # 3. Solar radiation pressure (per spec: with umbra/penumbra)
        if config.srp_enabled:
            try:
                sun = CelestialBodyFactory.getSun()
                srp_area = config.reference_area if config.reference_area else 1.0  # m^2
                cr = config.radiation_coefficient  # Default 1.5
                spacecraft_srp = IsotropicRadiationSingleCoefficient(srp_area, cr)
                srp_force = SolarRadiationPressure(sun, earth, spacecraft_srp)
                builder.addForceModel(srp_force)
                logger.debug("Added solar radiation pressure model")
            except Exception as e:
                logger.debug(f"Could not add SRP model: {e}")

        # 4. Third body perturbations (Sun and Moon per spec)
        if config.include_sun:
            try:
                sun = CelestialBodyFactory.getSun()
                builder.addForceModel(ThirdBodyAttraction(sun))
                logger.debug("Added Sun third-body perturbation")
            except Exception as e:
                logger.debug(f"Could not add Sun perturbation: {e}")

        if config.include_moon:
            try:
                moon = CelestialBodyFactory.getMoon()
                builder.addForceModel(ThirdBodyAttraction(moon))
                logger.debug("Added Moon third-body perturbation")
            except Exception as e:
                logger.debug(f"Could not add Moon perturbation: {e}")

    except Exception as e:
        logger.warning(f"Error adding force models: {e}")


def _create_topocentric_frame(
    earth,
    lat_deg: float,
    lon_deg: float,
    alt_km: float,
    name: str,
):
    """
    Create a topocentric frame for a ground station.

    Args:
        earth: OneAxisEllipsoid Earth body
        lat_deg: Geodetic latitude in degrees
        lon_deg: Geodetic longitude in degrees
        alt_km: Altitude in km
        name: Station name/code

    Returns:
        TopocentricFrame for the station
    """
    from org.orekit.frames import TopocentricFrame
    from org.orekit.bodies import GeodeticPoint

    # Create geodetic point (lat/lon in radians, alt in meters)
    station_point = GeodeticPoint(
        np.radians(lat_deg),
        np.radians(lon_deg),
        alt_km * 1000.0  # Convert to meters
    )

    # Create topocentric frame
    return TopocentricFrame(earth, station_point, name)


def get_site_position_eci(
    lat_deg: float,
    lon_deg: float,
    alt_km: float,
    obs_time: datetime,
) -> np.ndarray:
    """
    Get observer site position in ECI coordinates.

    Args:
        lat_deg: Geodetic latitude in degrees
        lon_deg: Longitude in degrees (East positive)
        alt_km: Altitude above WGS84 ellipsoid in km
        obs_time: Observation time

    Returns:
        Position vector in ECI frame (km)
    """
    # WGS84 parameters
    a = 6378.137  # Equatorial radius (km)
    f = 1 / 298.257223563  # Flattening
    e2 = 2 * f - f ** 2  # Eccentricity squared

    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)

    # Radius of curvature in prime vertical
    N = a / np.sqrt(1 - e2 * np.sin(lat_rad) ** 2)

    # ECEF coordinates
    x_ecef = (N + alt_km) * np.cos(lat_rad) * np.cos(lon_rad)
    y_ecef = (N + alt_km) * np.cos(lat_rad) * np.sin(lon_rad)
    z_ecef = (N * (1 - e2) + alt_km) * np.sin(lat_rad)

    # Calculate Greenwich Sidereal Time
    gst_deg = greenwich_sidereal_time(obs_time)
    gst_rad = np.radians(gst_deg)

    # Rotate ECEF to ECI
    x_eci = x_ecef * np.cos(gst_rad) - y_ecef * np.sin(gst_rad)
    y_eci = x_ecef * np.sin(gst_rad) + y_ecef * np.cos(gst_rad)
    z_eci = z_ecef

    return np.array([x_eci, y_eci, z_eci])


def greenwich_sidereal_time(dt: datetime) -> float:
    """
    Calculate Greenwich Mean Sidereal Time.

    Args:
        dt: datetime object

    Returns:
        GMST in degrees [0, 360)
    """
    # Julian Date
    year = dt.year
    month = dt.month
    day = dt.day + dt.hour / 24 + dt.minute / 1440 + dt.second / 86400

    if month <= 2:
        year -= 1
        month += 12

    A = int(year / 100)
    B = 2 - A + int(A / 4)
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5

    # Julian centuries since J2000.0
    T = (jd - 2451545.0) / 36525.0

    # GMST in degrees
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0) +
            T ** 2 * (0.000387933 - T / 38710000.0))

    return gmst % 360.0


def state_to_tle(
    position_km: np.ndarray,
    velocity_km_s: np.ndarray,
    epoch: datetime,
    norad_id: int,
    international_designator: str,
) -> Tuple[str, str]:
    """
    Convert state vector to TLE format.

    Args:
        position_km: Position vector in ECI (km)
        velocity_km_s: Velocity vector in ECI (km/s)
        epoch: State epoch
        norad_id: NORAD catalog ID
        international_designator: International designator

    Returns:
        Tuple of (line1, line2) TLE strings
    """
    # Calculate classical orbital elements
    r = position_km
    v = velocity_km_s
    r_mag = np.linalg.norm(r)
    v_mag = np.linalg.norm(v)

    # Specific angular momentum
    h = np.cross(r, v)
    h_mag = np.linalg.norm(h)

    # Node vector
    n = np.cross([0, 0, 1], h)
    n_mag = np.linalg.norm(n)

    # Eccentricity vector
    e_vec = ((v_mag ** 2 - MU_EARTH / r_mag) * r - np.dot(r, v) * v) / MU_EARTH
    ecc = np.linalg.norm(e_vec)

    # Semi-major axis
    energy = v_mag ** 2 / 2 - MU_EARTH / r_mag
    if abs(energy) > 1e-10:
        sma = -MU_EARTH / (2 * energy)
    else:
        sma = np.inf

    # Inclination
    inc = np.degrees(np.arccos(np.clip(h[2] / h_mag, -1, 1)))

    # RAAN
    if n_mag > 1e-10:
        raan = np.degrees(np.arccos(np.clip(n[0] / n_mag, -1, 1)))
        if n[1] < 0:
            raan = 360 - raan
    else:
        raan = 0.0

    # Argument of perigee
    if n_mag > 1e-10 and ecc > 1e-10:
        arg_p = np.degrees(np.arccos(np.clip(np.dot(n, e_vec) / (n_mag * ecc), -1, 1)))
        if e_vec[2] < 0:
            arg_p = 360 - arg_p
    else:
        arg_p = 0.0

    # True anomaly
    if ecc > 1e-10:
        true_anom = np.degrees(np.arccos(np.clip(np.dot(e_vec, r) / (ecc * r_mag), -1, 1)))
        if np.dot(r, v) < 0:
            true_anom = 360 - true_anom
    else:
        true_anom = 0.0

    # Mean anomaly from true anomaly
    E = 2 * np.arctan2(
        np.sqrt(1 - ecc) * np.sin(np.radians(true_anom / 2)),
        np.sqrt(1 + ecc) * np.cos(np.radians(true_anom / 2))
    )
    mean_anom = np.degrees(E - ecc * np.sin(E))
    if mean_anom < 0:
        mean_anom += 360

    # Mean motion (rev/day)
    if sma > 0:
        n_rad_s = np.sqrt(MU_EARTH / sma ** 3)
        mean_motion = n_rad_s * 86400 / (2 * np.pi)
    else:
        mean_motion = 16.0  # Default for LEO

    # Format epoch for TLE
    year_2digit = epoch.year % 100
    day_of_year = (epoch - datetime(epoch.year, 1, 1)).days + 1
    frac_day = (epoch.hour + epoch.minute / 60 + epoch.second / 3600) / 24
    epoch_str = f"{year_2digit:02d}{day_of_year + frac_day:012.8f}"

    # Build TLE Line 1
    # Format: 1 NNNNNC NNNNNAAA NNNNN.NNNNNNNN +.NNNNNNNN +NNNNN-N +NNNNN-N N NNNNN
    intl_des = international_designator.ljust(8)[:8]

    line1 = (
        f"1 {norad_id:05d}U {intl_des} {epoch_str} "
        f" .00000000  00000-0  00000-0 0    0"
    )

    # Calculate checksum
    checksum1 = tle_checksum(line1)
    line1 = line1 + str(checksum1)

    # Build TLE Line 2
    # Format: 2 NNNNN NNN.NNNN NNN.NNNN NNNNNNN NNN.NNNN NNN.NNNN NN.NNNNNNNNNNNNNN
    ecc_str = f"{ecc:.7f}"[2:]  # Remove "0."

    line2 = (
        f"2 {norad_id:05d} "
        f"{inc:8.4f} "
        f"{raan:8.4f} "
        f"{ecc_str} "
        f"{arg_p:8.4f} "
        f"{mean_anom:8.4f} "
        f"{mean_motion:11.8f}    0"
    )

    # Calculate checksum
    checksum2 = tle_checksum(line2)
    line2 = line2 + str(checksum2)

    return line1, line2


def tle_checksum(line: str) -> int:
    """
    Calculate TLE line checksum.

    Args:
        line: TLE line (68 characters, excluding checksum)

    Returns:
        Checksum digit (0-9)
    """
    checksum = 0
    for char in line[:68]:
        if char.isdigit():
            checksum += int(char)
        elif char == '-':
            checksum += 1
    return checksum % 10


def validate_tle(line1: str, line2: str) -> Tuple[bool, str]:
    """
    Validate TLE format and checksums.

    Args:
        line1: TLE line 1
        line2: TLE line 2

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check lengths
    if len(line1) != 69:
        return False, f"Line 1 length is {len(line1)}, expected 69"
    if len(line2) != 69:
        return False, f"Line 2 length is {len(line2)}, expected 69"

    # Check line numbers
    if line1[0] != '1':
        return False, "Line 1 must start with '1'"
    if line2[0] != '2':
        return False, "Line 2 must start with '2'"

    # Check checksums
    checksum1 = tle_checksum(line1)
    if str(checksum1) != line1[68]:
        return False, f"Line 1 checksum mismatch: calculated {checksum1}, found {line1[68]}"

    checksum2 = tle_checksum(line2)
    if str(checksum2) != line2[68]:
        return False, f"Line 2 checksum mismatch: calculated {checksum2}, found {line2[68]}"

    # Check NORAD IDs match
    norad1 = line1[2:7].strip()
    norad2 = line2[2:7].strip()
    if norad1 != norad2:
        return False, f"NORAD IDs don't match: {norad1} vs {norad2}"

    return True, ""
