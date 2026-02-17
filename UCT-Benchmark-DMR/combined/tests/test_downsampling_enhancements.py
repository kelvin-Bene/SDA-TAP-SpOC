# -*- coding: utf-8 -*-
"""
Tests for enhanced downsampling functionality.

Tests:
- Regime-specific downsampling
- Track identification and preservation
- 3D coverage calculation
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest


class TestRegimeDetection:
    """Tests for orbital regime detection in downsampling."""

    def test_determine_leo(self):
        """Test LEO detection."""
        from uct_benchmark.data.dataManipulation import determine_orbital_regime

        regime = determine_orbital_regime(7000)
        assert regime == "LEO"

    def test_determine_meo(self):
        """Test MEO detection."""
        from uct_benchmark.data.dataManipulation import determine_orbital_regime

        regime = determine_orbital_regime(20000)
        assert regime == "MEO"

    def test_determine_geo(self):
        """Test GEO detection."""
        from uct_benchmark.data.dataManipulation import determine_orbital_regime

        regime = determine_orbital_regime(42200)
        assert regime == "GEO"

    def test_determine_heo(self):
        """Test HEO detection by eccentricity."""
        from uct_benchmark.data.dataManipulation import determine_orbital_regime

        regime = determine_orbital_regime(26000, 0.75)
        assert regime == "HEO"

    def test_get_regime_profile(self):
        """Test getting regime profile."""
        from uct_benchmark.data.dataManipulation import get_regime_profile

        leo_profile = get_regime_profile("LEO")
        geo_profile = get_regime_profile("GEO")

        # GEO should have higher min coverage due to longer visibility
        assert geo_profile["min_coverage_pct"] > leo_profile["min_coverage_pct"]


class TestTrackIdentification:
    """Tests for track identification."""

    def test_identify_tracks_single_track(self):
        """Test identifying a single continuous track."""
        from uct_benchmark.data.dataManipulation import identify_tracks

        # Create observations within 90 minutes
        base_time = datetime(2025, 1, 15, 12, 0, 0)
        obs_df = pd.DataFrame(
            {
                "obTime": [base_time + timedelta(minutes=i * 10) for i in range(5)],
                "satNo": [25544] * 5,
                "idSensor": ["SEN001"] * 5,
                "ra": [100.0 + i for i in range(5)],
                "declination": [20.0] * 5,
            }
        )

        tracks = identify_tracks(obs_df)
        assert len(tracks) == 1
        assert len(tracks[0]) == 5

    def test_identify_tracks_multiple_tracks(self):
        """Test identifying multiple tracks with gaps."""
        from uct_benchmark.data.dataManipulation import identify_tracks

        base_time = datetime(2025, 1, 15, 12, 0, 0)

        # First track
        times1 = [base_time + timedelta(minutes=i * 10) for i in range(3)]
        # Second track (after 2 hour gap)
        times2 = [base_time + timedelta(hours=3, minutes=i * 10) for i in range(3)]

        obs_df = pd.DataFrame(
            {
                "obTime": times1 + times2,
                "satNo": [25544] * 6,
                "idSensor": ["SEN001"] * 6,
                "ra": [100.0 + i for i in range(6)],
                "declination": [20.0] * 6,
            }
        )

        tracks = identify_tracks(obs_df)
        assert len(tracks) == 2

    def test_identify_tracks_empty_df(self):
        """Test with empty DataFrame."""
        from uct_benchmark.data.dataManipulation import identify_tracks

        obs_df = pd.DataFrame(columns=["obTime", "satNo", "idSensor"])
        tracks = identify_tracks(obs_df)
        assert len(tracks) == 0


class TestTrackPreservation:
    """Tests for track-preserving downsampling."""

    def test_thin_within_tracks(self):
        """Test thinning observations within tracks."""
        from uct_benchmark.data.dataManipulation import thin_within_tracks

        # Create a track with 10 observations
        base_time = datetime(2025, 1, 15, 12, 0, 0)
        track = pd.DataFrame(
            {
                "obTime": [base_time + timedelta(seconds=i * 30) for i in range(10)],
                "satNo": [25544] * 10,
                "ra": [100.0 + i * 0.1 for i in range(10)],
                "declination": [20.0] * 10,
                "id": [f"obs_{i}" for i in range(10)],
            }
        )

        tracks = [track]
        rng = np.random.default_rng(42)

        # Thin to 3-5 obs per track
        result = thin_within_tracks(tracks, (3, 5), preserve_boundaries=True, rng=rng)

        assert len(result) >= 3
        assert len(result) <= 5

    def test_preserve_boundaries(self):
        """Test that first and last observations are preserved."""
        from uct_benchmark.data.dataManipulation import thin_within_tracks

        base_time = datetime(2025, 1, 15, 12, 0, 0)
        track = pd.DataFrame(
            {
                "obTime": [base_time + timedelta(seconds=i * 30) for i in range(10)],
                "satNo": [25544] * 10,
                "id": [f"obs_{i}" for i in range(10)],
            }
        )

        tracks = [track]
        rng = np.random.default_rng(42)

        result = thin_within_tracks(tracks, (3, 5), preserve_boundaries=True, rng=rng)

        # First and last should be preserved
        result_ids = result["id"].tolist()
        assert "obs_0" in result_ids
        assert "obs_9" in result_ids


class TestCoverageCalculation:
    """Tests for 3D orbital coverage calculation."""

    def test_compute_arc_coverage_full(self):
        """Test arc coverage with full orbit coverage."""
        from uct_benchmark.data.dataManipulation import compute_arc_coverage

        # Observations uniformly distributed around orbit
        anomalies = np.linspace(0, 2 * np.pi, 36)  # Every 10 degrees
        coverage = compute_arc_coverage(anomalies)

        assert coverage > 0.8  # Should be high coverage

    def test_compute_arc_coverage_partial(self):
        """Test arc coverage with partial orbit coverage."""
        from uct_benchmark.data.dataManipulation import compute_arc_coverage

        # Observations only in one quarter
        anomalies = np.linspace(0, np.pi / 2, 10)
        coverage = compute_arc_coverage(anomalies)

        # Quarter orbit should have coverage <= 50%
        assert coverage <= 0.5

    def test_compute_arc_coverage_sparse(self):
        """Test arc coverage with sparse observations."""
        from uct_benchmark.data.dataManipulation import compute_arc_coverage

        # Only 2 observations
        anomalies = np.array([0, np.pi])
        coverage = compute_arc_coverage(anomalies)

        assert coverage >= 0


class TestRegimeSpecificDownsampling:
    """Tests for regime-specific downsampling."""

    def test_downsample_by_regime_returns_dataframe(self):
        """Test that downsample_by_regime returns a DataFrame."""
        from uct_benchmark.data.dataManipulation import downsample_by_regime
        from uct_benchmark.settings import DownsampleConfig

        # Create test data
        base_time = datetime(2025, 1, 15, 12, 0, 0)
        obs_df = pd.DataFrame(
            {
                "obTime": [base_time + timedelta(minutes=i) for i in range(100)],
                "satNo": [25544] * 100,
                "ra": [100.0 + i * 0.1 for i in range(100)],
                "declination": [20.0] * 100,
                "id": [f"obs_{i}" for i in range(100)],
                "idSensor": ["SEN001"] * 100,
                "senlat": [30.0] * 100,
                "senlon": [-100.0] * 100,
            }
        )

        sat_params = {
            25544: {
                "Semi-Major Axis": 6800,
                "Eccentricity": 0.001,
                "Period": 5400,
            }
        }

        config = DownsampleConfig(seed=42)
        result = downsample_by_regime(obs_df, sat_params, config)

        assert isinstance(result, pd.DataFrame)

    def test_downsample_empty_input(self):
        """Test with empty input."""
        from uct_benchmark.data.dataManipulation import downsample_by_regime

        obs_df = pd.DataFrame()
        sat_params = {}

        result = downsample_by_regime(obs_df, sat_params)
        assert result.empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
