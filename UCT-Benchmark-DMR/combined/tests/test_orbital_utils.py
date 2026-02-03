# -*- coding: utf-8 -*-
"""Tests for orbital regime determination utilities."""

import pytest


class TestDetermineOrbitalRegime:
    """Tests for determine_orbital_regime function."""

    def test_import_from_utils(self):
        """Verify function can be imported from uct_benchmark.utils."""
        from uct_benchmark.utils import determine_orbital_regime

        assert callable(determine_orbital_regime)

    def test_import_from_orbital_module(self):
        """Verify function can be imported from orbital module directly."""
        from uct_benchmark.utils.orbital import determine_orbital_regime

        assert callable(determine_orbital_regime)

    @pytest.mark.parametrize(
        "sma,ecc,expected",
        [
            # LEO cases - below semiMajorAxis_LEO (8378 km)
            (7000, 0.0, "LEO"),  # Typical LEO
            (6700, 0.0, "LEO"),  # Low LEO
            (8000, 0.0, "LEO"),  # High LEO
            (8377, 0.0, "LEO"),  # Just below LEO threshold
            # MEO cases - between LEO and GEO thresholds
            (8378, 0.0, "MEO"),  # Just at LEO threshold (becomes MEO)
            (20000, 0.0, "MEO"),  # Typical MEO
            (26000, 0.0, "MEO"),  # GPS altitude
            (42163, 0.0, "MEO"),  # Just below GEO
            # GEO cases - at or above semiMajorAxis_GEO (42164 km)
            (42164, 0.0, "GEO"),  # At GEO threshold
            (42165, 0.0, "GEO"),  # Just above GEO
            (45000, 0.0, "GEO"),  # Super-GEO
            # HEO cases - high eccentricity (>= 0.7)
            (20000, 0.75, "HEO"),  # HEO in MEO altitude range
            (7000, 0.8, "HEO"),  # HEO in LEO altitude range
            (42164, 0.7, "HEO"),  # HEO at GEO altitude
            (50000, 0.9, "HEO"),  # Very eccentric
        ],
    )
    def test_orbital_regime_classification(self, sma, ecc, expected):
        """Test orbital regime classification with various inputs."""
        from uct_benchmark.utils.orbital import determine_orbital_regime

        result = determine_orbital_regime(sma, ecc)
        assert result == expected, f"Expected {expected} for SMA={sma}, e={ecc}, got {result}"

    def test_default_eccentricity(self):
        """Test that eccentricity defaults to 0.0."""
        from uct_benchmark.utils.orbital import determine_orbital_regime

        # Without eccentricity parameter, should behave as if e=0
        result_with_default = determine_orbital_regime(7000)
        result_with_explicit = determine_orbital_regime(7000, 0.0)
        assert result_with_default == result_with_explicit == "LEO"

    def test_eccentricity_boundary(self):
        """Test the exact eccentricity boundary (0.7) for HEO classification."""
        from uct_benchmark.utils.orbital import determine_orbital_regime

        # Just below HEO threshold
        assert determine_orbital_regime(20000, 0.69) == "MEO"
        # At HEO threshold
        assert determine_orbital_regime(20000, 0.70) == "HEO"
        # Above HEO threshold
        assert determine_orbital_regime(20000, 0.71) == "HEO"

    def test_heo_takes_priority(self):
        """Verify HEO classification takes priority over altitude-based classification."""
        from uct_benchmark.utils.orbital import determine_orbital_regime

        # Even at GEO altitude, high eccentricity should classify as HEO
        assert determine_orbital_regime(42164, 0.7) == "HEO"
        # Even at LEO altitude, high eccentricity should classify as HEO
        assert determine_orbital_regime(6700, 0.8) == "HEO"
