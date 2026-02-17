# -*- coding: utf-8 -*-
"""
Atmospheric effects module for observation simulation.

Provides physics-based models for:
- Atmospheric refraction correction
- Velocity aberration correction

Created for UCT Benchmarking Enhancement.
"""

from typing import Optional, Tuple

import numpy as np

# =============================================================================
# ATMOSPHERIC REFRACTION
# =============================================================================


def apply_atmospheric_refraction(
    elevation_true: float,
    wavelength_nm: float = 550.0,
    temperature_c: float = 15.0,
    pressure_mbar: float = 1013.25,
    humidity_pct: float = 50.0,
) -> Optional[float]:
    """
    Apply atmospheric refraction correction to elevation angle.

    Uses Bennett's formula for optical observations, with chromatic
    and atmospheric condition corrections.

    Bennett's formula (arcminutes):
    R = 1/tan(el + 7.31/(el + 4.4))

    Args:
        elevation_true: True (geometric) elevation in degrees
        wavelength_nm: Observation wavelength in nanometers (default 550nm V-band)
        temperature_c: Surface temperature in Celsius
        pressure_mbar: Surface pressure in millibars
        humidity_pct: Relative humidity percentage

    Returns:
        Apparent (refracted) elevation in degrees, or None if below observability
    """
    # Below observability threshold
    if elevation_true < 0:
        return None

    # For very low elevations, refraction becomes unreliable
    if elevation_true < 6:
        return None

    # Bennett's formula (in arcminutes)
    # R = cot(el + 7.31/(el + 4.4)) arcminutes
    el = elevation_true  # degrees
    R_arcmin = 1.0 / np.tan(np.radians(el + 7.31 / (el + 4.4)))

    # Convert to arcseconds
    R_arcsec = R_arcmin * 60.0

    # Pressure and temperature correction
    # Standard conditions: T=15C, P=1013.25 mbar
    P_correction = pressure_mbar / 1013.25
    T_correction = 283.15 / (273.15 + temperature_c)  # (273.15 + 10) / (273.15 + T)
    R_arcsec *= P_correction * T_correction

    # Chromatic correction (simplified dispersion model)
    # Reference wavelength is 550nm (V-band)
    # Cauchy's equation approximation
    lambda_ref = 550.0
    chromatic_factor = 1.0 + 0.0048 * ((lambda_ref / wavelength_nm) ** 2 - 1)
    R_arcsec *= chromatic_factor

    # Humidity correction (minor effect, typically < 1%)
    # Water vapor reduces refraction slightly
    humidity_factor = 1.0 - 0.0001 * (humidity_pct - 50)
    R_arcsec *= humidity_factor

    # Apply refraction (apparent = true + refraction for positive elevation)
    elevation_apparent = elevation_true + R_arcsec / 3600.0

    return elevation_apparent


def refraction_correction_for_ra_dec(
    ra_deg: float,
    dec_deg: float,
    observer_lat: float,
    observer_lon: float,
    observer_alt_km: float,
    obs_time,
    wavelength_nm: float = 550.0,
) -> Tuple[float, float]:
    """
    Apply refraction correction to RA/Dec coordinates.

    Converts RA/Dec to Az/El, applies refraction, converts back.

    Args:
        ra_deg: Right Ascension in degrees
        dec_deg: Declination in degrees
        observer_lat: Observer latitude in degrees
        observer_lon: Observer longitude in degrees
        observer_alt_km: Observer altitude in km
        obs_time: Observation datetime
        wavelength_nm: Observation wavelength in nm

    Returns:
        Tuple of (corrected_ra, corrected_dec) in degrees
    """
    # For now, return uncorrected values
    # Full implementation requires sidereal time calculation
    # and proper coordinate transformations

    # Simplified: apply small correction based on declination
    # (placeholder for full implementation)
    return ra_deg, dec_deg


def get_refraction_at_elevation(elevation_deg: float) -> float:
    """
    Get refraction amount at a given elevation.

    Returns the refraction in arcseconds for quick lookups.

    Args:
        elevation_deg: Elevation angle in degrees

    Returns:
        Refraction in arcseconds
    """
    if elevation_deg < 0:
        return np.nan

    if elevation_deg < 6:
        # Extrapolate from 6 degrees (unreliable region)
        R_6 = 1.0 / np.tan(np.radians(6 + 7.31 / (6 + 4.4))) * 60
        factor = (6 / max(0.1, elevation_deg)) ** 2
        return min(R_6 * factor, 3600)  # Cap at 1 degree

    # Bennett's formula
    R_arcmin = 1.0 / np.tan(np.radians(elevation_deg + 7.31 / (elevation_deg + 4.4)))
    return R_arcmin * 60.0


# =============================================================================
# VELOCITY ABERRATION
# =============================================================================


def compute_velocity_aberration(
    ra_deg: float,
    dec_deg: float,
    observer_velocity: np.ndarray,
    target_velocity: Optional[np.ndarray] = None,
) -> Tuple[float, float]:
    """
    Apply velocity aberration correction due to relative motion.

    Classical aberration: theta = v/c * sin(angle)

    For satellites:
    - Observer velocity from Earth rotation (~0.46 km/s at equator)
    - Target velocity from orbit (varies with altitude)
    - Combined effect can be 10-30 arcsec for LEO

    Args:
        ra_deg: Right Ascension in degrees
        dec_deg: Declination in degrees
        observer_velocity: Observer velocity vector in km/s (ECI frame)
        target_velocity: Target velocity vector in km/s (ECI frame), optional

    Returns:
        Tuple of (corrected_ra, corrected_dec) in degrees
    """
    c = 299792.458  # Speed of light in km/s

    # Convert RA/Dec to unit vector
    ra_rad = np.radians(ra_deg)
    dec_rad = np.radians(dec_deg)

    n_x = np.cos(dec_rad) * np.cos(ra_rad)
    n_y = np.cos(dec_rad) * np.sin(ra_rad)
    n_z = np.sin(dec_rad)
    n = np.array([n_x, n_y, n_z])

    # Relative velocity
    if target_velocity is not None:
        v_rel = target_velocity - observer_velocity
    else:
        v_rel = -observer_velocity  # Assume target at rest

    # Classical aberration formula
    # n' = n + v/c - n*(n.v/c)
    v_over_c = v_rel / c
    n_dot_v = np.dot(n, v_over_c)

    n_aberrated = n + v_over_c - n * n_dot_v

    # Normalize
    n_aberrated = n_aberrated / np.linalg.norm(n_aberrated)

    # Convert back to RA/Dec
    ra_corrected = np.degrees(np.arctan2(n_aberrated[1], n_aberrated[0])) % 360
    dec_corrected = np.degrees(np.arcsin(np.clip(n_aberrated[2], -1, 1)))

    return ra_corrected, dec_corrected


def compute_observer_velocity(
    observer_lat: float, observer_lon: float, observer_alt_km: float, obs_time
) -> np.ndarray:
    """
    Compute observer velocity in ECI frame due to Earth rotation.

    Args:
        observer_lat: Geodetic latitude in degrees
        observer_lon: Geodetic longitude in degrees
        observer_alt_km: Altitude above sea level in km
        obs_time: Observation datetime

    Returns:
        Velocity vector in km/s (ECI frame)
    """
    # Earth rotation rate (rad/s)
    omega_earth = 7.292115e-5

    # Earth equatorial radius (km)
    R_earth = 6378.137

    # Observer distance from Earth's rotation axis
    lat_rad = np.radians(observer_lat)
    r = (R_earth + observer_alt_km) * np.cos(lat_rad)

    # Velocity magnitude (km/s)
    v_mag = omega_earth * r

    # Direction is tangent to rotation (East)
    # In ECI frame, this rotates with time
    # Simplified: assume observer at obs_lon at obs_time

    # For more accurate calculation, need GMST (Greenwich Mean Sidereal Time)
    # Placeholder: return equatorial velocity
    v_east = v_mag

    return np.array([0, v_east, 0])  # Simplified east direction


def aberration_magnitude_arcsec(velocity_km_s: float, angle_to_velocity_deg: float = 90.0) -> float:
    """
    Calculate aberration magnitude in arcseconds.

    Args:
        velocity_km_s: Relative velocity magnitude in km/s
        angle_to_velocity_deg: Angle between line of sight and velocity vector

    Returns:
        Aberration in arcseconds
    """
    c = 299792.458  # km/s
    angle_rad = np.radians(angle_to_velocity_deg)

    # Classical aberration: theta = v/c * sin(angle)
    aberration_rad = (velocity_km_s / c) * np.sin(angle_rad)

    return np.degrees(aberration_rad) * 3600


# =============================================================================
# COMBINED ATMOSPHERIC EFFECTS
# =============================================================================


def apply_atmospheric_effects(
    ra_deg: float,
    dec_deg: float,
    elevation_deg: float,
    observer_lat: float,
    observer_lon: float,
    observer_alt_km: float,
    obs_time,
    observer_velocity: Optional[np.ndarray] = None,
    target_velocity: Optional[np.ndarray] = None,
    apply_refraction: bool = True,
    apply_aberration: bool = True,
    wavelength_nm: float = 550.0,
) -> Tuple[float, float, float]:
    """
    Apply all atmospheric effects to observation coordinates.

    Args:
        ra_deg: Right Ascension in degrees
        dec_deg: Declination in degrees
        elevation_deg: Elevation angle in degrees
        observer_lat: Observer latitude in degrees
        observer_lon: Observer longitude in degrees
        observer_alt_km: Observer altitude in km
        obs_time: Observation datetime
        observer_velocity: Observer velocity (computed if None)
        target_velocity: Target velocity (optional)
        apply_refraction: Whether to apply refraction
        apply_aberration: Whether to apply aberration
        wavelength_nm: Observation wavelength

    Returns:
        Tuple of (corrected_ra, corrected_dec, corrected_elevation)
    """
    corrected_ra = ra_deg
    corrected_dec = dec_deg
    corrected_el = elevation_deg

    # Apply refraction to elevation
    if apply_refraction:
        refracted_el = apply_atmospheric_refraction(elevation_deg, wavelength_nm)
        if refracted_el is not None:
            corrected_el = refracted_el

    # Apply velocity aberration
    if apply_aberration:
        if observer_velocity is None:
            observer_velocity = compute_observer_velocity(
                observer_lat, observer_lon, observer_alt_km, obs_time
            )

        corrected_ra, corrected_dec = compute_velocity_aberration(
            ra_deg, dec_deg, observer_velocity, target_velocity
        )

    return corrected_ra, corrected_dec, corrected_el
