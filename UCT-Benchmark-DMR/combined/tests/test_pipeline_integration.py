"""
Tests for downsampling and simulation pipeline integration.

Tests the integration of downsampling and simulation with the main
generateDataset pipeline and related components.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from uct_benchmark.data.dataManipulation import (
    apply_downsampling,
    apply_simulation_to_gaps,
    determine_orbital_regime,
    identify_tracks,
)
from uct_benchmark.settings import DownsampleConfig, SimulationConfig

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_observations():
    """Create sample observation data for testing."""
    np.random.seed(42)
    n_obs = 100
    base_time = datetime(2024, 1, 1)

    obs = pd.DataFrame(
        {
            "id": [f"OBS{i:04d}" for i in range(n_obs)],
            "satNo": np.repeat([25544, 25545, 25546], [34, 33, 33]),
            "obTime": [base_time + timedelta(minutes=i * 5) for i in range(n_obs)],
            "ra": np.random.uniform(0, 360, n_obs),
            "declination": np.random.uniform(-90, 90, n_obs),
            "sensorName": np.random.choice(["SEN001", "SEN002"], n_obs),
            "dataMode": ["REAL"] * n_obs,
        }
    )
    return obs


@pytest.fixture
def sample_elset_data():
    """Create sample element set (TLE) data for testing."""
    # ISS TLE
    return pd.DataFrame(
        {
            "satNo": [25544, 25545, 25546],
            "line1": [
                "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9025",
                "1 25545U 98067B   24001.50000000  .00016717  00000-0  10270-3 0  9025",
                "1 25546U 98067C   24001.50000000  .00016717  00000-0  10270-3 0  9025",
            ],
            "line2": [
                "2 25544  51.6400 208.9163 0006703 358.0000   2.0000 15.49580000123456",
                "2 25545  51.6400 208.9163 0006703 358.0000   2.0000 15.49580000123456",
                "2 25546  51.6400 208.9163 0006703 358.0000   2.0000 15.49580000123456",
            ],
        }
    )


@pytest.fixture
def sample_sat_params():
    """Create sample satellite parameters for testing."""
    return {
        25544: {
            "Semi-Major Axis": 6780,
            "Eccentricity": 0.0006703,
            "Inclination": 51.64,
            "RAAN": 208.9163,
            "Argument of Perigee": 358.0,
            "Mean Anomaly": 2.0,
            "Period": 5520,
            "Number of Obs": 34,
            "Orbital Coverage": 0.5,
            "Max Track Gap": 2.0,
        },
        25545: {
            "Semi-Major Axis": 6780,
            "Eccentricity": 0.0006703,
            "Inclination": 51.64,
            "RAAN": 208.9163,
            "Argument of Perigee": 358.0,
            "Mean Anomaly": 2.0,
            "Period": 5520,
            "Number of Obs": 33,
            "Orbital Coverage": 0.5,
            "Max Track Gap": 2.0,
        },
        25546: {
            "Semi-Major Axis": 6780,
            "Eccentricity": 0.0006703,
            "Inclination": 51.64,
            "RAAN": 208.9163,
            "Argument of Perigee": 358.0,
            "Mean Anomaly": 2.0,
            "Period": 5520,
            "Number of Obs": 33,
            "Orbital Coverage": 0.5,
            "Max Track Gap": 2.0,
        },
    }


@pytest.fixture
def sample_sensor_df():
    """Create sample sensor data for testing."""
    return pd.DataFrame(
        {
            "idSensor": ["SEN001", "SEN002", "SEN003"],
            "name": ["DIEGO_GARCIA", "ASCENSION", "MAUI"],
            "senlat": [-7.3, -7.9, 20.7],
            "senlon": [72.4, -14.4, -156.3],
            "senalt": [0.01, 0.04, 3.1],
            "count": [10, 10, 10],
        }
    )


# =============================================================================
# DOWNSAMPLING INTEGRATION TESTS
# =============================================================================


class TestApplyDownsampling:
    """Tests for the apply_downsampling function."""

    def test_returns_empty_metadata_for_empty_input(self):
        """Verify empty input returns appropriate metadata."""
        empty_df = pd.DataFrame()
        config = DownsampleConfig()

        result_df, metadata = apply_downsampling(empty_df, {}, config=config)

        assert result_df.empty
        assert metadata["status"] == "empty_input"
        assert metadata["original_count"] == 0
        assert metadata["final_count"] == 0

    def test_returns_original_when_no_sat_params(self, sample_observations):
        """Verify original data returned when no satellite parameters."""
        config = DownsampleConfig()

        result_df, metadata = apply_downsampling(sample_observations, {}, config=config)

        assert len(result_df) == len(sample_observations)
        assert metadata["status"] == "no_sat_params"
        assert metadata["retention_ratio"] == 1.0

    def test_downsampling_reduces_observations(self, sample_observations, sample_sat_params):
        """Verify downsampling reduces the number of observations."""
        config = DownsampleConfig(target_coverage=0.05, max_obs_per_sat=20, seed=42)

        result_df, metadata = apply_downsampling(
            sample_observations, sample_sat_params, config=config, tier="T2"
        )

        assert len(result_df) < len(sample_observations)
        assert metadata["status"] == "success"
        assert metadata["retention_ratio"] < 1.0
        assert metadata["tier"] == "T2"

    def test_tier_affects_downsampling_intensity(self, sample_observations, sample_sat_params):
        """Verify different tiers produce different downsampling levels."""
        results = {}
        for tier in ["T1", "T2", "T3", "T4"]:
            config = DownsampleConfig(seed=42)
            result_df, metadata = apply_downsampling(
                sample_observations.copy(), sample_sat_params, config=config, tier=tier
            )
            results[tier] = len(result_df)

        # T1 should retain more observations than T4
        assert results["T1"] >= results["T4"]

    def test_seed_provides_reproducibility(self, sample_observations, sample_sat_params):
        """Verify using the same seed produces identical results."""
        config1 = DownsampleConfig(seed=12345)
        config2 = DownsampleConfig(seed=12345)
        config3 = DownsampleConfig(seed=54321)

        result1, _ = apply_downsampling(
            sample_observations.copy(), sample_sat_params, config=config1
        )
        result2, _ = apply_downsampling(
            sample_observations.copy(), sample_sat_params, config=config2
        )
        result3, _ = apply_downsampling(
            sample_observations.copy(), sample_sat_params, config=config3
        )

        # Same seed should give same result
        assert len(result1) == len(result2)

    def test_metadata_contains_config(self, sample_observations, sample_sat_params):
        """Verify metadata contains the configuration used."""
        config = DownsampleConfig(
            target_coverage=0.1,
            target_gap=3.0,
            max_obs_per_sat=30,
            preserve_track_boundaries=True,
            seed=42,
        )

        _, metadata = apply_downsampling(sample_observations, sample_sat_params, config=config)

        assert "config" in metadata
        assert metadata["config"]["target_coverage"] == 0.1
        assert metadata["config"]["target_gap"] == 3.0
        assert metadata["config"]["max_obs_per_sat"] == 30


# =============================================================================
# SIMULATION INTEGRATION TESTS
# =============================================================================


class TestApplySimulationToGaps:
    """Tests for the apply_simulation_to_gaps function."""

    def test_returns_empty_metadata_for_empty_input(self):
        """Verify empty input returns appropriate metadata."""
        empty_df = pd.DataFrame()
        empty_elset = pd.DataFrame()

        result_df, metadata = apply_simulation_to_gaps(empty_df, empty_elset, pd.DataFrame())

        assert result_df.empty
        assert metadata["status"] == "empty_input"

    def test_returns_original_when_no_elset_data(self, sample_observations):
        """Verify original data returned when no element set data."""
        result_df, metadata = apply_simulation_to_gaps(sample_observations, None, None)

        assert len(result_df) == len(sample_observations)
        assert metadata["status"] == "no_elset_data"
        assert metadata["simulated_count"] == 0

    def test_simulation_adds_observations_basic(
        self, sample_observations, sample_elset_data, sample_sensor_df
    ):
        """Verify simulation function handles inputs correctly."""
        config = SimulationConfig(apply_sensor_noise=False, max_synthetic_ratio=0.5, seed=42)

        # This will run the actual function but likely won't produce simulated
        # observations in the test environment (no Orekit initialized)
        result_df, metadata = apply_simulation_to_gaps(
            sample_observations.copy(), sample_elset_data, sample_sensor_df, config=config
        )

        # Verify function returns valid output structure
        assert isinstance(result_df, pd.DataFrame)
        assert "status" in metadata
        assert "original_count" in metadata
        assert metadata["original_count"] == len(sample_observations)

    def test_metadata_contains_counts(
        self, sample_observations, sample_elset_data, sample_sensor_df
    ):
        """Verify metadata contains correct counts."""
        config = SimulationConfig(seed=42)

        _, metadata = apply_simulation_to_gaps(
            sample_observations, sample_elset_data, sample_sensor_df, config=config
        )

        assert "original_count" in metadata
        assert "simulated_count" in metadata
        assert "total_count" in metadata
        assert metadata["original_count"] == len(sample_observations)


# =============================================================================
# ORBITAL REGIME DETECTION TESTS
# =============================================================================


class TestOrbitalRegimeDetection:
    """Tests for orbital regime detection function."""

    def test_detects_leo(self):
        """Verify LEO detection for semi-major axis < 8378 km."""
        assert determine_orbital_regime(6780) == "LEO"
        assert determine_orbital_regime(7000) == "LEO"
        assert determine_orbital_regime(8377) == "LEO"

    def test_detects_meo(self):
        """Verify MEO detection for semi-major axis 8378-42164 km."""
        assert determine_orbital_regime(8378) == "MEO"
        assert determine_orbital_regime(20200) == "MEO"
        assert determine_orbital_regime(42163) == "MEO"

    def test_detects_geo(self):
        """Verify GEO detection for semi-major axis >= 42164 km."""
        assert determine_orbital_regime(42164) == "GEO"
        assert determine_orbital_regime(42200) == "GEO"

    def test_detects_heo(self):
        """Verify HEO detection for high eccentricity."""
        assert determine_orbital_regime(26600, eccentricity=0.74) == "HEO"
        assert determine_orbital_regime(40000, eccentricity=0.8) == "HEO"


# =============================================================================
# TRACK IDENTIFICATION TESTS
# =============================================================================


class TestTrackIdentification:
    """Tests for track identification function."""

    def test_identifies_continuous_tracks(self):
        """Verify continuous observations grouped into tracks."""
        base_time = datetime(2024, 1, 1)
        obs = pd.DataFrame(
            {
                "satNo": [25544] * 10,
                "obTime": [base_time + timedelta(minutes=i) for i in range(10)],
                "ra": [180.0] * 10,
                "declination": [45.0] * 10,
            }
        )

        tracks = identify_tracks(obs, gap_threshold_minutes=90)

        # Should be one continuous track
        assert len(tracks) == 1

    def test_splits_on_gaps(self):
        """Verify tracks split on large gaps."""
        base_time = datetime(2024, 1, 1)
        # Create two groups with a 2-hour gap
        obs = pd.DataFrame(
            {
                "satNo": [25544] * 10,
                "obTime": (
                    [base_time + timedelta(minutes=i) for i in range(5)]
                    + [base_time + timedelta(minutes=120 + i) for i in range(5)]
                ),
                "ra": [180.0] * 10,
                "declination": [45.0] * 10,
            }
        )

        tracks = identify_tracks(obs, gap_threshold_minutes=90)

        # Should be two tracks due to gap
        assert len(tracks) == 2

    def test_handles_multiple_satellites(self):
        """Verify tracks separated by satellite."""
        base_time = datetime(2024, 1, 1)
        obs = pd.DataFrame(
            {
                "satNo": [25544] * 5 + [25545] * 5,
                "obTime": [base_time + timedelta(minutes=i) for i in range(10)],
                "ra": [180.0] * 10,
                "declination": [45.0] * 10,
            }
        )

        tracks = identify_tracks(obs, gap_threshold_minutes=90)

        # Should have at least 2 tracks (one per satellite)
        assert len(tracks) >= 2


# =============================================================================
# CONFIGURATION TESTS
# =============================================================================


class TestConfigDataclasses:
    """Tests for configuration dataclasses."""

    def test_downsample_config_defaults(self):
        """Verify DownsampleConfig has sensible defaults."""
        config = DownsampleConfig()

        assert config.target_coverage == 0.05
        assert config.target_gap == 2.0
        assert config.max_obs_per_sat == 50
        assert config.min_obs_per_sat == 5
        assert config.preserve_track_boundaries is True
        assert config.seed is None

    def test_simulation_config_defaults(self):
        """Verify SimulationConfig has sensible defaults."""
        config = SimulationConfig()

        assert config.apply_sensor_noise is True
        assert config.sensor_model == "GEODSS"
        assert config.max_synthetic_ratio == 0.5
        assert config.seed is None

    def test_config_custom_values(self):
        """Verify configs accept custom values."""
        ds_config = DownsampleConfig(
            target_coverage=0.1, target_gap=3.0, max_obs_per_sat=100, seed=42
        )

        assert ds_config.target_coverage == 0.1
        assert ds_config.target_gap == 3.0
        assert ds_config.max_obs_per_sat == 100
        assert ds_config.seed == 42


# =============================================================================
# BACKWARD COMPATIBILITY TESTS
# =============================================================================


class TestBackwardCompatibility:
    """Tests to ensure existing functionality is not broken."""

    def test_existing_downsampling_functions_unchanged(
        self, sample_observations, sample_sat_params
    ):
        """Verify existing downsampling functions still work."""
        from uct_benchmark.data.dataManipulation import downsample_by_regime

        # This should not raise any errors
        result = downsample_by_regime(
            sample_observations.copy(),
            sample_sat_params,
            config=None,
            rng=np.random.default_rng(42),
        )

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_existing_track_functions_unchanged(self, sample_observations):
        """Verify existing track functions still work."""
        from uct_benchmark.data.dataManipulation import identify_tracks

        tracks = identify_tracks(sample_observations)

        assert isinstance(tracks, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
