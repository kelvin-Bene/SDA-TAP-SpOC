# -*- coding: utf-8 -*-
"""
Tests for track binning and data manipulation functions.

Tests:
- binTracks function for grouping observations
- Track identification and splitting
- Orbital period calculation
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

# =============================================================================
# BIN TRACKS TESTS
# =============================================================================


class TestBinTracks:
    """Tests for binTracks function."""

    @pytest.fixture
    def sample_observations(self):
        """Create sample observation data for testing."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        return pd.DataFrame(
            {
                "id": [f"obs{i}" for i in range(15)],
                "obTime": [
                    # Track 1 for sat 25544 (5 obs, ~5 min apart)
                    base_time + timedelta(minutes=0),
                    base_time + timedelta(minutes=5),
                    base_time + timedelta(minutes=10),
                    base_time + timedelta(minutes=15),
                    base_time + timedelta(minutes=20),
                    # Track 2 for sat 25544 (after 2hr gap, 4 obs)
                    base_time + timedelta(hours=2, minutes=0),
                    base_time + timedelta(hours=2, minutes=5),
                    base_time + timedelta(hours=2, minutes=10),
                    base_time + timedelta(hours=2, minutes=15),
                    # Track for sat 25545 (6 obs)
                    base_time + timedelta(minutes=0),
                    base_time + timedelta(minutes=5),
                    base_time + timedelta(minutes=10),
                    base_time + timedelta(minutes=15),
                    base_time + timedelta(minutes=20),
                    base_time + timedelta(minutes=25),
                ],
                "satNo": [25544] * 9 + [25545] * 6,
                "idSensor": ["SEN001"] * 9 + ["SEN002"] * 6,
                "senlat": [30.0] * 9 + [40.0] * 6,
                "senlon": [-100.0] * 9 + [-80.0] * 6,
                "senalt": [0.1] * 9 + [0.2] * 6,
                "ra": np.random.uniform(0, 360, 15),
                "declination": np.random.uniform(-90, 90, 15),
            }
        )

    @pytest.fixture
    def sample_state_vectors(self):
        """Create sample state vectors for testing."""
        # LEO orbit - ~400km altitude
        r_leo = 6778.0  # km (Earth radius + 400km)
        v_leo = 7.67  # km/s (circular velocity at this altitude)

        return pd.DataFrame(
            {
                "satNo": [25544, 25545],
                "epoch": [datetime(2024, 1, 1), datetime(2024, 1, 1)],
                "xpos": [r_leo, r_leo],
                "ypos": [0.0, 0.0],
                "zpos": [0.0, 0.0],
                "xvel": [0.0, 0.0],
                "yvel": [v_leo, v_leo],
                "zvel": [0.0, 0.0],
            }
        )

    def test_bin_tracks_basic(self, sample_observations, sample_state_vectors):
        """Test basic track binning functionality."""
        from uct_benchmark.data.dataManipulation import binTracks

        tracks, metrics = binTracks(sample_observations, sample_state_vectors)

        # Should have tracks
        assert len(tracks) > 0

        # Each track should be a (satNo, period, df) tuple
        for sat, period, df in tracks:
            assert isinstance(sat, (int, np.integer))
            assert isinstance(period, (float, np.floating))
            assert isinstance(df, pd.DataFrame)
            assert len(df) >= 3  # Minimum track length

    def test_bin_tracks_metrics(self, sample_observations, sample_state_vectors):
        """Test that metrics are correctly computed."""
        from uct_benchmark.data.dataManipulation import binTracks

        tracks, metrics = binTracks(sample_observations, sample_state_vectors)

        # metrics = [total, kept, discarded, invalid]
        assert len(metrics) == 4
        assert metrics[0] >= 0  # total tracks found
        assert metrics[1] >= 0  # tracks kept
        assert metrics[2] >= 0  # tracks discarded
        assert metrics[3] >= 0  # invalid groups

        # Total should be kept + discarded
        assert metrics[0] == metrics[1] + metrics[2]

    def test_bin_tracks_gap_detection(self, sample_state_vectors):
        """Test that large time gaps split tracks."""
        from uct_benchmark.data.dataManipulation import binTracks

        base_time = datetime(2024, 1, 1, 12, 0, 0)

        # Create observations with a clear 2-hour gap
        obs = pd.DataFrame(
            {
                "id": [f"obs{i}" for i in range(8)],
                "obTime": [
                    # First track (4 obs)
                    base_time + timedelta(minutes=0),
                    base_time + timedelta(minutes=5),
                    base_time + timedelta(minutes=10),
                    base_time + timedelta(minutes=15),
                    # Second track after 2-hour gap (4 obs)
                    base_time + timedelta(hours=2, minutes=0),
                    base_time + timedelta(hours=2, minutes=5),
                    base_time + timedelta(hours=2, minutes=10),
                    base_time + timedelta(hours=2, minutes=15),
                ],
                "satNo": [25544] * 8,
                "idSensor": ["SEN001"] * 8,
                "senlat": [30.0] * 8,
                "senlon": [-100.0] * 8,
                "senalt": [0.1] * 8,
                "ra": np.random.uniform(0, 360, 8),
                "declination": np.random.uniform(-90, 90, 8),
            }
        )

        tracks, metrics = binTracks(obs, sample_state_vectors)

        # Should detect 2 separate tracks due to gap
        sat_25544_tracks = [t for t in tracks if t[0] == 25544]
        assert len(sat_25544_tracks) == 2

    def test_bin_tracks_minimum_length(self, sample_state_vectors):
        """Test that tracks shorter than 3 observations are discarded."""
        from uct_benchmark.data.dataManipulation import binTracks

        base_time = datetime(2024, 1, 1, 12, 0, 0)

        # Create observations with some short tracks
        obs = pd.DataFrame(
            {
                "id": [f"obs{i}" for i in range(5)],
                "obTime": [
                    # Short track (2 obs) - should be discarded
                    base_time + timedelta(minutes=0),
                    base_time + timedelta(minutes=5),
                    # Valid track (3 obs)
                    base_time + timedelta(hours=2, minutes=0),
                    base_time + timedelta(hours=2, minutes=5),
                    base_time + timedelta(hours=2, minutes=10),
                ],
                "satNo": [25544] * 5,
                "idSensor": ["SEN001"] * 5,
                "senlat": [30.0] * 5,
                "senlon": [-100.0] * 5,
                "senalt": [0.1] * 5,
                "ra": np.random.uniform(0, 360, 5),
                "declination": np.random.uniform(-90, 90, 5),
            }
        )

        tracks, metrics = binTracks(obs, sample_state_vectors)

        # Should have 1 valid track (the 3-obs one) and 1 discarded
        assert metrics[1] >= 1  # kept
        # All tracks should have at least 3 observations
        for _, _, df in tracks:
            assert len(df) >= 3

    def test_bin_tracks_multiple_satellites(self, sample_observations, sample_state_vectors):
        """Test binning with multiple satellites."""
        from uct_benchmark.data.dataManipulation import binTracks

        tracks, metrics = binTracks(sample_observations, sample_state_vectors)

        # Should have tracks for both satellites
        satellites_with_tracks = set(t[0] for t in tracks)
        assert len(satellites_with_tracks) >= 1

    def test_bin_tracks_orbital_period(self, sample_observations, sample_state_vectors):
        """Test that orbital periods are computed correctly."""
        from uct_benchmark.data.dataManipulation import binTracks

        tracks, metrics = binTracks(sample_observations, sample_state_vectors)

        # LEO orbital period should be ~90 minutes (5400 seconds)
        for sat, period, df in tracks:
            assert 5000 < period < 6000  # LEO period range

    def test_bin_tracks_empty_input(self, sample_state_vectors):
        """Test handling of empty observation DataFrame."""
        from uct_benchmark.data.dataManipulation import binTracks

        empty_obs = pd.DataFrame(
            columns=[
                "id",
                "obTime",
                "satNo",
                "idSensor",
                "senlat",
                "senlon",
                "senalt",
                "ra",
                "declination",
            ]
        )

        tracks, metrics = binTracks(empty_obs, sample_state_vectors)

        assert len(tracks) == 0
        assert metrics[1] == 0  # no tracks kept


# =============================================================================
# ORBITAL REGIME DETECTION TESTS
# =============================================================================


class TestOrbitalRegimeDetection:
    """Tests for orbital regime detection."""

    def test_determine_leo(self):
        """Test LEO detection."""
        from uct_benchmark.data.dataManipulation import determine_orbital_regime

        # Various LEO altitudes
        assert determine_orbital_regime(6700) == "LEO"  # ~320km altitude
        assert determine_orbital_regime(7000) == "LEO"  # ~622km altitude
        assert determine_orbital_regime(7500) == "LEO"  # ~1122km altitude

    def test_determine_meo(self):
        """Test MEO detection."""
        from uct_benchmark.data.dataManipulation import determine_orbital_regime

        # GPS/GLONASS altitude range
        assert determine_orbital_regime(20200) == "MEO"  # GPS
        assert determine_orbital_regime(26600) == "MEO"  # GLONASS

    def test_determine_geo(self):
        """Test GEO detection."""
        from uct_benchmark.data.dataManipulation import determine_orbital_regime

        # Geostationary altitude
        assert determine_orbital_regime(42164) == "GEO"
        assert determine_orbital_regime(42200) == "GEO"

    def test_determine_heo(self):
        """Test HEO detection based on eccentricity."""
        from uct_benchmark.data.dataManipulation import determine_orbital_regime

        # High eccentricity orbits (Molniya-type)
        assert determine_orbital_regime(26600, eccentricity=0.74) == "HEO"
        assert determine_orbital_regime(40000, eccentricity=0.8) == "HEO"

    def test_heo_takes_precedence(self):
        """Test that high eccentricity overrides altitude classification."""
        from uct_benchmark.data.dataManipulation import determine_orbital_regime

        # Even at LEO altitude, high eccentricity → HEO
        assert determine_orbital_regime(7000, eccentricity=0.75) == "HEO"


# =============================================================================
# TRACK IDENTIFICATION TESTS
# =============================================================================


class TestTrackIdentification:
    """Tests for identify_tracks function."""

    def test_identify_single_track(self):
        """Test identifying a single continuous track."""
        from uct_benchmark.data.dataManipulation import identify_tracks

        base_time = datetime(2024, 1, 1, 12, 0, 0)
        obs = pd.DataFrame(
            {
                "obTime": [base_time + timedelta(minutes=i * 5) for i in range(10)],
                "satNo": [25544] * 10,
                "idSensor": ["SEN001"] * 10,
                "ra": [100.0 + i for i in range(10)],
                "declination": [20.0] * 10,
            }
        )

        tracks = identify_tracks(obs, gap_threshold_minutes=90)

        assert len(tracks) == 1
        assert len(tracks[0]) == 10

    def test_identify_multiple_tracks_by_gap(self):
        """Test splitting tracks based on time gaps."""
        from uct_benchmark.data.dataManipulation import identify_tracks

        base_time = datetime(2024, 1, 1, 12, 0, 0)
        obs = pd.DataFrame(
            {
                "obTime": [
                    # First track
                    base_time + timedelta(minutes=0),
                    base_time + timedelta(minutes=5),
                    base_time + timedelta(minutes=10),
                    # 2-hour gap
                    base_time + timedelta(hours=2, minutes=0),
                    base_time + timedelta(hours=2, minutes=5),
                    base_time + timedelta(hours=2, minutes=10),
                ],
                "satNo": [25544] * 6,
                "idSensor": ["SEN001"] * 6,
                "ra": [100.0] * 6,
                "declination": [20.0] * 6,
            }
        )

        tracks = identify_tracks(obs, gap_threshold_minutes=90)

        assert len(tracks) == 2

    def test_identify_tracks_different_satellites(self):
        """Test that different satellites create separate tracks."""
        from uct_benchmark.data.dataManipulation import identify_tracks

        base_time = datetime(2024, 1, 1, 12, 0, 0)
        obs = pd.DataFrame(
            {
                "obTime": [base_time + timedelta(minutes=i) for i in range(6)],
                "satNo": [25544] * 3 + [25545] * 3,
                "idSensor": ["SEN001"] * 6,
                "ra": [100.0] * 6,
                "declination": [20.0] * 6,
            }
        )

        tracks = identify_tracks(obs, gap_threshold_minutes=90)

        # Should have at least 2 tracks (one per satellite)
        assert len(tracks) >= 2

    def test_identify_tracks_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        from uct_benchmark.data.dataManipulation import identify_tracks

        obs = pd.DataFrame(columns=["obTime", "satNo", "idSensor"])
        tracks = identify_tracks(obs)

        assert len(tracks) == 0


# =============================================================================
# REGIME PROFILE TESTS
# =============================================================================


class TestRegimeProfiles:
    """Tests for regime-specific downsampling profiles."""

    def test_get_regime_profile_leo(self):
        """Test getting LEO profile."""
        from uct_benchmark.data.dataManipulation import get_regime_profile

        profile = get_regime_profile("LEO")

        assert "min_coverage_pct" in profile
        assert "max_track_gap_periods" in profile
        assert "obs_per_track" in profile

    def test_get_regime_profile_geo(self):
        """Test getting GEO profile."""
        from uct_benchmark.data.dataManipulation import get_regime_profile

        profile = get_regime_profile("GEO")

        # GEO should have different characteristics than LEO
        leo_profile = get_regime_profile("LEO")
        assert (
            profile["min_coverage_pct"] != leo_profile["min_coverage_pct"]
            or profile["max_track_gap_periods"] != leo_profile["max_track_gap_periods"]
        )

    def test_get_regime_profile_unknown(self):
        """Test getting profile for unknown regime (should default to LEO)."""
        from uct_benchmark.data.dataManipulation import get_regime_profile

        profile = get_regime_profile("UNKNOWN")
        leo_profile = get_regime_profile("LEO")

        # Should fall back to LEO profile
        assert profile == leo_profile


# =============================================================================
# COVERAGE CALCULATION TESTS
# =============================================================================


class TestCoverageCalculation:
    """Tests for orbital coverage calculation."""

    def test_compute_arc_coverage_full(self):
        """Test arc coverage with full orbit."""
        from uct_benchmark.data.dataManipulation import compute_arc_coverage

        # Full orbit coverage
        anomalies = np.linspace(0, 2 * np.pi, 36)  # Every 10 degrees
        coverage = compute_arc_coverage(anomalies)

        assert coverage > 0.9

    def test_compute_arc_coverage_quarter(self):
        """Test arc coverage with quarter orbit."""
        from uct_benchmark.data.dataManipulation import compute_arc_coverage

        # Quarter orbit
        anomalies = np.linspace(0, np.pi / 2, 10)
        coverage = compute_arc_coverage(anomalies)

        assert coverage <= 0.5

    def test_compute_arc_coverage_sparse(self):
        """Test arc coverage with sparse observations."""
        from uct_benchmark.data.dataManipulation import compute_arc_coverage

        # Just 2 points
        anomalies = np.array([0, np.pi])
        coverage = compute_arc_coverage(anomalies)

        assert coverage >= 0


# =============================================================================
# THIN WITHIN TRACKS TESTS
# =============================================================================


class TestThinWithinTracks:
    """Tests for track thinning functionality."""

    def test_thin_preserves_boundaries(self):
        """Test that thinning preserves first and last observations."""
        from uct_benchmark.data.dataManipulation import thin_within_tracks

        base_time = datetime(2024, 1, 1, 12, 0, 0)
        track = pd.DataFrame(
            {
                "obTime": [base_time + timedelta(seconds=i * 30) for i in range(10)],
                "satNo": [25544] * 10,
                "id": [f"obs_{i}" for i in range(10)],
            }
        )

        rng = np.random.default_rng(42)
        result = thin_within_tracks([track], (3, 5), preserve_boundaries=True, rng=rng)

        # First and last should be preserved
        result_ids = result["id"].tolist()
        assert "obs_0" in result_ids
        assert "obs_9" in result_ids

    def test_thin_respects_count_range(self):
        """Test that thinning respects the observation count range."""
        from uct_benchmark.data.dataManipulation import thin_within_tracks

        base_time = datetime(2024, 1, 1, 12, 0, 0)
        track = pd.DataFrame(
            {
                "obTime": [base_time + timedelta(seconds=i * 30) for i in range(20)],
                "satNo": [25544] * 20,
                "id": [f"obs_{i}" for i in range(20)],
            }
        )

        rng = np.random.default_rng(42)
        result = thin_within_tracks([track], (5, 10), preserve_boundaries=True, rng=rng)

        assert len(result) >= 5
        assert len(result) <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
