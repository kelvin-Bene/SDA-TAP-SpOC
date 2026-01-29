"""
Coordinate and unit conversion utilities for UCTP Lab.

Provides conversions between angular coordinates, Cartesian states,
and various reference frames used in the pipeline.
"""

import numpy as np


def radec_to_unit_vector(ra_deg: float, dec_deg: float) -> np.ndarray:
    """Convert RA/Dec (degrees) to a unit direction vector in ECI."""
    ra = np.deg2rad(ra_deg)
    dec = np.deg2rad(dec_deg)
    return np.array([
        np.cos(dec) * np.cos(ra),
        np.cos(dec) * np.sin(ra),
        np.sin(dec),
    ])


def angular_separation_deg(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Compute angular separation between two RA/Dec points in degrees."""
    u1 = radec_to_unit_vector(ra1, dec1)
    u2 = radec_to_unit_vector(ra2, dec2)
    dot = np.clip(np.dot(u1, u2), -1.0, 1.0)
    return np.rad2deg(np.arccos(dot))


def great_circle_distance(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """
    Compute great-circle distance between two sky positions.

    Uses the Vincenty formula for numerical stability.

    Args:
        ra1, dec1, ra2, dec2: Coordinates in degrees.

    Returns:
        Angular distance in degrees.
    """
    ra1_r, dec1_r = np.deg2rad(ra1), np.deg2rad(dec1)
    ra2_r, dec2_r = np.deg2rad(ra2), np.deg2rad(dec2)
    dra = ra2_r - ra1_r

    num = np.sqrt(
        (np.cos(dec2_r) * np.sin(dra)) ** 2
        + (np.cos(dec1_r) * np.sin(dec2_r) - np.sin(dec1_r) * np.cos(dec2_r) * np.cos(dra)) ** 2
    )
    den = np.sin(dec1_r) * np.sin(dec2_r) + np.cos(dec1_r) * np.cos(dec2_r) * np.cos(dra)
    return np.rad2deg(np.arctan2(num, den))


def state_to_keplerian(state: np.ndarray, mu: float = 398600.4418) -> dict:
    """
    Convert a Cartesian state [x,y,z,vx,vy,vz] (km, km/s) to Keplerian elements.

    Returns:
        Dictionary with keys: a, e, i, raan, argp, nu (semi-major axis km,
        eccentricity, inclination deg, RAAN deg, argument of perigee deg,
        true anomaly deg).
    """
    r_vec = state[:3]
    v_vec = state[3:]
    r = np.linalg.norm(r_vec)
    v = np.linalg.norm(v_vec)

    # Specific angular momentum
    h_vec = np.cross(r_vec, v_vec)
    h = np.linalg.norm(h_vec)

    # Node vector
    k_hat = np.array([0, 0, 1])
    n_vec = np.cross(k_hat, h_vec)
    n = np.linalg.norm(n_vec)

    # Eccentricity vector
    e_vec = (1.0 / mu) * ((v**2 - mu / r) * r_vec - np.dot(r_vec, v_vec) * v_vec)
    e = np.linalg.norm(e_vec)

    # Specific energy -> semi-major axis
    energy = 0.5 * v**2 - mu / r
    a = -mu / (2 * energy) if energy != 0 else float("inf")

    # Inclination
    i = np.rad2deg(np.arccos(np.clip(h_vec[2] / h, -1, 1)))

    # RAAN
    raan = np.rad2deg(np.arctan2(n_vec[1], n_vec[0])) % 360 if n > 1e-10 else 0.0

    # Argument of perigee
    if n > 1e-10 and e > 1e-10:
        argp = np.rad2deg(np.arccos(np.clip(np.dot(n_vec, e_vec) / (n * e), -1, 1)))
        if e_vec[2] < 0:
            argp = 360 - argp
    else:
        argp = 0.0

    # True anomaly
    if e > 1e-10:
        nu = np.rad2deg(np.arccos(np.clip(np.dot(e_vec, r_vec) / (e * r), -1, 1)))
        if np.dot(r_vec, v_vec) < 0:
            nu = 360 - nu
    else:
        nu = 0.0

    return {"a": a, "e": e, "i": i, "raan": raan, "argp": argp, "nu": nu}


def compute_angular_rate(
    ra1: float, dec1: float, t1: float,
    ra2: float, dec2: float, t2: float,
) -> float:
    """
    Compute angular rate between two observations in deg/s.

    Args:
        ra1, dec1: First observation (degrees).
        t1: Time of first observation (seconds, e.g. Julian date * 86400).
        ra2, dec2: Second observation (degrees).
        t2: Time of second observation (seconds).

    Returns:
        Angular rate in degrees per second.
    """
    dt = abs(t2 - t1)
    if dt < 1e-10:
        return 0.0
    ang = great_circle_distance(ra1, dec1, ra2, dec2)
    return ang / dt
