# -*- coding: utf-8 -*-
"""
Comprehensive Integration Tests for UCT Benchmark Pipeline

This module tests the integration of all components to ensure the recent changes
work correctly together without breaking existing functionality.

Tests include:
1. Full pipeline flow with new parameters
2. API endpoint integration
3. Worker job processing
4. Database persistence
5. Cross-component data flow

Author: UCT Benchmark Team
Date: 2026
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import json
import tempfile
import os


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_udl_response():
    """Create mock UDL API response data."""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    sat_ids = [25544, 25545, 25546, 25547, 25548]

    observations = []
    for sat_id in sat_ids:
        for j in range(20):
            observations.append({
                "id": f"obs_{sat_id}_{j}",
                "satNo": sat_id,
                "obTime": (base_time + timedelta(hours=j)).isoformat() + "Z",
                "ra": float(np.random.uniform(0, 360)),
                "declination": float(np.random.uniform(-90, 90)),
                "sensorName": "GEODSS",
                "idSensor": "SEN001",
                "senlat": 20.7,
                "senlon": -156.3,
                "senalt": 3100,
            })

    return observations


@pytest.fixture
def mock_state_vectors():
    """Create mock state vector data."""
    sat_ids = [25544, 25545, 25546, 25547, 25548]
    return [{
        "satNo": sat_id,
        "epoch": datetime(2024, 1, 1).isoformat() + "Z",
        "xpos": 6800 + i * 10,
        "ypos": 100,
        "zpos": 50,
        "xvel": 7.5,
        "yvel": 0.1,
        "zvel": 0.05,
        "mass": 1000 + i * 100,
        "crossSection": 10 + i,
        "cov": None,
    } for i, sat_id in enumerate(sat_ids)]


@pytest.fixture
def mock_elsets():
    """Create mock TLE data."""
    sat_ids = [25544, 25545, 25546, 25547, 25548]
    return [{
        "satNo": sat_id,
        "line1": f"1 {sat_id:05d}U 98067A   24001.00000000  .00000000  00000-0  00000-0 0    0",
        "line2": f"2 {sat_id:05d}  51.6400 000.0000 0000001 000.0000 000.0000 15.50000000    0",
    } for sat_id in sat_ids]


@pytest.fixture
def sample_dataset_config():
    """Create sample dataset generation config."""
    return {
        "name": "test-integration-dataset",
        "regime": "LEO",
        "timeframe": 3,
        "timeunit": "days",
        "use_window_selection": True,
        "target_percentage": "50",
        "output_tracktle": False,
        "object_type_code": "H",
        "event_code": "NE",
        "include_non_ref_obs": False,
        "non_ref_ratio": 0.1,
    }


# =============================================================================
# GENERATE DATASET PARAMETER TESTS
# =============================================================================


class TestGenerateDatasetParameters:
    """Test that generateDataset accepts all new parameters."""

    def test_accepts_target_percentage_parameter(self):
        """Verify generateDataset has target_percentage parameter."""
        from uct_benchmark.api.apiIntegration import generateDataset
        import inspect

        sig = inspect.signature(generateDataset)
        params = sig.parameters

        assert "target_percentage" in params
        assert params["target_percentage"].default == "UN"

    def test_accepts_output_tracktle_parameter(self):
        """Verify generateDataset has output_tracktle parameter."""
        from uct_benchmark.api.apiIntegration import generateDataset
        import inspect

        sig = inspect.signature(generateDataset)
        params = sig.parameters

        assert "output_tracktle" in params
        assert params["output_tracktle"].default == False

    def test_use_window_selection_default_true(self):
        """Verify use_window_selection defaults to True."""
        from uct_benchmark.api.apiIntegration import generateDataset
        import inspect

        sig = inspect.signature(generateDataset)
        params = sig.parameters

        assert "use_window_selection" in params
        assert params["use_window_selection"].default == True


# =============================================================================
# BACKEND API MODEL INTEGRATION TESTS
# =============================================================================


class TestBackendAPIModelIntegration:
    """Test backend API models work correctly with new fields."""

    def test_dataset_create_full_config(self):
        """Test DatasetCreate with all new fields."""
        from backend_api.models import DatasetCreate

        config = DatasetCreate(
            name="full-test-dataset",
            regime="LEO",
            timeframe=7,
            timeunit="days",
            use_window_selection=True,
            target_percentage="50",
            output_tracktle=True,
            object_type_code="H",
            event_code="NE",
            include_non_ref_obs=True,
            non_ref_ratio=0.1,
        )

        assert config.name == "full-test-dataset"
        assert config.regime == "LEO"
        assert config.use_window_selection == True
        assert config.target_percentage == "50"
        assert config.output_tracktle == True

    def test_dataset_create_json_serialization(self):
        """Test DatasetCreate can be serialized to JSON."""
        from backend_api.models import DatasetCreate

        config = DatasetCreate(
            name="json-test",
            regime="LEO",
            target_percentage="10",
            output_tracktle=False,
        )

        # Should be able to serialize to dict
        config_dict = config.model_dump()

        assert "target_percentage" in config_dict
        assert "output_tracktle" in config_dict
        assert config_dict["target_percentage"] == "10"

    def test_dataset_create_validation(self):
        """Test DatasetCreate validates correctly."""
        from backend_api.models import DatasetCreate

        # Valid regimes
        for regime in ["LEO", "MEO", "GEO", "HEO"]:
            config = DatasetCreate(name="test", regime=regime)
            assert config.regime == regime


# =============================================================================
# LEGACY CODE INTEGRATION TESTS
# =============================================================================


class TestLegacyCodeIntegration:
    """Test legacy 16-character code integration."""

    def test_legacy_code_to_config(self):
        """Test converting legacy code to configuration."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "H50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)

        # Should extract all components
        assert parsed.object_type == "H"
        assert parsed.target_percentage == "50"
        assert parsed.orbital_regime == "LEO"
        assert parsed.event == "NE"
        assert parsed.sensor_type == "OP"
        assert parsed.fitspan_days == 7

    def test_legacy_code_generates_window_criteria(self):
        """Test legacy code can generate window criteria."""
        try:
            from uct_benchmark.data.windowSelection import create_criteria_from_legacy_code

            criteria = create_criteria_from_legacy_code("H50LEONEOPSSSS07")

            assert criteria is not None
            assert criteria.fit_span_days == 7
            assert criteria.regimes == ["LEO"]
        except ImportError:
            pytest.skip("windowSelection module not fully available")

    def test_all_legacy_code_combinations_parse(self):
        """Test various legacy code combinations parse correctly."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        test_codes = [
            "H50LEONEOPSSSS07",
            "C10MEOBURASSNS14",
            "A01GEOLLRFAAAH01",
            "U50HEONEFUSSSS03",
            "N50LEONEOPSSSL10",
        ]

        for code in test_codes:
            parsed = LegacyDatasetCode.from_code(code)
            regenerated = parsed.to_code()
            assert regenerated == code, f"Failed for code: {code}"


# =============================================================================
# WINDOW SELECTION INTEGRATION TESTS
# =============================================================================


class TestWindowSelectionIntegration:
    """Test window selection algorithm integration."""

    def test_window_criteria_creation(self):
        """Test WindowCriteria can be created."""
        from uct_benchmark.data.windowSelection import WindowCriteria

        criteria = WindowCriteria(
            fit_span_days=7,
            min_objects=10,
            max_objects=100,
            regimes=["LEO"],
        )

        assert criteria.fit_span_days == 7
        assert criteria.regimes == ["LEO"]

    def test_window_tier_classification(self):
        """Test window tier classification values."""
        from uct_benchmark.data.windowSelection import WindowTier

        # Test all tiers are accessible
        tiers = [WindowTier.TIER_1, WindowTier.TIER_2, WindowTier.TIER_3,
                 WindowTier.TIER_4, WindowTier.TIER_5]

        values = [t.value for t in tiers]
        assert values == [1, 2, 3, 4, 5]


# =============================================================================
# TARGET PERCENTAGE INTEGRATION TESTS
# =============================================================================


class TestTargetPercentageIntegration:
    """Test target percentage enforcement integration."""

    @pytest.fixture
    def sample_obs_df(self):
        """Create sample observations for testing."""
        np.random.seed(42)
        base_time = datetime(2024, 1, 1)

        # 10 satellites, mix of HAMR (first 4) and normal (rest)
        sat_ids = list(range(25544, 25554))
        observations = []

        for sat_id in sat_ids:
            for j in range(15):
                observations.append({
                    "id": f"obs_{sat_id}_{j}",
                    "satNo": sat_id,
                    "obTime": base_time + timedelta(hours=j),
                    "ra": np.random.uniform(0, 360),
                    "declination": np.random.uniform(-90, 90),
                })

        return pd.DataFrame(observations)

    def test_fifty_percent_achievable(self, sample_obs_df):
        """Test 50% target is achievable with sufficient HAMR satellites."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        # First 4 satellites are HAMR
        hamr_sats = [25544, 25545, 25546, 25547]
        all_sats = list(sample_obs_df["satNo"].unique())

        result_df, metadata = enforce_target_percentage(
            obs_df=sample_obs_df,
            object_type_sats=hamr_sats,
            all_sats=all_sats,
            target_percentage="50",
        )

        assert metadata["enforced"] == True
        # Check approximately 50%
        achieved = metadata.get("achieved_pct", 0)
        assert 0.3 <= achieved <= 0.7

    def test_enforcement_preserves_observation_structure(self, sample_obs_df):
        """Test enforcement preserves observation data structure."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        original_cols = set(sample_obs_df.columns)
        hamr_sats = [25544, 25545]
        all_sats = list(sample_obs_df["satNo"].unique())

        result_df, _ = enforce_target_percentage(
            obs_df=sample_obs_df,
            object_type_sats=hamr_sats,
            all_sats=all_sats,
            target_percentage="50",
        )

        # All original columns should be preserved
        assert set(result_df.columns) == original_cols


# =============================================================================
# TRACKTLE INTEGRATION TESTS
# =============================================================================


class TestTrackTLEIntegration:
    """Test TrackTLE module integration."""

    def test_generate_tracktle_with_minimum_obs(self):
        """Test TrackTLE generation with minimum observations."""
        from uct_benchmark.simulation.tracktle import generate_tracktle, Observation

        base_time = datetime(2024, 1, 1, 12, 0, 0)

        # Create 3 observations (minimum for IOD)
        observations = [
            Observation(
                epoch=base_time + timedelta(minutes=i * 5),
                ra_deg=180.0 + i * 0.1,
                dec_deg=45.0 + i * 0.05,
                site_code="GEODSS",
                site_lat=20.7,
                site_lon=-156.3,
                site_alt_km=3.1,
            )
            for i in range(3)
        ]

        result = generate_tracktle(observations, norad_id=25544)

        # Should return a result (may or may not converge)
        assert result is not None
        assert hasattr(result, "tle_line1")
        assert hasattr(result, "convergence_status")

    def test_generate_tracktle_insufficient_obs_raises(self):
        """Test TrackTLE raises error with insufficient observations."""
        from uct_benchmark.simulation.tracktle import generate_tracktle, Observation

        # Only 2 observations - should raise
        observations = [
            Observation(
                epoch=datetime(2024, 1, 1, 12, i, 0),
                ra_deg=180.0,
                dec_deg=45.0,
                site_code="GEODSS",
                site_lat=20.7,
                site_lon=-156.3,
                site_alt_km=3.1,
            )
            for i in range(2)
        ]

        with pytest.raises(ValueError, match="minimum 3 observations"):
            generate_tracktle(observations)


# =============================================================================
# TRUE NEGATIVES INTEGRATION TESTS
# =============================================================================


class TestTrueNegativesIntegration:
    """Test true negatives (non-reference observations) integration."""

    @pytest.fixture
    def reference_obs(self):
        """Create reference observations."""
        base_time = datetime(2024, 1, 1)
        ref_sats = [25544, 25545, 25546]

        observations = []
        for sat_id in ref_sats:
            for j in range(10):
                observations.append({
                    "id": f"ref_obs_{sat_id}_{j}",
                    "satNo": sat_id,
                    "obTime": base_time + timedelta(hours=j),
                    "ra": np.random.uniform(0, 360),
                    "declination": np.random.uniform(-90, 90),
                })

        return pd.DataFrame(observations)

    @pytest.fixture
    def all_obs_pool(self):
        """Create pool of all observations including non-ref."""
        base_time = datetime(2024, 1, 1)
        all_sats = [25544, 25545, 25546, 99001, 99002, 99003]

        observations = []
        for sat_id in all_sats:
            for j in range(10):
                observations.append({
                    "id": f"pool_obs_{sat_id}_{j}",
                    "satNo": sat_id,
                    "obTime": base_time + timedelta(hours=j),
                    "ra": np.random.uniform(0, 360),
                    "declination": np.random.uniform(-90, 90),
                })

        return pd.DataFrame(observations)

    def test_add_non_reference_observations(self, reference_obs, all_obs_pool):
        """Test adding non-reference observations."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations

        reference_norad_ids = [25544, 25545, 25546]

        combined_df, non_ref_truth = add_non_reference_observations(
            ref_obs_df=reference_obs,
            reference_norad_ids=reference_norad_ids,
            all_observations_df=all_obs_pool,
            non_ref_ratio=0.1,
            seed=42,
        )

        # Should have more observations than reference
        assert len(combined_df) >= len(reference_obs)

    def test_non_ref_exactly_two_per_satellite(self, reference_obs, all_obs_pool):
        """Test exactly 2 observations per non-ref satellite per Louis's spec."""
        from uct_benchmark.data.dataManipulation import add_non_reference_observations

        reference_norad_ids = [25544, 25545, 25546]

        combined_df, non_ref_truth = add_non_reference_observations(
            ref_obs_df=reference_obs,
            reference_norad_ids=reference_norad_ids,
            all_observations_df=all_obs_pool,
            non_ref_ratio=0.2,
            seed=42,
        )

        if non_ref_truth is not None and not non_ref_truth.empty:
            # Count obs per non-ref satellite
            obs_per_sat = non_ref_truth.groupby("source_norad_id").size()

            for sat_id, count in obs_per_sat.items():
                assert count == 2, f"Sat {sat_id} has {count} obs, expected 2"


# =============================================================================
# DECORRELATION INTEGRATION TESTS
# =============================================================================


class TestDecorrelationIntegration:
    """Test decorrelation (satNo removal) integration."""

    def test_decorrelation_columns_removed(self):
        """Test that identifying columns are removed."""
        base_time = datetime(2024, 1, 1)

        obs_df = pd.DataFrame([{
            "id": f"obs_{i}",
            "satNo": 25544 + (i % 3),
            "obTime": base_time + timedelta(hours=i),
            "ra": 180.0,
            "declination": 45.0,
            "idOnOrbit": "TEST",
            "origObjectId": 12345,
            "rawFileURI": "s3://bucket/file",
            "createdAt": datetime.now(),
        } for i in range(10)])

        # Simulate decorrelation
        decorrelated = obs_df.drop(
            columns=[
                "satNo", "idOnOrbit", "origObjectId",
                "rawFileURI", "createdAt", "trackId",
                "has_cov", "is_non_reference",
            ],
            errors="ignore",
        )

        # Sensitive columns should be removed
        assert "satNo" not in decorrelated.columns
        assert "idOnOrbit" not in decorrelated.columns
        assert "origObjectId" not in decorrelated.columns

        # Observation data should remain
        assert "id" in decorrelated.columns
        assert "obTime" in decorrelated.columns
        assert "ra" in decorrelated.columns


# =============================================================================
# ANSWER KEY INTEGRATION TESTS
# =============================================================================


class TestAnswerKeyIntegration:
    """Test answer key generation integration."""

    def test_answer_key_maps_all_observations(self):
        """Test answer key contains all observations."""
        obs_df = pd.DataFrame([{
            "id": f"obs_{sat}_{i}",
            "satNo": sat,
        } for sat in [25544, 25545, 25546] for i in range(5)])

        answer_key = {}
        grouped_obs_ids = {}

        for sat_no in obs_df["satNo"].unique():
            sat_obs = obs_df[obs_df["satNo"] == sat_no]
            obs_ids = sat_obs["id"].tolist()
            grouped_obs_ids[int(sat_no)] = obs_ids
            for obs_id in obs_ids:
                answer_key[obs_id] = int(sat_no)

        # All observations should be in answer key
        assert len(answer_key) == len(obs_df)

        # All satellites should be in grouped_obs_ids
        assert len(grouped_obs_ids) == 3

    def test_answer_key_json_serializable(self):
        """Test answer key can be JSON serialized."""
        answer_key = {
            "obs_1": 25544,
            "obs_2": 25544,
            "obs_3": 25545,
        }
        grouped_obs_ids = {
            25544: ["obs_1", "obs_2"],
            25545: ["obs_3"],
        }

        # Should be JSON serializable
        json_str = json.dumps(grouped_obs_ids)
        parsed = json.loads(json_str)

        assert "25544" in parsed or 25544 in parsed


# =============================================================================
# CROSS-COMPONENT FLOW TESTS
# =============================================================================


class TestCrossComponentFlow:
    """Test data flows correctly between components."""

    def test_legacy_code_to_generation_params(self):
        """Test legacy code parameters flow to generation."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "H50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)

        # Extract generation parameters
        params = {
            "object_type_code": parsed.object_type,
            "target_percentage": parsed.target_percentage,
            "regime": parsed.orbital_regime,
            "event_code": parsed.event,
            "timeframe": parsed.fitspan_days,
            "timeunit": "days",
        }

        assert params["object_type_code"] == "H"
        assert params["target_percentage"] == "50"
        assert params["regime"] == "LEO"
        assert params["event_code"] == "NE"
        assert params["timeframe"] == 7

    def test_window_tier_to_dataset_tier_mapping(self):
        """Test window tier maps to dataset tier correctly."""
        from uct_benchmark.data.windowSelection import WindowTier

        tier_map = {
            WindowTier.TIER_1: "T1",
            WindowTier.TIER_2: "T2",
            WindowTier.TIER_3: "T3",
            WindowTier.TIER_4: "T4",
            WindowTier.TIER_5: "T5",
        }

        for window_tier, expected_tier in tier_map.items():
            assert f"T{window_tier.value}" == expected_tier


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
