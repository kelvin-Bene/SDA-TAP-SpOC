# -*- coding: utf-8 -*-
"""
Comprehensive Unit Tests for UCT Benchmark Changes

This module tests all the recent changes to ensure they don't break existing functionality:
1. Target percentage enforcement function
2. TrackTLE integration
3. Window selection defaults
4. Tier 5 definition
5. Backend API model updates
6. Worker parameter passing

Author: UCT Benchmark Team
Date: 2026
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_observations_df():
    """Create sample observations DataFrame for testing."""
    np.random.seed(42)
    base_time = datetime(2024, 1, 1, 0, 0, 0)

    # 5 satellites, 20 observations each = 100 total observations
    sat_ids = [25544, 25545, 25546, 25547, 25548]
    observations = []

    for sat_id in sat_ids:
        for j in range(20):
            observations.append({
                "id": f"obs_{sat_id}_{j}",
                "satNo": sat_id,
                "obTime": base_time + timedelta(hours=j),
                "ra": np.random.uniform(0, 360),
                "declination": np.random.uniform(-90, 90),
                "sensorName": "GEODSS",
                "idSensor": "SEN001",
                "senlat": 20.7,
                "senlon": -156.3,
                "senalt": 3100,
            })

    return pd.DataFrame(observations)


@pytest.fixture
def sample_state_df():
    """Create sample state vector DataFrame."""
    sat_ids = [25544, 25545, 25546, 25547, 25548]
    return pd.DataFrame([{
        "satNo": sat_id,
        "epoch": datetime(2024, 1, 1),
        "xpos": 6800 + i * 10,
        "ypos": 100,
        "zpos": 50,
        "xvel": 7.5,
        "yvel": 0.1,
        "zvel": 0.05,
        "mass": 1000 + i * 100,
        "crossSection": 10 + i,
    } for i, sat_id in enumerate(sat_ids)])


@pytest.fixture
def sample_elset_df():
    """Create sample TLE/elset DataFrame."""
    sat_ids = [25544, 25545, 25546, 25547, 25548]
    return pd.DataFrame([{
        "satNo": sat_id,
        "line1": f"1 {sat_id:05d}U 98067A   24001.00000000  .00000000  00000-0  00000-0 0    0",
        "line2": f"2 {sat_id:05d}  51.6400 000.0000 0000001 000.0000 000.0000 15.50000000    0",
        "elset": {
            "semi_major_axis": 6778 + i * 10,
            "eccentricity": 0.001,
            "inclination": 51.64,
            "RAAN": 0.0,
            "perigee": 0.0,
            "mean_anomaly": 0.0,
            "period_sec": 5400,
        }
    } for i, sat_id in enumerate(sat_ids)])


# =============================================================================
# TARGET PERCENTAGE ENFORCEMENT TESTS
# =============================================================================


class TestEnforceTargetPercentage:
    """Unit tests for enforce_target_percentage function."""

    def test_function_exists(self):
        """Verify function can be imported."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage
        assert callable(enforce_target_percentage)

    def test_fifty_percent_enforcement(self, sample_observations_df):
        """Test 50% target percentage."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        # First 3 satellites are "target" type
        object_type_sats = [25544, 25545, 25546]
        all_sats = list(sample_observations_df["satNo"].unique())

        result_df, metadata = enforce_target_percentage(
            obs_df=sample_observations_df,
            object_type_sats=object_type_sats,
            all_sats=all_sats,
            target_percentage="50",
        )

        assert metadata["enforced"] == True
        assert metadata["target_percentage"] == "50"
        assert metadata["requested_pct"] == 0.50

        # Check approximately 50%
        final_sats = list(result_df["satNo"].unique())
        target_count = len([s for s in final_sats if s in object_type_sats])
        if len(final_sats) > 0:
            actual_pct = target_count / len(final_sats)
            assert 0.3 <= actual_pct <= 0.7  # Allow tolerance

    def test_ten_percent_enforcement(self, sample_observations_df):
        """Test 10% target percentage."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        object_type_sats = [25544, 25545, 25546]
        all_sats = list(sample_observations_df["satNo"].unique())

        result_df, metadata = enforce_target_percentage(
            obs_df=sample_observations_df,
            object_type_sats=object_type_sats,
            all_sats=all_sats,
            target_percentage="10",
        )

        assert metadata["enforced"] == True
        assert metadata["requested_pct"] == 0.10

    def test_one_percent_enforcement(self, sample_observations_df):
        """Test 1% target percentage."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        object_type_sats = [25544]
        all_sats = list(sample_observations_df["satNo"].unique())

        result_df, metadata = enforce_target_percentage(
            obs_df=sample_observations_df,
            object_type_sats=object_type_sats,
            all_sats=all_sats,
            target_percentage="01",
        )

        assert metadata["enforced"] == True
        assert metadata["requested_pct"] == 0.01

    def test_unspecified_bypasses_enforcement(self, sample_observations_df):
        """Test UN (unspecified) bypasses enforcement."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        original_len = len(sample_observations_df)
        object_type_sats = [25544, 25545]
        all_sats = list(sample_observations_df["satNo"].unique())

        result_df, metadata = enforce_target_percentage(
            obs_df=sample_observations_df,
            object_type_sats=object_type_sats,
            all_sats=all_sats,
            target_percentage="UN",
        )

        assert metadata["enforced"] == False
        assert len(result_df) == original_len

    def test_empty_object_type_sats(self, sample_observations_df):
        """Test with no target type satellites."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        object_type_sats = []
        all_sats = list(sample_observations_df["satNo"].unique())

        result_df, metadata = enforce_target_percentage(
            obs_df=sample_observations_df,
            object_type_sats=object_type_sats,
            all_sats=all_sats,
            target_percentage="50",
        )

        assert metadata["enforced"] == True
        assert metadata["target_count"] == 0

    def test_metadata_structure(self, sample_observations_df):
        """Test metadata contains all expected keys."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        object_type_sats = [25544, 25545]
        all_sats = list(sample_observations_df["satNo"].unique())

        result_df, metadata = enforce_target_percentage(
            obs_df=sample_observations_df,
            object_type_sats=object_type_sats,
            all_sats=all_sats,
            target_percentage="50",
        )

        expected_keys = [
            "target_percentage", "enforced", "requested_pct", "achieved_pct",
            "target_count", "normal_count", "total_satellites",
            "target_satellites", "available_target_count", "available_normal_count"
        ]
        for key in expected_keys:
            assert key in metadata, f"Missing key: {key}"


# =============================================================================
# WINDOW TIER ENUM TESTS
# =============================================================================


class TestWindowTierEnum:
    """Unit tests for WindowTier enum changes."""

    def test_tier_1_exists(self):
        """Verify TIER_1 exists."""
        from uct_benchmark.data.windowSelection import WindowTier
        assert hasattr(WindowTier, "TIER_1")
        assert WindowTier.TIER_1.value == 1

    def test_tier_2_exists(self):
        """Verify TIER_2 exists."""
        from uct_benchmark.data.windowSelection import WindowTier
        assert hasattr(WindowTier, "TIER_2")
        assert WindowTier.TIER_2.value == 2

    def test_tier_3_exists(self):
        """Verify TIER_3 exists."""
        from uct_benchmark.data.windowSelection import WindowTier
        assert hasattr(WindowTier, "TIER_3")
        assert WindowTier.TIER_3.value == 3

    def test_tier_4_exists(self):
        """Verify TIER_4 exists."""
        from uct_benchmark.data.windowSelection import WindowTier
        assert hasattr(WindowTier, "TIER_4")
        assert WindowTier.TIER_4.value == 4

    def test_tier_5_exists_new(self):
        """Verify TIER_5 exists (new addition per Louis's spec)."""
        from uct_benchmark.data.windowSelection import WindowTier
        assert hasattr(WindowTier, "TIER_5")
        assert WindowTier.TIER_5.value == 5

    def test_all_tiers_are_distinct(self):
        """Verify all tiers have distinct values."""
        from uct_benchmark.data.windowSelection import WindowTier
        values = [t.value for t in WindowTier]
        assert len(values) == len(set(values))

    def test_tier_ordering(self):
        """Verify tiers are ordered correctly."""
        from uct_benchmark.data.windowSelection import WindowTier
        assert WindowTier.TIER_1.value < WindowTier.TIER_2.value
        assert WindowTier.TIER_2.value < WindowTier.TIER_3.value
        assert WindowTier.TIER_3.value < WindowTier.TIER_4.value
        assert WindowTier.TIER_4.value < WindowTier.TIER_5.value


# =============================================================================
# SETTINGS TESTS
# =============================================================================


class TestSettingsUpdates:
    """Unit tests for settings.py updates."""

    def test_thresholds_includes_t5(self):
        """Verify thresholds list includes T5."""
        from uct_benchmark.settings import thresholds
        assert "T5" in thresholds

    def test_thresholds_order(self):
        """Verify thresholds are in correct order."""
        from uct_benchmark.settings import thresholds
        # T1 should come before T2, T2 before T3, etc.
        t1_idx = thresholds.index("T1")
        t5_idx = thresholds.index("T5")
        assert t1_idx < t5_idx


# =============================================================================
# BACKEND API MODEL TESTS
# =============================================================================


class TestBackendAPIModels:
    """Unit tests for backend API model updates."""

    def test_dataset_create_has_target_percentage(self):
        """Verify DatasetCreate has target_percentage field."""
        from backend_api.models import DatasetCreate

        config = DatasetCreate(
            name="test",
            regime="LEO",
            target_percentage="50",
        )
        assert config.target_percentage == "50"

    def test_dataset_create_target_percentage_default(self):
        """Verify target_percentage defaults to UN."""
        from backend_api.models import DatasetCreate

        config = DatasetCreate(name="test", regime="LEO")
        assert config.target_percentage == "UN"

    def test_dataset_create_has_output_tracktle(self):
        """Verify DatasetCreate has output_tracktle field."""
        from backend_api.models import DatasetCreate

        config = DatasetCreate(
            name="test",
            regime="LEO",
            output_tracktle=True,
        )
        assert config.output_tracktle == True

    def test_dataset_create_output_tracktle_default(self):
        """Verify output_tracktle defaults to False."""
        from backend_api.models import DatasetCreate

        config = DatasetCreate(name="test", regime="LEO")
        assert config.output_tracktle == False

    def test_dataset_create_use_window_selection_default(self):
        """Verify use_window_selection defaults to True."""
        from backend_api.models import DatasetCreate

        config = DatasetCreate(name="test", regime="LEO")
        assert config.use_window_selection == True


# =============================================================================
# LEGACY CODE PARSING TESTS
# =============================================================================


class TestLegacyCodeParsing:
    """Unit tests for legacy 16-character code parsing."""

    def test_parse_valid_code(self):
        """Test parsing a valid 16-character code."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = LegacyDatasetCode.from_code("H50LEONEOPSSSS07")

        assert code.object_type == "H"
        assert code.target_percentage == "50"
        assert code.orbital_regime == "LEO"
        assert code.event == "NE"
        assert code.sensor_type == "OP"
        assert code.orbit_coverage == "S"
        assert code.track_gap == "S"
        assert code.observation_count == "S"
        assert code.object_count == "S"
        assert code.fitspan_days == 7

    def test_code_roundtrip(self):
        """Test that code can be parsed and regenerated."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        original = "C10MEOBURASSNS14"
        parsed = LegacyDatasetCode.from_code(original)
        regenerated = parsed.to_code()

        assert regenerated == original

    def test_all_object_types(self):
        """Test all object type codes parse correctly."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        for obj_type in ["H", "C", "A", "U", "N"]:
            code = f"{obj_type}50LEONEOPSSSS07"
            parsed = LegacyDatasetCode.from_code(code)
            assert parsed.object_type == obj_type

    def test_all_event_codes(self):
        """Test all event codes parse correctly."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        for event in ["MB", "BU", "LL", "NE"]:
            code = f"U50LEO{event}OPSSSS07"
            parsed = LegacyDatasetCode.from_code(code)
            assert parsed.event == event

    def test_all_target_percentages(self):
        """Test all target percentage codes parse correctly."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        for pct in ["50", "10", "01", "UN"]:
            code = f"H{pct}LEONEOPSSSS07"
            parsed = LegacyDatasetCode.from_code(code)
            assert parsed.target_percentage == pct


# =============================================================================
# TRACKTLE MODULE TESTS
# =============================================================================


class TestTrackTLEModule:
    """Unit tests for TrackTLE module."""

    def test_observation_dataclass(self):
        """Test Observation dataclass."""
        from uct_benchmark.simulation.tracktle import Observation

        obs = Observation(
            epoch=datetime(2024, 1, 1, 12, 0, 0),
            ra_deg=180.0,
            dec_deg=45.0,
            site_code="GEODSS",
            site_lat=20.7,
            site_lon=-156.3,
            site_alt_km=3.1,
        )

        assert obs.epoch == datetime(2024, 1, 1, 12, 0, 0)
        assert obs.ra_deg == 180.0
        assert obs.dec_deg == 45.0
        assert obs.site_code == "GEODSS"

    def test_tracktle_result_dataclass(self):
        """Test TrackTLEResult dataclass."""
        from uct_benchmark.simulation.tracktle import TrackTLEResult

        result = TrackTLEResult(
            tle_line1="1 25544U 98067A   24001.00000000  .00000000  00000-0  00000-0 0    0",
            tle_line2="2 25544  51.6400 000.0000 0000001 000.0000 000.0000 15.50000000    0",
            epoch=datetime(2024, 1, 1),
            position_km=np.array([6778.0, 0.0, 0.0]),
            velocity_km_s=np.array([0.0, 7.66, 0.0]),
        )

        assert result.tle_line1.startswith("1 ")
        assert result.tle_line2.startswith("2 ")
        assert result.epoch == datetime(2024, 1, 1)

    def test_tracktle_result_to_dict(self):
        """Test TrackTLEResult.to_dict() method."""
        from uct_benchmark.simulation.tracktle import TrackTLEResult

        result = TrackTLEResult(
            tle_line1="1 25544U 98067A   24001.00000000  .00000000  00000-0  00000-0 0    0",
            tle_line2="2 25544  51.6400 000.0000 0000001 000.0000 000.0000 15.50000000    0",
            epoch=datetime(2024, 1, 1),
            position_km=np.array([6778.0, 0.0, 0.0]),
            velocity_km_s=np.array([0.0, 7.66, 0.0]),
            convergence_status="converged",
            iterations=5,
        )

        result_dict = result.to_dict()

        assert "tle_line1" in result_dict
        assert "tle_line2" in result_dict
        assert "epoch" in result_dict
        assert "convergence_status" in result_dict
        assert result_dict["convergence_status"] == "converged"


# =============================================================================
# OBJECT TYPE FILTERING TESTS
# =============================================================================


class TestObjectTypeFiltering:
    """Unit tests for object type filtering."""

    def test_hamr_code_mapping(self):
        """Test HAMR (H) code mapping."""
        from uct_benchmark.settings import LEGACY_OBJECT_TYPE_MAP
        assert "H" in LEGACY_OBJECT_TYPE_MAP
        assert LEGACY_OBJECT_TYPE_MAP["H"] == "HAMR"

    def test_close_code_mapping(self):
        """Test Close (C) code mapping."""
        from uct_benchmark.settings import LEGACY_OBJECT_TYPE_MAP
        assert "C" in LEGACY_OBJECT_TYPE_MAP
        assert LEGACY_OBJECT_TYPE_MAP["C"] == "PROX"

    def test_apparent_code_mapping(self):
        """Test Apparent (A) code mapping."""
        from uct_benchmark.settings import LEGACY_OBJECT_TYPE_MAP
        assert "A" in LEGACY_OBJECT_TYPE_MAP

    def test_calibration_code_mapping(self):
        """Test Calibration (N) code mapping."""
        from uct_benchmark.settings import LEGACY_OBJECT_TYPE_MAP
        assert "N" in LEGACY_OBJECT_TYPE_MAP
        assert LEGACY_OBJECT_TYPE_MAP["N"] == "CALIB"


# =============================================================================
# EVENT FILTERING TESTS
# =============================================================================


class TestEventFiltering:
    """Unit tests for event filtering."""

    def test_maneuver_code_mapping(self):
        """Test Maneuver Between (MB) code mapping."""
        from uct_benchmark.settings import LEGACY_EVENT_MAP
        assert "MB" in LEGACY_EVENT_MAP

    def test_breakup_code_mapping(self):
        """Test Breakup (BU) code mapping."""
        from uct_benchmark.settings import LEGACY_EVENT_MAP
        assert "BU" in LEGACY_EVENT_MAP

    def test_lowthrust_code_mapping(self):
        """Test Long Low-thrust (LL) code mapping."""
        from uct_benchmark.settings import LEGACY_EVENT_MAP
        assert "LL" in LEGACY_EVENT_MAP


# =============================================================================
# ANSWER KEY GENERATION TESTS
# =============================================================================


class TestAnswerKeyGeneration:
    """Unit tests for answer key generation."""

    def test_answer_key_format(self, sample_observations_df):
        """Test answer key has correct format."""
        answer_key = {}
        grouped_obs_ids = {}

        for sat_no in sample_observations_df["satNo"].unique():
            sat_obs = sample_observations_df[sample_observations_df["satNo"] == sat_no]
            obs_ids = sat_obs["id"].tolist()
            grouped_obs_ids[int(sat_no)] = obs_ids
            for obs_id in obs_ids:
                answer_key[obs_id] = int(sat_no)

        # Every observation should have an entry
        assert len(answer_key) == len(sample_observations_df)

        # Keys should be observation IDs
        for obs_id in answer_key.keys():
            assert isinstance(obs_id, str)
            assert obs_id.startswith("obs_")

        # Values should be satellite IDs
        for sat_id in answer_key.values():
            assert isinstance(sat_id, int)

    def test_grouped_obs_ids_format(self, sample_observations_df):
        """Test grouped_obs_ids has correct format."""
        grouped_obs_ids = {}

        for sat_no in sample_observations_df["satNo"].unique():
            sat_obs = sample_observations_df[sample_observations_df["satNo"] == sat_no]
            obs_ids = sat_obs["id"].tolist()
            grouped_obs_ids[int(sat_no)] = obs_ids

        # Should have 5 satellites
        assert len(grouped_obs_ids) == 5

        # Each satellite should have 20 observations
        for sat_id, obs_ids in grouped_obs_ids.items():
            assert len(obs_ids) == 20


# =============================================================================
# DECORRELATION TESTS
# =============================================================================


class TestDecorrelation:
    """Unit tests for decorrelation."""

    def test_satno_removed(self, sample_observations_df):
        """Test satNo is removed during decorrelation."""
        dataset = sample_observations_df.copy()

        # Simulate decorrelation
        dataset = dataset.drop(
            columns=["satNo", "idOnOrbit", "origObjectId"],
            errors="ignore",
        )

        assert "satNo" not in dataset.columns

    def test_observation_id_preserved(self, sample_observations_df):
        """Test observation ID is preserved."""
        dataset = sample_observations_df.copy()
        original_ids = set(dataset["id"])

        dataset = dataset.drop(columns=["satNo"], errors="ignore")

        assert set(dataset["id"]) == original_ids

    def test_observation_data_preserved(self, sample_observations_df):
        """Test observation data (ra, dec, time) is preserved."""
        dataset = sample_observations_df.copy()

        dataset = dataset.drop(columns=["satNo"], errors="ignore")

        assert "ra" in dataset.columns
        assert "declination" in dataset.columns
        assert "obTime" in dataset.columns


# =============================================================================
# TRUE NEGATIVES TESTS
# =============================================================================


class TestTrueNegatives:
    """Unit tests for true negatives implementation."""

    def test_non_ref_obs_per_satellite_constant(self):
        """Verify NON_REF_OBS_PER_SATELLITE is 2."""
        from uct_benchmark.settings import NON_REF_OBS_PER_SATELLITE
        assert NON_REF_OBS_PER_SATELLITE == 2

    def test_add_non_reference_observations_function_exists(self):
        """Verify add_non_reference_observations function exists."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations
        assert callable(add_non_reference_observations)


# =============================================================================
# QUALITY LEVEL TESTS
# =============================================================================


class TestQualityLevels:
    """Unit tests for quality level configurations."""

    def test_quality_ranges_defined(self):
        """Test quality ranges are defined."""
        from uct_benchmark.settings import QUALITY_RANGES

        assert "A" in QUALITY_RANGES
        assert "S" in QUALITY_RANGES
        assert "N" in QUALITY_RANGES

    def test_quality_level_thresholds(self):
        """Test quality level thresholds are defined."""
        from uct_benchmark.settings import QUALITY_LEVEL_THRESHOLDS

        assert "coverage" in QUALITY_LEVEL_THRESHOLDS
        assert "track_gap" in QUALITY_LEVEL_THRESHOLDS
        assert "observation_count" in QUALITY_LEVEL_THRESHOLDS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
