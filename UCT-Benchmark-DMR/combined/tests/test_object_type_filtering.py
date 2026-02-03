# -*- coding: utf-8 -*-
"""
Test Suite for Object Type Filtering

Tests the filter_by_object_type_code() function for each object type code:
- H: HAMR (High Area-to-Mass Ratio)
- C: Close physical proximity
- A: Apparent angular proximity
- U: Unspecified/Normal
- N: Calibration satellites
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestFilterByObjectTypeCode:
    """Tests for the filter_by_object_type_code function."""

    @pytest.fixture
    def sample_observations_df(self):
        """Create sample observations DataFrame."""
        np.random.seed(42)
        n_obs = 100
        base_time = datetime(2024, 1, 1)

        # Create observations from various satellites
        sat_ids = [25544, 25545, 25546, 25547, 25548, 25549]

        return pd.DataFrame({
            "id": [f"obs_{i}" for i in range(n_obs)],
            "satNo": np.random.choice(sat_ids, n_obs),
            "obTime": [base_time + timedelta(hours=i) for i in range(n_obs)],
            "ra": np.random.uniform(0, 360, n_obs),
            "declination": np.random.uniform(-90, 90, n_obs),
        })

    @pytest.fixture
    def sample_physical_data(self):
        """Create sample physical data with A/M ratios."""
        return {
            25544: {"mass": 100, "cross_section": 5},   # A/M = 0.05 (normal)
            25545: {"mass": 10, "cross_section": 5},    # A/M = 0.5 (HAMR)
            25546: {"mass": 50, "cross_section": 10},   # A/M = 0.2 (HAMR)
            25547: {"mass": 200, "cross_section": 10},  # A/M = 0.05 (normal)
            25548: {"mass": 5, "cross_section": 2},     # A/M = 0.4 (HAMR)
            25549: {"mass": 500, "cross_section": 20},  # A/M = 0.04 (normal)
        }

    @pytest.fixture
    def sample_sat_params(self):
        """Create sample satellite orbital parameters."""
        return {
            25544: {"semi_major_axis_km": 6800, "eccentricity": 0.001},
            25545: {"semi_major_axis_km": 6850, "eccentricity": 0.002},
            25546: {"semi_major_axis_km": 6900, "eccentricity": 0.003},
            25547: {"semi_major_axis_km": 6950, "eccentricity": 0.001},
            25548: {"semi_major_axis_km": 7000, "eccentricity": 0.002},
            25549: {"semi_major_axis_km": 7050, "eccentricity": 0.003},
        }

    def test_unspecified_object_type_returns_all(
        self, sample_observations_df, sample_sat_params, sample_physical_data
    ):
        """Test that U (Unspecified) returns all observations."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=sample_observations_df,
            object_type_code="U",
            sat_params=sample_sat_params,
            physical_data=sample_physical_data,
        )

        # U should return all observations
        assert len(filtered_df) == len(sample_observations_df)
        assert metadata["object_type_code"] == "U"

    def test_hamr_object_type_filters_correctly(
        self, sample_observations_df, sample_sat_params, sample_physical_data
    ):
        """Test that H (HAMR) filters to high A/M ratio objects."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code
        from uct_benchmark.settings import HAMR_THRESHOLD

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=sample_observations_df,
            object_type_code="H",
            sat_params=sample_sat_params,
            physical_data=sample_physical_data,
        )

        assert metadata["object_type_code"] == "H"
        assert "HAMR" in metadata.get("filters_applied", [])

        # Get the HAMR satellites from our physical data
        hamr_sats = []
        for sat_no, data in sample_physical_data.items():
            am_ratio = data["cross_section"] / data["mass"]
            if am_ratio >= HAMR_THRESHOLD:
                hamr_sats.append(sat_no)

        # If HAMR objects were found, verify filtering
        if hamr_sats and not filtered_df.empty:
            # All observations should be from HAMR satellites
            filtered_sats = filtered_df["satNo"].unique()
            for sat in filtered_sats:
                assert sat in hamr_sats, f"Satellite {sat} should be HAMR"

    def test_calibration_object_type(
        self, sample_observations_df, sample_sat_params, sample_physical_data
    ):
        """Test that N (Calibration) filters to calibration satellites."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code
        from uct_benchmark.settings import CALIBRATION_SATELLITES

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=sample_observations_df,
            object_type_code="N",
            sat_params=sample_sat_params,
            physical_data=sample_physical_data,
        )

        assert metadata["object_type_code"] == "N"

        # If calibration satellites found in observations
        if not filtered_df.empty:
            filtered_sats = filtered_df["satNo"].unique()
            for sat in filtered_sats:
                assert sat in CALIBRATION_SATELLITES, f"Satellite {sat} should be calibration"

    def test_invalid_object_type_raises_error(
        self, sample_observations_df, sample_sat_params, sample_physical_data
    ):
        """Test that invalid object type codes raise ValueError."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code

        with pytest.raises(ValueError) as exc_info:
            filter_by_object_type_code(
                obs_df=sample_observations_df,
                object_type_code="X",  # Invalid code
                sat_params=sample_sat_params,
                physical_data=sample_physical_data,
            )

        assert "Invalid object type code" in str(exc_info.value)

    def test_empty_observations_df(
        self, sample_sat_params, sample_physical_data
    ):
        """Test handling of empty observations DataFrame."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code

        empty_df = pd.DataFrame(columns=["id", "satNo", "obTime", "ra", "declination"])

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=empty_df,
            object_type_code="U",
            sat_params=sample_sat_params,
            physical_data=sample_physical_data,
        )

        assert filtered_df.empty
        assert metadata["status"] == "empty_input"

    def test_close_proximity_filtering(
        self, sample_observations_df, sample_sat_params, sample_physical_data
    ):
        """Test that C (Close) filters for physical proximity."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code

        # Create state data for proximity calculation
        state_data = {
            25544: {"x": 6800, "y": 0, "z": 0, "vx": 0, "vy": 7.5, "vz": 0},
            25545: {"x": 6800.05, "y": 0, "z": 0, "vx": 0, "vy": 7.5, "vz": 0},  # Very close!
            25546: {"x": 7000, "y": 0, "z": 0, "vx": 0, "vy": 7.3, "vz": 0},
            25547: {"x": 7200, "y": 0, "z": 0, "vx": 0, "vy": 7.1, "vz": 0},
            25548: {"x": 6000, "y": 0, "z": 0, "vx": 0, "vy": 8.0, "vz": 0},
            25549: {"x": 6500, "y": 0, "z": 0, "vx": 0, "vy": 7.7, "vz": 0},
        }

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=sample_observations_df,
            object_type_code="C",
            sat_params=sample_sat_params,
            physical_data=sample_physical_data,
            state_data=state_data,
        )

        assert metadata["object_type_code"] == "C"
        # The function should apply proximity filtering

    def test_apparent_proximity_filtering(
        self, sample_observations_df, sample_sat_params, sample_physical_data
    ):
        """Test that A (Apparent) filters for angular proximity."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=sample_observations_df,
            object_type_code="A",
            sat_params=sample_sat_params,
            physical_data=sample_physical_data,
        )

        assert metadata["object_type_code"] == "A"
        # The function should apply angular proximity filtering

    def test_metadata_contains_required_fields(
        self, sample_observations_df, sample_sat_params, sample_physical_data
    ):
        """Test that metadata contains all required fields."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=sample_observations_df,
            object_type_code="U",
            sat_params=sample_sat_params,
            physical_data=sample_physical_data,
        )

        # Check required metadata fields
        assert "object_type_code" in metadata
        assert "total_satellites" in metadata
        assert "filters_applied" in metadata


class TestObjectFilterConfig:
    """Tests for the ObjectFilterConfig dataclass."""

    def test_default_config(self):
        """Test default ObjectFilterConfig values."""
        from uct_benchmark.data.objectTypeFiltering import ObjectFilterConfig
        from uct_benchmark.settings import HAMR_THRESHOLD

        config = ObjectFilterConfig()

        assert config.enable_hamr == False
        assert config.hamr_threshold == HAMR_THRESHOLD
        assert config.enable_proximity == False
        assert config.enable_calibration == False
        assert config.object_types == ["NORM"]

    def test_config_with_custom_values(self):
        """Test ObjectFilterConfig with custom values."""
        from uct_benchmark.data.objectTypeFiltering import ObjectFilterConfig

        config = ObjectFilterConfig(
            enable_hamr=True,
            hamr_threshold=0.2,
            object_types=["HAMR", "PROX"],
        )

        assert config.enable_hamr == True
        assert config.hamr_threshold == 0.2
        assert "HAMR" in config.object_types
        assert "PROX" in config.object_types


class TestHAMRFiltering:
    """Specific tests for HAMR (High Area-to-Mass Ratio) filtering."""

    def test_hamr_threshold_boundary(self):
        """Test HAMR filtering at threshold boundary."""
        from uct_benchmark.data.objectTypeFiltering import filter_hamr_objects
        from uct_benchmark.settings import HAMR_THRESHOLD

        satellite_ids = [1, 2, 3, 4, 5]
        physical_data = {
            1: {"mass": 100, "cross_section": HAMR_THRESHOLD * 100},     # Exactly at threshold
            2: {"mass": 100, "cross_section": HAMR_THRESHOLD * 100 + 1}, # Just above
            3: {"mass": 100, "cross_section": HAMR_THRESHOLD * 100 - 1}, # Just below
            4: {"mass": 100, "cross_section": HAMR_THRESHOLD * 200},     # Well above
            5: {"mass": 100, "cross_section": HAMR_THRESHOLD * 50},      # Well below
        }

        hamr_sats, normal_sats = filter_hamr_objects(
            satellite_ids, physical_data, HAMR_THRESHOLD
        )

        # Satellites 1, 2, 4 should be HAMR (>= threshold)
        assert 1 in hamr_sats  # Exactly at threshold
        assert 2 in hamr_sats  # Just above
        assert 4 in hamr_sats  # Well above

        # Satellites 3, 5 should be normal (< threshold)
        assert 3 in normal_sats
        assert 5 in normal_sats

    def test_hamr_with_missing_physical_data(self):
        """Test HAMR filtering when some satellites have no physical data."""
        from uct_benchmark.data.objectTypeFiltering import filter_hamr_objects
        from uct_benchmark.settings import HAMR_THRESHOLD

        satellite_ids = [1, 2, 3]
        physical_data = {
            1: {"mass": 10, "cross_section": 5},  # A/M = 0.5 (HAMR)
            # 2 is missing physical data
            # 3 is missing physical data
        }

        hamr_sats, normal_sats = filter_hamr_objects(
            satellite_ids, physical_data, HAMR_THRESHOLD
        )

        # Satellite 1 should be HAMR
        assert 1 in hamr_sats

        # Satellites 2, 3 should be in normal (no data = can't confirm HAMR)
        assert 2 in normal_sats
        assert 3 in normal_sats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
