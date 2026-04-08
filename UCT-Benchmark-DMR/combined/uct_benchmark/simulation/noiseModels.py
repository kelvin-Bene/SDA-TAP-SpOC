# -*- coding: utf-8 -*-
"""
Physical Noise Models for Observation Simulation

This module implements physically realistic noise models as described by Lewis.
The noise is NOT isotropic (random) but depends on:
1. Viewing angle (elevation) - atmospheric path length
2. Atmospheric conditions (seeing) - turbulence
3. Sensor location and characteristics
4. Object brightness and background

Lewis (transcript): "The noise is not completely random. It's dependent on
viewing angle, atmospheric conditions, viewing location, a lot of different things."

Author: UCT Benchmark Team
Date: 2026
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple

import numpy as np
from loguru import logger


class SensorType(Enum):
    """Types of sensors for noise modeling."""
    OPTICAL_GROUND = "optical_ground"      # Ground-based optical telescope
    OPTICAL_SPACE = "optical_space"        # Space-based optical sensor
    RADAR_GROUND = "radar_ground"          # Ground-based radar
    RADAR_SPACE = "radar_space"            # Space-based radar
    PASSIVE_RF = "passive_rf"              # Passive RF detection


@dataclass
class AtmosphericConditions:
    """Atmospheric conditions affecting observation quality."""

    # Seeing (arcseconds) - atmospheric turbulence
    # Good: < 1", Average: 1-2", Poor: > 2"
    seeing_arcsec: float = 1.5

    # Transparency (0-1) - atmospheric clarity
    # 1.0 = perfectly clear, 0.5 = thin clouds, 0.0 = opaque
    transparency: float = 0.9

    # Humidity (0-1)
    humidity: float = 0.3

    # Temperature (Celsius)
    temperature_c: float = 15.0

    # Pressure (hPa)
    pressure_hpa: float = 1013.25

    # Wind speed (m/s) - affects dome seeing
    wind_speed_ms: float = 5.0


@dataclass
class SensorCharacteristics:
    """Physical characteristics of the observing sensor."""

    sensor_type: SensorType = SensorType.OPTICAL_GROUND
    name: str = "Generic"

    # Location
    latitude_deg: float = 0.0
    longitude_deg: float = 0.0
    altitude_m: float = 0.0

    # Optical characteristics
    aperture_m: float = 1.0           # Telescope aperture in meters
    focal_length_m: float = 10.0      # Focal length in meters
    pixel_scale_arcsec: float = 1.0   # Arcseconds per pixel

    # Pointing accuracy
    pointing_accuracy_arcsec: float = 1.0
    tracking_accuracy_arcsec_per_sec: float = 0.1

    # Timing accuracy
    timing_accuracy_ms: float = 1.0

    # Detection limits
    limiting_magnitude: float = 18.0
    saturation_magnitude: float = 6.0

    # Systematic biases (arcseconds)
    systematic_bias_ra: float = 0.0
    systematic_bias_dec: float = 0.0


@dataclass
class NoiseModel:
    """Complete noise model for an observation."""

    # Random noise components (1-sigma, arcseconds)
    angular_noise_ra_arcsec: float = 1.0
    angular_noise_dec_arcsec: float = 1.0

    # Systematic biases (arcseconds)
    systematic_bias_ra_arcsec: float = 0.0
    systematic_bias_dec_arcsec: float = 0.0

    # Timing noise (milliseconds)
    timing_noise_ms: float = 1.0

    # Position noise (for radar, km)
    position_noise_km: float = 0.01

    # Correlation between RA and Dec errors
    correlation_ra_dec: float = 0.0

    # Contributing factors
    factors: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# ATMOSPHERIC EFFECTS
# =============================================================================


def compute_airmass(elevation_deg: float) -> float:
    """
    Compute atmospheric airmass for a given elevation angle.

    Airmass represents the relative path length through the atmosphere.
    At zenith (90 deg), airmass = 1. At horizon (0 deg), airmass = ~38.

    Uses the Kasten & Young (1989) formula for accurate results at low elevations.

    Args:
        elevation_deg: Elevation angle above horizon in degrees

    Returns:
        Airmass (dimensionless)
    """
    if elevation_deg <= 0:
        return float("inf")

    # Kasten & Young (1989) formula
    zenith_angle_deg = 90.0 - elevation_deg
    zenith_angle_rad = np.radians(zenith_angle_deg)

    # Avoid division by zero near horizon
    if zenith_angle_deg >= 90:
        return 38.0  # Maximum practical airmass

    airmass = 1.0 / (
        np.cos(zenith_angle_rad) +
        0.50572 * (96.07995 - zenith_angle_deg) ** (-1.6364)
    )

    return min(airmass, 38.0)


def compute_atmospheric_refraction(
    elevation_deg: float,
    temperature_c: float = 15.0,
    pressure_hpa: float = 1013.25,
) -> float:
    """
    Compute atmospheric refraction correction.

    Atmospheric refraction makes objects appear higher than they actually are.
    This is a systematic effect that should be corrected, but residual errors
    contribute to noise.

    Uses the Bennett (1982) formula.

    Args:
        elevation_deg: Apparent elevation in degrees
        temperature_c: Temperature in Celsius
        pressure_hpa: Pressure in hectopascals

    Returns:
        Refraction correction in arcseconds
    """
    if elevation_deg <= 0:
        return 0.0

    # Bennett formula (arcminutes)
    h = elevation_deg
    R_arcmin = 1.0 / np.tan(np.radians(h + 7.31 / (h + 4.4)))

    # Convert to arcseconds and apply pressure/temperature correction
    R_arcsec = R_arcmin * 60.0
    R_arcsec *= (pressure_hpa / 1010.0) * (283.0 / (273.0 + temperature_c))

    return R_arcsec


def compute_seeing_at_elevation(
    zenith_seeing_arcsec: float,
    elevation_deg: float,
) -> float:
    """
    Compute seeing at a given elevation angle.

    Seeing degrades with increasing airmass (lower elevation).
    Follows a power law: seeing ~ seeing_zenith * airmass^0.6

    Args:
        zenith_seeing_arcsec: Seeing at zenith in arcseconds
        elevation_deg: Elevation angle in degrees

    Returns:
        Seeing at given elevation in arcseconds
    """
    airmass = compute_airmass(elevation_deg)

    if airmass == float("inf"):
        return float("inf")

    # Fried's law: seeing ~ airmass^0.6
    return zenith_seeing_arcsec * (airmass ** 0.6)


def compute_scintillation_noise(
    elevation_deg: float,
    aperture_m: float,
    exposure_time_sec: float = 1.0,
) -> float:
    """
    Compute scintillation (twinkling) noise contribution.

    Scintillation causes rapid brightness fluctuations that affect
    centroid determination. Larger apertures average out scintillation better.

    Args:
        elevation_deg: Elevation angle in degrees
        aperture_m: Telescope aperture in meters
        exposure_time_sec: Exposure time in seconds

    Returns:
        Scintillation-induced position noise in arcseconds
    """
    airmass = compute_airmass(elevation_deg)

    if airmass == float("inf"):
        return float("inf")

    # Dravins et al. (1998) formula for scintillation index
    # sigma_I / I ~ 0.09 * D^(-2/3) * X^(1.75) * exp(-h/8000) * t^(-0.5)
    # Simplified for sea-level observatory

    sigma_scint = 0.09 * (aperture_m ** (-2/3)) * (airmass ** 1.75) * (exposure_time_sec ** (-0.5))

    # Convert intensity fluctuation to position uncertainty (empirical)
    # ~0.1 arcsec per 1% intensity variation for well-sampled PSF
    position_noise_arcsec = sigma_scint * 10.0  # Very rough approximation

    return position_noise_arcsec


# =============================================================================
# SENSOR-SPECIFIC NOISE
# =============================================================================


def compute_optical_noise(
    elevation_deg: float,
    sensor: SensorCharacteristics,
    atmosphere: AtmosphericConditions,
    object_magnitude: float = 12.0,
    exposure_time_sec: float = 1.0,
) -> Tuple[float, float, Dict]:
    """
    Compute noise for optical ground-based observations.

    Combines multiple noise sources:
    1. Atmospheric seeing (dominant at low elevation)
    2. Scintillation
    3. Photon noise (depends on object brightness)
    4. Detector noise
    5. Pointing/tracking errors

    Args:
        elevation_deg: Elevation angle in degrees
        sensor: Sensor characteristics
        atmosphere: Atmospheric conditions
        object_magnitude: Visual magnitude of object
        exposure_time_sec: Exposure time in seconds

    Returns:
        Tuple of (noise_ra_arcsec, noise_dec_arcsec, factors_dict)
    """
    factors = {}

    # 1. Seeing contribution
    seeing = compute_seeing_at_elevation(atmosphere.seeing_arcsec, elevation_deg)
    # Centroid precision ~ seeing / SNR, assume SNR ~ 10-100
    snr = max(5, 100 * 10 ** ((sensor.limiting_magnitude - object_magnitude) / 2.5))
    seeing_noise = seeing / snr
    factors["seeing"] = seeing_noise

    # 2. Scintillation contribution
    scint_noise = compute_scintillation_noise(
        elevation_deg, sensor.aperture_m, exposure_time_sec
    )
    factors["scintillation"] = scint_noise

    # 3. Pointing/tracking errors
    tracking_noise = sensor.tracking_accuracy_arcsec_per_sec * exposure_time_sec
    factors["tracking"] = tracking_noise

    # 4. Pixel scale contribution (sampling noise)
    # Centroid precision ~ pixel_scale / sqrt(12) for well-sampled PSF
    pixel_noise = sensor.pixel_scale_arcsec / np.sqrt(12)
    factors["pixel_sampling"] = pixel_noise

    # 5. Atmospheric refraction residuals (systematic, ~10% of refraction)
    refraction = compute_atmospheric_refraction(
        elevation_deg, atmosphere.temperature_c, atmosphere.pressure_hpa
    )
    refraction_residual = 0.1 * refraction / 3600  # 10% residual, convert to degrees
    factors["refraction_residual"] = refraction_residual * 3600  # Back to arcsec for factors

    # Combine noise sources in quadrature
    total_noise = np.sqrt(
        seeing_noise ** 2 +
        scint_noise ** 2 +
        tracking_noise ** 2 +
        pixel_noise ** 2
    )

    # Elevation-dependent anisotropy
    # Declination noise is typically larger at low elevations due to
    # differential refraction
    airmass = compute_airmass(elevation_deg)
    dec_multiplier = 1.0 + 0.1 * (airmass - 1)  # 10% increase per airmass

    noise_ra = total_noise
    noise_dec = total_noise * dec_multiplier

    factors["total_ra"] = noise_ra
    factors["total_dec"] = noise_dec
    factors["airmass"] = airmass
    factors["elevation_deg"] = elevation_deg

    return noise_ra, noise_dec, factors


def compute_space_optical_noise(
    sensor: SensorCharacteristics,
    object_magnitude: float = 12.0,
    exposure_time_sec: float = 1.0,
) -> Tuple[float, float, Dict]:
    """
    Compute noise for space-based optical observations.

    Space-based sensors don't have atmospheric effects but have:
    1. Pointing jitter
    2. Photon noise
    3. Detector effects

    Args:
        sensor: Sensor characteristics
        object_magnitude: Visual magnitude of object
        exposure_time_sec: Exposure time in seconds

    Returns:
        Tuple of (noise_ra_arcsec, noise_dec_arcsec, factors_dict)
    """
    factors = {}

    # No atmospheric effects, but still have:
    # 1. Pointing stability
    pointing_noise = sensor.pointing_accuracy_arcsec
    factors["pointing"] = pointing_noise

    # 2. Photon noise (simplified)
    snr = max(10, 100 * 10 ** ((sensor.limiting_magnitude - object_magnitude) / 2.5))
    photon_noise = sensor.pixel_scale_arcsec / snr
    factors["photon"] = photon_noise

    # 3. Pixel sampling
    pixel_noise = sensor.pixel_scale_arcsec / np.sqrt(12)
    factors["pixel_sampling"] = pixel_noise

    total_noise = np.sqrt(pointing_noise ** 2 + photon_noise ** 2 + pixel_noise ** 2)

    factors["total"] = total_noise

    return total_noise, total_noise, factors


def compute_radar_noise(
    elevation_deg: float,
    range_km: float,
    sensor: SensorCharacteristics,
) -> Tuple[float, float, float, Dict]:
    """
    Compute noise for radar observations.

    Radar noise depends on:
    1. Range (signal strength decreases with R^4)
    2. Elevation (atmospheric attenuation)
    3. System characteristics

    Args:
        elevation_deg: Elevation angle in degrees
        range_km: Slant range to object in km
        sensor: Sensor characteristics

    Returns:
        Tuple of (range_noise_km, range_rate_noise_km_s, angular_noise_deg, factors_dict)
    """
    factors = {}

    # Range noise increases with range
    # Typical: ~10m at 1000km, scaling with range
    base_range_noise_m = 10.0
    range_noise_m = base_range_noise_m * (range_km / 1000) ** 0.5
    range_noise_km = range_noise_m / 1000
    factors["range_noise_km"] = range_noise_km

    # Range rate noise (Doppler)
    range_rate_noise_m_s = 0.01 * (range_km / 1000) ** 0.25
    factors["range_rate_noise_m_s"] = range_rate_noise_m_s

    # Angular noise (typically worse than optical)
    angular_noise_deg = 0.01 * compute_airmass(elevation_deg) ** 0.3
    factors["angular_noise_deg"] = angular_noise_deg

    factors["range_km"] = range_km
    factors["elevation_deg"] = elevation_deg

    return range_noise_km, range_rate_noise_m_s, angular_noise_deg, factors


# =============================================================================
# MAIN NOISE COMPUTATION FUNCTION
# =============================================================================


def compute_physical_noise(
    elevation_deg: float,
    sensor: SensorCharacteristics = None,
    atmosphere: AtmosphericConditions = None,
    object_magnitude: float = 12.0,
    exposure_time_sec: float = 1.0,
    range_km: float = None,
) -> NoiseModel:
    """
    Compute physically realistic noise for an observation.

    This is the main entry point that replaces isotropic noise with
    a physical model based on observing conditions.

    Args:
        elevation_deg: Elevation angle above horizon in degrees
        sensor: Sensor characteristics (uses defaults if None)
        atmosphere: Atmospheric conditions (uses defaults if None)
        object_magnitude: Visual magnitude of object
        exposure_time_sec: Exposure time in seconds
        range_km: Slant range for radar observations

    Returns:
        NoiseModel with all noise components
    """
    if sensor is None:
        sensor = SensorCharacteristics()

    if atmosphere is None:
        atmosphere = AtmosphericConditions()

    model = NoiseModel()

    if sensor.sensor_type == SensorType.OPTICAL_GROUND:
        noise_ra, noise_dec, factors = compute_optical_noise(
            elevation_deg, sensor, atmosphere, object_magnitude, exposure_time_sec
        )
        model.angular_noise_ra_arcsec = noise_ra
        model.angular_noise_dec_arcsec = noise_dec
        model.timing_noise_ms = sensor.timing_accuracy_ms
        model.systematic_bias_ra_arcsec = sensor.systematic_bias_ra
        model.systematic_bias_dec_arcsec = sensor.systematic_bias_dec
        model.factors = factors

    elif sensor.sensor_type == SensorType.OPTICAL_SPACE:
        noise_ra, noise_dec, factors = compute_space_optical_noise(
            sensor, object_magnitude, exposure_time_sec
        )
        model.angular_noise_ra_arcsec = noise_ra
        model.angular_noise_dec_arcsec = noise_dec
        model.timing_noise_ms = sensor.timing_accuracy_ms
        model.factors = factors

    elif sensor.sensor_type in [SensorType.RADAR_GROUND, SensorType.RADAR_SPACE]:
        if range_km is None:
            range_km = 1000.0  # Default range
        range_noise, rr_noise, ang_noise, factors = compute_radar_noise(
            elevation_deg, range_km, sensor
        )
        model.position_noise_km = range_noise
        model.angular_noise_ra_arcsec = ang_noise * 3600
        model.angular_noise_dec_arcsec = ang_noise * 3600
        model.factors = factors

    else:
        # Default to simple optical model
        noise_ra, noise_dec, factors = compute_optical_noise(
            elevation_deg, sensor, atmosphere, object_magnitude, exposure_time_sec
        )
        model.angular_noise_ra_arcsec = noise_ra
        model.angular_noise_dec_arcsec = noise_dec
        model.factors = factors

    return model


def apply_physical_noise(
    ra_true: float,
    dec_true: float,
    elevation_deg: float,
    sensor: SensorCharacteristics = None,
    atmosphere: AtmosphericConditions = None,
    rng: np.random.Generator = None,
) -> Tuple[float, float, NoiseModel]:
    """
    Apply physically realistic noise to true RA/Dec values.

    This replaces the isotropic noise in the original simulation code.

    Args:
        ra_true: True right ascension in degrees
        dec_true: True declination in degrees
        elevation_deg: Elevation angle in degrees
        sensor: Sensor characteristics
        atmosphere: Atmospheric conditions
        rng: Random number generator

    Returns:
        Tuple of (ra_observed, dec_observed, noise_model)
    """
    if rng is None:
        rng = np.random.default_rng()

    # Compute noise model
    noise = compute_physical_noise(elevation_deg, sensor, atmosphere)

    # Apply random noise (Gaussian)
    # Convert arcseconds to degrees
    ra_noise_deg = rng.normal(0, noise.angular_noise_ra_arcsec / 3600)
    dec_noise_deg = rng.normal(0, noise.angular_noise_dec_arcsec / 3600)

    # Apply systematic biases
    ra_bias_deg = noise.systematic_bias_ra_arcsec / 3600
    dec_bias_deg = noise.systematic_bias_dec_arcsec / 3600

    # Compute observed values
    ra_obs = ra_true + ra_noise_deg + ra_bias_deg
    dec_obs = dec_true + dec_noise_deg + dec_bias_deg

    # Handle RA wraparound
    ra_obs = ra_obs % 360.0

    # Clamp Dec to valid range
    dec_obs = np.clip(dec_obs, -90.0, 90.0)

    return ra_obs, dec_obs, noise


# =============================================================================
# PREDEFINED SENSOR PROFILES
# =============================================================================

# These match the SENSOR_NOISE_MODELS in settings.py but with full physics

GEODSS_SENSOR = SensorCharacteristics(
    sensor_type=SensorType.OPTICAL_GROUND,
    name="GEODSS",
    aperture_m=1.0,
    focal_length_m=2.2,
    pixel_scale_arcsec=2.0,
    pointing_accuracy_arcsec=0.5,
    tracking_accuracy_arcsec_per_sec=0.1,
    timing_accuracy_ms=1.0,
    limiting_magnitude=16.5,
    systematic_bias_ra=0.1,
    systematic_bias_dec=0.05,
)

SBSS_SENSOR = SensorCharacteristics(
    sensor_type=SensorType.OPTICAL_SPACE,
    name="SBSS",
    aperture_m=0.3,
    focal_length_m=1.5,
    pixel_scale_arcsec=1.5,
    pointing_accuracy_arcsec=0.3,
    tracking_accuracy_arcsec_per_sec=0.05,
    timing_accuracy_ms=0.5,
    limiting_magnitude=15.0,
    systematic_bias_ra=0.05,
    systematic_bias_dec=0.02,
)

COMMERCIAL_EO_SENSOR = SensorCharacteristics(
    sensor_type=SensorType.OPTICAL_GROUND,
    name="Commercial_EO",
    aperture_m=0.5,
    focal_length_m=1.0,
    pixel_scale_arcsec=3.0,
    pointing_accuracy_arcsec=1.0,
    tracking_accuracy_arcsec_per_sec=0.2,
    timing_accuracy_ms=5.0,
    limiting_magnitude=14.0,
    systematic_bias_ra=0.2,
    systematic_bias_dec=0.1,
)

RADAR_SENSOR = SensorCharacteristics(
    sensor_type=SensorType.RADAR_GROUND,
    name="Radar",
    pointing_accuracy_arcsec=36.0,  # 0.01 degrees
    timing_accuracy_ms=0.1,
)

# Sensor lookup dictionary
SENSOR_PROFILES = {
    "GEODSS": GEODSS_SENSOR,
    "SBSS": SBSS_SENSOR,
    "Commercial_EO": COMMERCIAL_EO_SENSOR,
    "Radar": RADAR_SENSOR,
}


def get_sensor_profile(sensor_name: str) -> SensorCharacteristics:
    """Get a predefined sensor profile by name."""
    return SENSOR_PROFILES.get(sensor_name, GEODSS_SENSOR)


# =============================================================================
# CALIBRATED ATMOSPHERIC SEEING (Smear Explanation reference)
# =============================================================================

# Atmospheric seeing percentiles in arcseconds, calibrated against
# 518,092 real observations from Muztagh-ata Site II + Lijiang Observatory,
# plus reference values from Maidanek (best) and Antarctic stations (worst).
#
# Source: provided-materials/UCT Benchmarking/Measurement Simulation/
#         Smear Explanation, Results, Documentation.docx (Binyamin Stivi).
# Louis Caves explicitly cited this research in the Aug 28 2025 SDATap
# meeting as the calibration the simulator should be using instead of
# the constant 1 arcsec Gaussian default.
SMEAR_SEEING_PERCENTILES_ARCSEC = {
    "best":       0.25,    # Maidanek observatory, "best reasonable"
    "good_day":   0.30,    # 75th percentile (better than 75% of days)
    "median":     0.375,   # 50th percentile / "OK day"
    "bad_day":    0.4875,  # 25th percentile (worse than 75% of days)
    "really_bad": 0.70,    # 10th percentile (worse than 90% of days)
    "worst":      1.32,    # Antarctic stations, worst recorded
}


def sample_smear_seeing_arcsec(
    rng=None,
    bias: str = "median",
) -> float:
    """Sample atmospheric seeing in arcseconds from the Smear percentile chart.

    Args:
        rng: numpy random Generator for sampling. When None, returns the
            ``bias`` percentile deterministically. Useful for tests and for
            anchoring an entire simulation run at a known seeing level.
        bias: which percentile to anchor on when ``rng`` is None. One of
            'best', 'good_day', 'median' (default), 'bad_day', 'really_bad',
            'worst'.

    Returns:
        Seeing sigma in arcseconds, suitable for
        ``AtmosphericConditions.seeing_arcsec``.
    """
    if rng is None:
        return SMEAR_SEEING_PERCENTILES_ARCSEC[bias]

    # Right-skewed empirical distribution: most days are good, occasional
    # bad days. Matches the Lijiang FWHM histogram described in the Smear
    # doc as "noticeably skew right".
    levels = ["best", "good_day", "median", "bad_day", "really_bad", "worst"]
    weights = [0.10, 0.25, 0.35, 0.20, 0.07, 0.03]  # sums to 1.0
    pick = rng.choice(levels, p=weights)
    return SMEAR_SEEING_PERCENTILES_ARCSEC[pick]
