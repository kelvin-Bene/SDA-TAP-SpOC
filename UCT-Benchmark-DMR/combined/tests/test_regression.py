# -*- coding: utf-8 -*-
"""
Regression Tests for UCT Benchmark

This module ensures that recent changes do not break existing functionality.
These tests verify backward compatibility and that existing APIs continue
to work as expected.

Author: UCT Benchmark Team
Date: 2026
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json


# =============================================================================
# BACKWARD COMPATIBILITY TESTS
# =============================================================================


class TestBackwardCompatibility:
    """Test that existing functionality still works after changes."""

    def test_legacy_dataset_code_still_parses(self):
        """Verify existing legacy code parsing still works."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        # Test codes that were working before
        test_codes = [
            "U50LEONEOPSSSS07",
            "H50MEONEOPSSSS03",
            "C10GEOBURASSNS14",
        ]

        for code in test_codes:
            parsed = LegacyDatasetCode.from_code(code)
            assert parsed is not None
            # Should roundtrip correctly
            assert parsed.to_code() == code

    def test_window_criteria_still_works(self):
        """Verify WindowCriteria creation still works."""
        from uct_benchmark.data.windowSelection import WindowCriteria

        # Test existing WindowCriteria functionality
        criteria = WindowCriteria(
            fit_span_days=7,
            min_objects=10,
            regimes=["LEO"],
        )

        assert criteria.fit_span_days == 7
        assert criteria.min_objects == 10
        assert criteria.regimes == ["LEO"]

    def test_existing_tier_values_unchanged(self):
        """Verify existing tier values remain unchanged."""
        from uct_benchmark.data.windowSelection import WindowTier

        # Existing tiers should still have same values
        assert WindowTier.TIER_1.value == 1
        assert WindowTier.TIER_2.value == 2
        assert WindowTier.TIER_3.value == 3
        assert WindowTier.TIER_4.value == 4
        # New tier 5 should exist
        assert WindowTier.TIER_5.value == 5

    def test_settings_constants_unchanged(self):
        """Verify important settings constants haven't changed."""
        from uct_benchmark.settings import (
            HAMR_THRESHOLD,
            NON_REF_OBS_PER_SATELLITE,
            semiMajorAxis_LEO,
            semiMajorAxis_GEO,
        )

        # These values should remain consistent
        assert HAMR_THRESHOLD == 1.0  # Per Lewis's doc: A/M > 1 m^2/kg
        assert NON_REF_OBS_PER_SATELLITE == 2
        assert semiMajorAxis_LEO == 8378
        assert semiMajorAxis_GEO == 42164

    def test_quality_ranges_unchanged(self):
        """Verify quality range definitions unchanged."""
        from uct_benchmark.settings import QUALITY_RANGES

        # A/S/N ranges should be consistent
        assert QUALITY_RANGES["A"]["min_pct"] == 0.90
        assert QUALITY_RANGES["S"]["min_pct"] == 0.40
        assert QUALITY_RANGES["S"]["max_pct"] == 0.60
        assert QUALITY_RANGES["N"]["max_pct"] == 0.10


# =============================================================================
# GENERATE DATASET SIGNATURE TESTS
# =============================================================================


class TestGenerateDatasetSignature:
    """Test generateDataset function maintains expected signature."""

    def test_existing_parameters_still_work(self):
        """Verify all existing parameters are still present."""
        from uct_benchmark.api.apiIntegration import generateDataset
        import inspect

        sig = inspect.signature(generateDataset)
        params = sig.parameters

        # Existing required/common parameters
        expected_params = [
            "UDL_token",
            "ESA_token",
            "satIDs",
            "timeframe",
            "timeunit",
            "dt",
            "max_datapoints",
            "end_time",
            "use_database",
            "db_path",
            "dataset_name",
            "downsample_config",
            "simulation_config",
            "tier",
            "dataset_id",
            "progress_callback",
            "search_strategy",
            "window_size_minutes",
            "regime",
            "include_non_ref_obs",
            "non_ref_ratio",
            "object_type_code",
            "event_code",
            "use_window_selection",
            "window_criteria",
        ]

        for param in expected_params:
            assert param in params, f"Missing parameter: {param}"

    def test_new_parameters_have_defaults(self):
        """Verify new parameters have sensible defaults."""
        from uct_benchmark.api.apiIntegration import generateDataset
        import inspect

        sig = inspect.signature(generateDataset)
        params = sig.parameters

        # New parameters should have defaults for backward compatibility
        new_params = {
            "target_percentage": "UN",
            "output_tracktle": False,
        }

        for param, expected_default in new_params.items():
            assert param in params, f"Missing new parameter: {param}"
            assert params[param].default == expected_default, \
                f"Wrong default for {param}: {params[param].default} != {expected_default}"

    def test_use_window_selection_now_defaults_true(self):
        """Verify use_window_selection now defaults to True."""
        from uct_benchmark.api.apiIntegration import generateDataset
        import inspect

        sig = inspect.signature(generateDataset)
        params = sig.parameters

        # This changed from False to True
        assert params["use_window_selection"].default == True


# =============================================================================
# API MODEL BACKWARD COMPATIBILITY TESTS
# =============================================================================


class TestAPIModelBackwardCompatibility:
    """Test API models maintain backward compatibility."""

    def test_dataset_create_existing_fields(self):
        """Verify existing fields still work."""
        from backend_api.models import DatasetCreate

        # Should be able to create with just existing fields
        config = DatasetCreate(
            name="test-backward-compat",
            regime="LEO",
            timeframe=7,
            timeunit="days",
        )

        assert config.name == "test-backward-compat"
        assert config.regime == "LEO"
        assert config.timeframe == 7

    def test_dataset_create_new_fields_optional(self):
        """Verify new fields are optional (have defaults)."""
        from backend_api.models import DatasetCreate

        # Should work without specifying new fields
        config = DatasetCreate(name="test", regime="LEO")

        # New fields should have defaults
        assert hasattr(config, "target_percentage")
        assert hasattr(config, "output_tracktle")

    def test_dataset_create_validation_unchanged(self):
        """Verify validation rules still work."""
        from backend_api.models import DatasetCreate

        # Valid regimes should still be accepted
        for regime in ["LEO", "MEO", "GEO", "HEO"]:
            config = DatasetCreate(name="test", regime=regime)
            assert config.regime == regime


# =============================================================================
# TRACKTLE MODULE BACKWARD COMPATIBILITY
# =============================================================================


class TestTrackTLEBackwardCompatibility:
    """Test TrackTLE module maintains compatibility."""

    def test_observation_dataclass_fields(self):
        """Verify Observation dataclass has expected fields."""
        from uct_benchmark.simulation.tracktle import Observation

        obs = Observation(
            epoch=datetime(2024, 1, 1),
            ra_deg=180.0,
            dec_deg=45.0,
            site_code="GEODSS",
            site_lat=20.7,
            site_lon=-156.3,
            site_alt_km=3.1,
        )

        # All fields should be accessible
        assert obs.epoch == datetime(2024, 1, 1)
        assert obs.ra_deg == 180.0
        assert obs.dec_deg == 45.0

    def test_tracktle_result_dataclass_fields(self):
        """Verify TrackTLEResult dataclass has expected fields."""
        from uct_benchmark.simulation.tracktle import TrackTLEResult

        result = TrackTLEResult(
            tle_line1="test_line1",
            tle_line2="test_line2",
            epoch=datetime(2024, 1, 1),
            position_km=np.array([1, 2, 3]),
            velocity_km_s=np.array([4, 5, 6]),
        )

        assert result.tle_line1 == "test_line1"
        assert result.tle_line2 == "test_line2"
        assert result.convergence_status == "unknown"  # Default value


# =============================================================================
# DATA MANIPULATION BACKWARD COMPATIBILITY
# =============================================================================


class TestDataManipulationBackwardCompatibility:
    """Test data manipulation functions still work."""

    def test_add_non_reference_observations_exists(self):
        """Verify function exists and is callable."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations
        assert callable(add_non_reference_observations)

    def test_bin_tracks_exists(self):
        """Verify binTracks function exists."""
        from uct_benchmark.data.dataManipulation import binTracks
        assert callable(binTracks)


# =============================================================================
# OBJECT TYPE FILTERING BACKWARD COMPATIBILITY
# =============================================================================


class TestObjectTypeFilteringBackwardCompatibility:
    """Test object type filtering maintains compatibility."""

    def test_filter_function_exists(self):
        """Verify filter function exists."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code
        assert callable(filter_by_object_type_code)

    def test_object_filter_config_exists(self):
        """Verify ObjectFilterConfig exists."""
        from uct_benchmark.data.objectTypeFiltering import ObjectFilterConfig
        assert ObjectFilterConfig is not None


# =============================================================================
# EVENT DETECTION BACKWARD COMPATIBILITY
# =============================================================================


class TestEventDetectionBackwardCompatibility:
    """Test event detection maintains compatibility."""

    def test_filter_by_event_code_exists(self):
        """Verify function exists."""
        from uct_benchmark.data.eventDetection import filter_satellites_by_event_code
        assert callable(filter_satellites_by_event_code)

    def test_event_detection_config_exists(self):
        """Verify config class exists."""
        from uct_benchmark.data.eventDetection import EventDetectionConfig
        assert EventDetectionConfig is not None


# =============================================================================
# LEGACY CODE MAPPING BACKWARD COMPATIBILITY
# =============================================================================


class TestLegacyCodeMappingBackwardCompatibility:
    """Test legacy code mappings are unchanged."""

    def test_object_type_map_unchanged(self):
        """Verify object type map is consistent."""
        from uct_benchmark.settings import LEGACY_OBJECT_TYPE_MAP

        expected = {
            "H": "HAMR",
            "C": "PROX",
            "A": "APRX",
            "U": "NORM",
            "N": "CALIB",
        }

        for key, value in expected.items():
            assert key in LEGACY_OBJECT_TYPE_MAP
            assert LEGACY_OBJECT_TYPE_MAP[key] == value

    def test_event_map_unchanged(self):
        """Verify event map is consistent."""
        from uct_benchmark.settings import LEGACY_EVENT_MAP

        expected = {
            "MB": "MAN",
            "BU": "BRK",
            "LL": "LLT",
            "NE": "NRM",
        }

        for key, value in expected.items():
            assert key in LEGACY_EVENT_MAP
            assert LEGACY_EVENT_MAP[key] == value


# =============================================================================
# ENFORCE TARGET PERCENTAGE BACKWARD COMPATIBILITY
# =============================================================================


class TestEnforceTargetPercentageBackwardCompatibility:
    """Test enforce_target_percentage works correctly."""

    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame."""
        return pd.DataFrame({
            "satNo": [25544] * 10 + [25545] * 10 + [25546] * 10,
            "id": [f"obs_{i}" for i in range(30)],
            "obTime": [datetime(2024, 1, 1, i) for i in range(30)],
        })

    def test_returns_tuple(self, sample_df):
        """Verify function returns (DataFrame, dict) tuple."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        result = enforce_target_percentage(
            obs_df=sample_df,
            object_type_sats=[25544],
            all_sats=[25544, 25545, 25546],
            target_percentage="50",
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], pd.DataFrame)
        assert isinstance(result[1], dict)

    def test_preserves_dataframe_structure(self, sample_df):
        """Verify DataFrame structure is preserved."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        original_columns = set(sample_df.columns)

        result_df, _ = enforce_target_percentage(
            obs_df=sample_df,
            object_type_sats=[25544],
            all_sats=[25544, 25545, 25546],
            target_percentage="50",
        )

        assert set(result_df.columns) == original_columns

    def test_un_returns_unchanged(self, sample_df):
        """Verify UN returns unchanged data."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        original_len = len(sample_df)

        result_df, metadata = enforce_target_percentage(
            obs_df=sample_df,
            object_type_sats=[25544],
            all_sats=[25544, 25545, 25546],
            target_percentage="UN",
        )

        assert len(result_df) == original_len
        assert metadata["enforced"] == False


# =============================================================================
# THRESHOLDS LIST BACKWARD COMPATIBILITY
# =============================================================================


class TestThresholdsBackwardCompatibility:
    """Test thresholds list maintains compatibility."""

    def test_existing_thresholds_present(self):
        """Verify existing thresholds are still present."""
        from uct_benchmark.settings import thresholds

        # T1-T4 should still be present
        for tier in ["T1", "T2", "T3", "T4"]:
            assert tier in thresholds

    def test_thresholds_order_maintained(self):
        """Verify threshold order is maintained."""
        from uct_benchmark.settings import thresholds

        # T1 should come before T2, etc.
        t1_first = thresholds.index("T1")
        t4_last = max(i for i, t in enumerate(thresholds) if t == "T4")

        assert t1_first < t4_last


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
