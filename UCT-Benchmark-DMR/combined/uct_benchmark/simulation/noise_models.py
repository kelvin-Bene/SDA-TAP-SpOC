# -*- coding: utf-8 -*-
"""
Sensor noise models and photometric simulation for observation generation.

Provides:
- Sensor-specific noise characteristics
- Realistic observation noise injection
- Visual magnitude simulation

Created for UCT Benchmarking Enhancement.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

from uct_benchmark.settings import SENSOR_NOISE_MODELS, SimulationConfig

# =============================================================================
# SENSOR NOISE MODEL CLASSES
# =============================================================================


@dataclass
class OpticalNoiseModel:
    """Noise model for optical (EO) sensors."""

    angular_noise_arcsec: float = 0.5
    timing_noise_ms: float = 1.0
    mag_noise: float = 0.3
    systematic_bias_az: float = 0.0  # arcsec
    systematic_bias_el: float = 0.0  # arcsec
    sensor_type: str = "optical"

    def apply_noise(
        self, ra: float, dec: float, obs_time: float, rng: np.random.Generator = None
    ) -> Tuple[float, float, float]:
        """
        Apply optical sensor noise to measurements.

        Args:
            ra: Right Ascension in degrees
            dec: Declination in degrees
            obs_time: Observation time (for timing noise)
            rng: Random number generator

        Returns:
            Tuple of (noisy_ra, noisy_dec, noisy_time)
        """
        if rng is None:
            rng = np.random.default_rng()

        # Convert angular noise to degrees
        angular_noise_deg = self.angular_noise_arcsec / 3600.0

        # Apply Gaussian noise to angles
        noisy_ra = ra + rng.normal(0, angular_noise_deg)
        noisy_dec = dec + rng.normal(0, angular_noise_deg)

        # Apply systematic bias (converted to degrees)
        noisy_ra += self.systematic_bias_az / 3600.0
        noisy_dec += self.systematic_bias_el / 3600.0

        # Apply timing noise
        timing_noise_sec = self.timing_noise_ms / 1000.0
        noisy_time = obs_time + rng.normal(0, timing_noise_sec)

        return noisy_ra, noisy_dec, noisy_time


@dataclass
class RadarNoiseModel:
    """Noise model for radar sensors."""

    range_noise_m: float = 10.0
    range_rate_noise_m_s: float = 0.01
    angular_noise_deg: float = 0.01
    timing_noise_ms: float = 0.1
    sensor_type: str = "radar"

    def apply_noise(
        self,
        range_km: float,
        range_rate_km_s: float,
        az: float,
        el: float,
        obs_time: float,
        rng: np.random.Generator = None,
    ) -> Tuple[float, float, float, float, float]:
        """
        Apply radar sensor noise to measurements.

        Args:
            range_km: Range in kilometers
            range_rate_km_s: Range rate in km/s
            az: Azimuth in degrees
            el: Elevation in degrees
            obs_time: Observation time
            rng: Random number generator

        Returns:
            Tuple of (noisy_range, noisy_range_rate, noisy_az, noisy_el, noisy_time)
        """
        if rng is None:
            rng = np.random.default_rng()

        # Range noise (convert m to km)
        noisy_range = range_km + rng.normal(0, self.range_noise_m / 1000.0)

        # Range rate noise (convert m/s to km/s)
        noisy_range_rate = range_rate_km_s + rng.normal(0, self.range_rate_noise_m_s / 1000.0)

        # Angular noise
        noisy_az = az + rng.normal(0, self.angular_noise_deg)
        noisy_el = el + rng.normal(0, self.angular_noise_deg)

        # Timing noise
        timing_noise_sec = self.timing_noise_ms / 1000.0
        noisy_time = obs_time + rng.normal(0, timing_noise_sec)

        return noisy_range, noisy_range_rate, noisy_az, noisy_el, noisy_time


@dataclass
class RFNoiseModel:
    """Noise model for RF sensors."""

    angular_noise_deg: float = 0.1
    timing_noise_ms: float = 10.0
    frequency_noise_hz: float = 100.0
    sensor_type: str = "rf"

    def apply_noise(
        self,
        az: float,
        el: float,
        obs_time: float,
        frequency_hz: float = None,
        rng: np.random.Generator = None,
    ) -> Tuple[float, float, float, Optional[float]]:
        """
        Apply RF sensor noise to measurements.

        Args:
            az: Azimuth in degrees
            el: Elevation in degrees
            obs_time: Observation time
            frequency_hz: Signal frequency in Hz
            rng: Random number generator

        Returns:
            Tuple of (noisy_az, noisy_el, noisy_time, noisy_freq)
        """
        if rng is None:
            rng = np.random.default_rng()

        # Angular noise
        noisy_az = az + rng.normal(0, self.angular_noise_deg)
        noisy_el = el + rng.normal(0, self.angular_noise_deg)

        # Timing noise
        timing_noise_sec = self.timing_noise_ms / 1000.0
        noisy_time = obs_time + rng.normal(0, timing_noise_sec)

        # Frequency noise
        noisy_freq = None
        if frequency_hz is not None:
            noisy_freq = frequency_hz + rng.normal(0, self.frequency_noise_hz)

        return noisy_az, noisy_el, noisy_time, noisy_freq


# =============================================================================
# SENSOR MODEL FACTORY
# =============================================================================


def get_sensor_noise_model(sensor_name: str) -> object:
    """
    Get the appropriate noise model for a sensor.

    Args:
        sensor_name: Name of the sensor (e.g., 'GEODSS', 'SBSS', 'Radar')

    Returns:
        Noise model instance
    """
    # Check if sensor is in predefined models
    if sensor_name in SENSOR_NOISE_MODELS:
        params = SENSOR_NOISE_MODELS[sensor_name]
        sensor_type = params.get("sensor_type", "optical")

        if sensor_type == "optical":
            return OpticalNoiseModel(
                angular_noise_arcsec=params.get("angular_noise_arcsec", 0.5),
                timing_noise_ms=params.get("timing_noise_ms", 1.0),
                mag_noise=params.get("mag_noise", 0.3),
                systematic_bias_az=params.get("systematic_bias", {}).get("az", 0.0),
                systematic_bias_el=params.get("systematic_bias", {}).get("el", 0.0),
            )
        elif sensor_type == "radar":
            return RadarNoiseModel(
                range_noise_m=params.get("range_noise_m", 10.0),
                range_rate_noise_m_s=params.get("range_rate_noise_m_s", 0.01),
                angular_noise_deg=params.get("angular_noise_deg", 0.01),
                timing_noise_ms=params.get("timing_noise_ms", 0.1),
            )
        elif sensor_type == "rf":
            return RFNoiseModel(
                angular_noise_deg=params.get("angular_noise_deg", 0.1),
                timing_noise_ms=params.get("timing_noise_ms", 10.0),
            )

    # Default to generic optical model
    return OpticalNoiseModel()


def apply_sensor_noise(obs_dict: Dict, sensor_name: str, rng: np.random.Generator = None) -> Dict:
    """
    Apply sensor-specific noise to an observation dictionary.

    Args:
        obs_dict: Observation dictionary with ra, dec, obTime, etc.
        sensor_name: Name of the sensor
        rng: Random number generator

    Returns:
        Modified observation dictionary with noise applied
    """
    model = get_sensor_noise_model(sensor_name)
    result = obs_dict.copy()

    if isinstance(model, OpticalNoiseModel):
        noisy_ra, noisy_dec, _ = model.apply_noise(
            obs_dict.get("ra", 0),
            obs_dict.get("declination", 0),
            0,  # Time handled separately
            rng,
        )
        result["ra"] = noisy_ra
        result["declination"] = noisy_dec

    elif isinstance(model, RadarNoiseModel):
        noisy_range, noisy_rr, noisy_az, noisy_el, _ = model.apply_noise(
            obs_dict.get("range", 0),
            obs_dict.get("rangeRate", 0),
            obs_dict.get("azimuth", 0),
            obs_dict.get("elevation", 0),
            0,
            rng,
        )
        result["range"] = noisy_range
        result["rangeRate"] = noisy_rr
        result["azimuth"] = noisy_az
        result["elevation"] = noisy_el

    return result


# =============================================================================
# PHOTOMETRIC SIMULATION
# =============================================================================


def compute_phase_angle(
    sat_position: np.ndarray, sun_position: np.ndarray, observer_position: np.ndarray
) -> float:
    """
    Compute the phase angle (Sun-Satellite-Observer angle).

    Args:
        sat_position: Satellite position vector (km)
        sun_position: Sun position vector (km)
        observer_position: Observer position vector (km)

    Returns:
        Phase angle in radians
    """
    # Vector from satellite to sun
    sat_to_sun = sun_position - sat_position
    norm_sun = np.linalg.norm(sat_to_sun)
    if norm_sun < 1e-10:
        return 0.0  # Satellite at sun position (degenerate case)
    sat_to_sun = sat_to_sun / norm_sun

    # Vector from satellite to observer
    sat_to_obs = observer_position - sat_position
    norm_obs = np.linalg.norm(sat_to_obs)
    if norm_obs < 1e-10:
        return 0.0  # Satellite at observer position (degenerate case)
    sat_to_obs = sat_to_obs / norm_obs

    # Phase angle is the angle between these vectors
    cos_phase = np.clip(np.dot(sat_to_sun, sat_to_obs), -1.0, 1.0)
    phase_angle = np.arccos(cos_phase)

    return phase_angle


def lambertian_phase_function(phase_angle: float) -> float:
    """
    Compute Lambertian diffuse reflection phase function.

    Args:
        phase_angle: Phase angle in radians

    Returns:
        Phase function value (0 to 1)
    """
    # Lambertian sphere model
    # f(phi) = (2/3) * ((pi - phi)*cos(phi) + sin(phi)) / pi
    phi = phase_angle
    f = (2.0 / 3.0) * ((np.pi - phi) * np.cos(phi) + np.sin(phi)) / np.pi
    return max(0.0, f)


def simulate_magnitude(
    sat_position: np.ndarray,
    sun_position: np.ndarray,
    observer_position: np.ndarray,
    cross_section_m2: float,
    albedo: float = 0.2,
    elevation_deg: float = 90.0,
) -> float:
    """
    Simulate visual magnitude using phase angle geometry.

    Uses Lambertian diffuse reflection model with:
    1. Phase angle computation
    2. Diffuse reflection phase function
    3. Range^2 falloff
    4. Atmospheric extinction

    Args:
        sat_position: Satellite ECI position in km
        sun_position: Sun ECI position in km
        observer_position: Observer ECI position in km
        cross_section_m2: Satellite cross-sectional area in m^2
        albedo: Surface albedo (default 0.2 for typical spacecraft)
        elevation_deg: Elevation angle for extinction calculation

    Returns:
        Apparent visual magnitude
    """
    # Compute phase angle
    phase_angle = compute_phase_angle(sat_position, sun_position, observer_position)

    # Compute phase function
    phase_func = lambertian_phase_function(phase_angle)

    if phase_func <= 0:
        return np.inf  # Not illuminated

    # Range from observer to satellite (m)
    range_m = np.linalg.norm(sat_position - observer_position) * 1000

    # Cross section in m^2
    cross_section = cross_section_m2

    # Solar constant at 1 AU (W/m^2)
    solar_const = 1361.0

    # Distance from satellite to sun (convert to AU)
    sun_dist_km = np.linalg.norm(sun_position - sat_position)
    sun_dist_au = sun_dist_km / 149597870.7

    # Reflected power per steradian
    # P_reflected = albedo * cross_section * solar_const / sun_dist_au^2 * phase_func / pi
    reflected_intensity = (
        albedo * cross_section * solar_const * phase_func / (np.pi * sun_dist_au**2)
    )

    # Intensity at observer (W/m^2)
    intensity_at_observer = reflected_intensity / (4 * np.pi * range_m**2)

    # Convert to magnitude
    # Sun apparent magnitude = -26.74
    # Sun intensity at Earth ~ 1361 W/m^2
    sun_mag = -26.74
    sun_intensity = 1361.0  # W/m^2

    if intensity_at_observer <= 0:
        return np.inf

    mag = sun_mag - 2.5 * np.log10(intensity_at_observer / sun_intensity)

    # Atmospheric extinction
    if 0 < elevation_deg < 90:
        airmass = 1.0 / np.sin(np.radians(max(1.0, elevation_deg)))
        extinction_per_airmass = 0.2  # Typical V-band
        mag += extinction_per_airmass * airmass

    return mag


def get_sun_position_approx(obs_datetime) -> np.ndarray:
    """
    Get approximate Sun position in ECI frame.

    Uses simplified solar position calculation.

    Args:
        obs_datetime: Observation datetime

    Returns:
        Sun position vector in km (ECI frame)
    """
    # Days since J2000 epoch
    j2000 = np.datetime64("2000-01-01T12:00:00")
    days_since_j2000 = (np.datetime64(obs_datetime) - j2000) / np.timedelta64(1, "D")

    # Mean longitude of the Sun (degrees)
    L = 280.460 + 0.9856474 * days_since_j2000
    L = L % 360

    # Mean anomaly (degrees)
    g = 357.528 + 0.9856003 * days_since_j2000
    g = g % 360

    # Ecliptic longitude (degrees)
    g_rad = np.radians(g)
    ecliptic_lon = L + 1.915 * np.sin(g_rad) + 0.020 * np.sin(2 * g_rad)

    # Obliquity of ecliptic (degrees)
    obliquity = 23.439 - 0.0000004 * days_since_j2000

    # Convert to RA/Dec
    ecliptic_lon_rad = np.radians(ecliptic_lon)
    obliquity_rad = np.radians(obliquity)

    ra = np.arctan2(np.cos(obliquity_rad) * np.sin(ecliptic_lon_rad), np.cos(ecliptic_lon_rad))
    dec = np.arcsin(np.sin(obliquity_rad) * np.sin(ecliptic_lon_rad))

    # Distance to Sun (AU) - simplified
    r_au = 1.00014 - 0.01671 * np.cos(g_rad) - 0.00014 * np.cos(2 * g_rad)
    r_km = r_au * 149597870.7

    # Convert to ECI position
    x = r_km * np.cos(dec) * np.cos(ra)
    y = r_km * np.cos(dec) * np.sin(ra)
    z = r_km * np.sin(dec)

    return np.array([x, y, z])


def is_satellite_illuminated(
    sat_position: np.ndarray, sun_position: np.ndarray, earth_radius_km: float = 6378.137
) -> bool:
    """
    Check if satellite is illuminated (not in Earth's shadow).

    Uses cylindrical shadow model (simplified).

    Args:
        sat_position: Satellite ECI position in km
        sun_position: Sun ECI position in km
        earth_radius_km: Earth radius in km

    Returns:
        True if illuminated, False if in shadow
    """
    # Unit vector from Earth to Sun
    sun_dir = sun_position / np.linalg.norm(sun_position)

    # Project satellite position onto sun direction
    sat_projection = np.dot(sat_position, sun_dir)

    # If satellite is on sun side of Earth, it's illuminated
    if sat_projection > 0:
        return True

    # Distance from satellite to Earth-Sun line
    perp_dist = np.linalg.norm(sat_position - sat_projection * sun_dir)

    # If perpendicular distance > Earth radius, satellite is illuminated
    return perp_dist > earth_radius_km


# =============================================================================
# COMBINED NOISE APPLICATION
# =============================================================================


def apply_realistic_noise(
    ra: float,
    dec: float,
    obs_time,
    sensor_name: str = "GEODSS",
    config: SimulationConfig = None,
    rng: np.random.Generator = None,
) -> Tuple[float, float, float]:
    """
    Apply realistic sensor noise including all effects.

    Args:
        ra: Right Ascension in degrees
        dec: Declination in degrees
        obs_time: Observation time
        sensor_name: Sensor name for noise model selection
        config: Simulation configuration
        rng: Random number generator

    Returns:
        Tuple of (noisy_ra, noisy_dec, timing_offset_sec)
    """
    if config is None:
        config = SimulationConfig()

    if rng is None:
        rng = np.random.default_rng(config.seed)

    if not config.apply_sensor_noise:
        return ra, dec, 0.0

    # Get sensor model
    model = get_sensor_noise_model(config.sensor_model if config else sensor_name)

    if isinstance(model, OpticalNoiseModel):
        noisy_ra, noisy_dec, timing_offset = model.apply_noise(ra, dec, 0, rng)
        return noisy_ra, noisy_dec, timing_offset

    # Default case
    return ra, dec, 0.0
