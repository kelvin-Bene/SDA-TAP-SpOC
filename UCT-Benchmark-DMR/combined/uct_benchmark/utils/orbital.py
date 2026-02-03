# -*- coding: utf-8 -*-
"""
Orbital regime utilities.

Consolidated from duplicate implementations in:
- uct_benchmark/api/apiIntegration.py
- uct_benchmark/data/dataManipulation.py
"""

from uct_benchmark.settings import semiMajorAxis_GEO, semiMajorAxis_LEO


def determine_orbital_regime(semi_major_axis_km: float, eccentricity: float = 0.0) -> str:
    """
    Determine the orbital regime based on semi-major axis and eccentricity.

    Args:
        semi_major_axis_km: Semi-major axis in kilometers
        eccentricity: Orbital eccentricity (default 0)

    Returns:
        str: One of 'LEO', 'MEO', 'GEO', 'HEO'

    Examples:
        >>> determine_orbital_regime(7000, 0.0)
        'LEO'
        >>> determine_orbital_regime(20000, 0.0)
        'MEO'
        >>> determine_orbital_regime(42164, 0.0)
        'GEO'
        >>> determine_orbital_regime(20000, 0.75)
        'HEO'
    """
    if eccentricity >= 0.7:
        return "HEO"
    elif semi_major_axis_km < semiMajorAxis_LEO:
        return "LEO"
    elif semi_major_axis_km >= semiMajorAxis_GEO:
        return "GEO"
    else:
        return "MEO"
