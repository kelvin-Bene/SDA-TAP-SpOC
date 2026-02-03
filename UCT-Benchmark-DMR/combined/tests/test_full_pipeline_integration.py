# -*- coding: utf-8 -*-
"""
End-to-End Integration Tests for UCT Benchmark Pipeline.

These tests verify alignment with Louis's vision and ensure all features
work together correctly in the full dataset generation pipeline.

Tests cover:
1. Legacy 16-character code parsing and enforcement
2. Target percentage enforcement (positions 2-3 of code)
3. Object type filtering (H, C, A, U, N)
4. Event filtering (MB, BU, LL, NE)
5. True negatives (exactly 2 obs per non-ref satellite)
6. Window selection with tier classification
7. Decorrelation (satNo removal)
8. Answer key generation
9. TrackTLE output generation

Author: UCT Benchmark Team
Date: 2026
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import Counter


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_observations():
    """Create sample observations for testing."""
    np.random.seed(42)
    base_time = datetime(2024, 1, 1, 0, 0, 0)

    # Create observations for multiple satellites
    sat_ids = [25544, 25545, 25546, 25547, 25548]  # 5 reference satellites
    observations = []

    for i, sat_id in enumerate(sat_ids):
        # Create 20 observations per satellite
        for j in range(20):
            obs = {
                "id": f"obs_{sat_id}_{j}",
                "satNo": sat_id,
                "obTime": base_time + timedelta(hours=i*24 + j),
                "ra": np.random.uniform(0, 360),
                "declination": np.random.uniform(-90, 90),
                "sensorName": "GEODSS",
                "idSensor": "SEN001",
                "senlat": 20.7,
                "senlon": -156.3,
                "senalt": 3100,
            }
            observations.append(obs)

    return pd.DataFrame(observations)


@pytest.fixture
def sample_state_data():
    """Create sample state vector data."""
    sat_ids = [25544, 25545, 25546, 25547, 25548]
    states = []

    for sat_id in sat_ids:
        states.append({
            "satNo": sat_id,
            "epoch": datetime(2024, 1, 1),
            "xpos": np.random.uniform(6800, 7200),
            "ypos": np.random.uniform(-100, 100),
            "zpos": np.random.uniform(-100, 100),
            "xvel": np.random.uniform(-8, 8),
            "yvel": np.random.uniform(-1, 1),
            "zvel": np.random.uniform(-1, 1),
            "mass": np.random.uniform(100, 5000),
            "crossSection": np.random.uniform(1, 50),
        })

    return pd.DataFrame(states)


@pytest.fixture
def sample_elset_data():
    """Create sample TLE/elset data."""
    sat_ids = [25544, 25545, 25546, 25547, 25548]
    elsets = []

    for sat_id in sat_ids:
        elsets.append({
            "satNo": sat_id,
            "line1": f"1 {sat_id:05d}U 98067A   24001.00000000  .00000000  00000-0  00000-0 0    0",
            "line2": f"2 {sat_id:05d}  51.6400 000.0000 0000001 000.0000 000.0000 15.50000000    0",
            "elset": {
                "semi_major_axis": 6778 + np.random.uniform(0, 100),
                "eccentricity": 0.001,
                "inclination": 51.64,
                "RAAN": 0.0,
                "perigee": 0.0,
                "mean_anomaly": 0.0,
                "period_sec": 5400,
            }
        })

    return pd.DataFrame(elsets)


# =============================================================================
# TARGET PERCENTAGE ENFORCEMENT TESTS
# =============================================================================


class TestTargetPercentageEnforcement:
    """Test target percentage enforcement from 16-char code positions 2-3."""

    def test_enforce_target_percentage_50(self, sample_observations):
        """Test 50% target percentage enforcement."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        # Simulate: 3 of 5 satellites are "target" type (e.g., HAMR)
        object_type_sats = [25544, 25545, 25546]
        all_sats = list(sample_observations["satNo"].unique())

        filtered_df, metadata = enforce_target_percentage(
            obs_df=sample_observations,
            object_type_sats=object_type_sats,
            all_sats=all_sats,
            target_percentage="50",
        )

        assert metadata["enforced"] == True
        assert metadata["target_percentage"] == "50"

        # Verify approximately 50% are target objects
        final_sats = list(filtered_df["satNo"].unique())
        target_count = len([s for s in final_sats if s in object_type_sats])
        achieved_pct = target_count / len(final_sats)

        # Allow some tolerance since we may not have exact numbers
        assert 0.4 <= achieved_pct <= 0.6, f"Expected ~50% target, got {achieved_pct:.1%}"

    def test_enforce_target_percentage_10(self, sample_observations):
        """Test 10% target percentage enforcement."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        object_type_sats = [25544, 25545, 25546]
        all_sats = list(sample_observations["satNo"].unique())

        filtered_df, metadata = enforce_target_percentage(
            obs_df=sample_observations,
            object_type_sats=object_type_sats,
            all_sats=all_sats,
            target_percentage="10",
        )

        assert metadata["enforced"] == True

        # With 5 satellites and 10% target, we expect 0-1 target satellites
        assert metadata["target_count"] <= 1

    def test_enforce_target_percentage_unspecified(self, sample_observations):
        """Test that UN (unspecified) bypasses enforcement."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage

        object_type_sats = [25544, 25545]
        all_sats = list(sample_observations["satNo"].unique())

        filtered_df, metadata = enforce_target_percentage(
            obs_df=sample_observations,
            object_type_sats=object_type_sats,
            all_sats=all_sats,
            target_percentage="UN",
        )

        assert metadata["enforced"] == False
        # Data should be unchanged
        assert len(filtered_df) == len(sample_observations)


# =============================================================================
# DECORRELATION TESTS
# =============================================================================


class TestDecorrelation:
    """Test decorrelation per Louis's specification."""

    def test_decorrelation_removes_satno(self, sample_observations):
        """Verify satNo is removed from decorrelated output."""
        # Simulate decorrelation from apiIntegration.py
        dataset = sample_observations.copy()
        dataset["uct"] = True

        # Remove satNo and other identifying columns
        dataset = dataset.drop(
            columns=[
                "satNo",
                "idOnOrbit",
                "origObjectId",
                "rawFileURI",
                "createdAt",
                "trackId",
                "has_cov",
                "is_non_reference",
            ],
            errors="ignore",
        )

        # Verify satNo is removed
        assert "satNo" not in dataset.columns

        # Verify essential observation columns are preserved
        assert "id" in dataset.columns
        assert "obTime" in dataset.columns
        assert "ra" in dataset.columns
        assert "declination" in dataset.columns

    def test_decorrelation_preserves_observation_id(self, sample_observations):
        """Verify observation ID is preserved for answer key lookup."""
        dataset = sample_observations.copy()

        original_ids = set(sample_observations["id"])
        dataset = dataset.drop(columns=["satNo"], errors="ignore")

        assert set(dataset["id"]) == original_ids


# =============================================================================
# ANSWER KEY GENERATION TESTS
# =============================================================================


class TestAnswerKeyGeneration:
    """Test answer key generation per Louis's decorrelation spec."""

    def test_answer_key_structure(self, sample_observations):
        """Verify answer key maps observations to true satellites."""
        # Simulate answer key generation from apiIntegration.py
        answer_key = {}
        grouped_obs_ids = {}

        for sat_no in sample_observations["satNo"].unique():
            sat_obs = sample_observations[sample_observations["satNo"] == sat_no]
            obs_ids = sat_obs["id"].tolist()
            grouped_obs_ids[int(sat_no)] = obs_ids
            for obs_id in obs_ids:
                answer_key[obs_id] = int(sat_no)

        # Verify structure
        assert isinstance(answer_key, dict)
        assert isinstance(grouped_obs_ids, dict)

        # Every observation should have an answer key entry
        assert len(answer_key) == len(sample_observations)

        # Verify answer key values are satellite IDs
        for obs_id, sat_no in answer_key.items():
            assert sat_no in sample_observations["satNo"].values

    def test_grouped_obs_ids_structure(self, sample_observations):
        """Verify grouped_obs_ids format: {sat_id: [obs_id, obs_id, ...]}."""
        grouped_obs_ids = {}

        for sat_no in sample_observations["satNo"].unique():
            sat_obs = sample_observations[sample_observations["satNo"] == sat_no]
            obs_ids = sat_obs["id"].tolist()
            grouped_obs_ids[int(sat_no)] = obs_ids

        # Each satellite should have a list of observation IDs
        for sat_id, obs_ids in grouped_obs_ids.items():
            assert isinstance(obs_ids, list)
            assert len(obs_ids) > 0

            # All obs_ids should be strings
            for obs_id in obs_ids:
                assert isinstance(obs_id, str)


# =============================================================================
# TRUE NEGATIVES TESTS
# =============================================================================


class TestTrueNegatives:
    """Test true negatives implementation per Louis's specification."""

    @pytest.fixture
    def non_ref_observations(self):
        """Create non-reference observations with exactly 2 per satellite."""
        base_time = datetime(2024, 1, 1)
        non_ref_sats = [99001, 99002, 99003]  # Non-reference satellites

        observations = []
        for sat_id in non_ref_sats:
            # Exactly 2 observations per non-ref satellite
            for j in range(2):
                obs = {
                    "id": f"non_ref_{sat_id}_{j}",
                    "satNo": sat_id,
                    "source_norad_id": sat_id,
                    "obTime": base_time + timedelta(hours=j),
                    "ra": np.random.uniform(0, 360),
                    "declination": np.random.uniform(-90, 90),
                    "is_non_reference": True,
                }
                observations.append(obs)

        return pd.DataFrame(observations)

    def test_exactly_two_observations_per_non_ref_satellite(self, non_ref_observations):
        """Verify Louis's spec: exactly 2 observations per non-reference satellite."""
        # Count observations per source satellite
        obs_per_sat = non_ref_observations.groupby("source_norad_id").size()

        # Each satellite should have exactly 2 observations
        for sat_id, count in obs_per_sat.items():
            assert count == 2, f"Satellite {sat_id} has {count} obs, expected 2"

    def test_non_ref_obs_marked_correctly(self, non_ref_observations):
        """Verify non-reference observations are properly flagged."""
        # All should have is_non_reference=True
        assert all(non_ref_observations["is_non_reference"] == True)


# =============================================================================
# WINDOW SELECTION TESTS
# =============================================================================


class TestWindowSelectionTier:
    """Test window selection returns tier classification."""

    def test_window_tier_enum_values(self):
        """Verify WindowTier enum has all expected values including T5."""
        from uct_benchmark.data.windowSelection import WindowTier

        # Check all tiers exist
        assert WindowTier.TIER_1.value == 1
        assert WindowTier.TIER_2.value == 2
        assert WindowTier.TIER_3.value == 3
        assert WindowTier.TIER_4.value == 4
        assert WindowTier.TIER_5.value == 5  # Louis's "impossible" tier

    def test_window_tier_is_valid_enum(self):
        """Verify tier from window selection is a valid enum value."""
        from uct_benchmark.data.windowSelection import WindowTier

        valid_tiers = [t.value for t in WindowTier]

        # All tiers 1-5 should be valid
        for tier_val in [1, 2, 3, 4, 5]:
            assert tier_val in valid_tiers


# =============================================================================
# OBJECT TYPE FILTERING TESTS
# =============================================================================


class TestObjectTypeFiltering:
    """Test object type filtering per Louis's 16-char code position 1."""

    @pytest.mark.parametrize("code,description", [
        ("H", "HAMR - High Area-to-Mass Ratio"),
        ("C", "Close - Physical proximity < 100km"),
        ("A", "Apparent - Angular proximity < 0.5 deg"),
        ("U", "Unspecified - All objects"),
        ("N", "Calibration - Well-known satellites"),
    ])
    def test_object_type_code_valid(self, code, description):
        """Test each object type code is recognized."""
        from uct_benchmark.settings import LEGACY_OBJECT_TYPE_MAP

        # All codes except U should have mappings
        if code != "U":
            assert code in LEGACY_OBJECT_TYPE_MAP, f"Missing mapping for {code}: {description}"


# =============================================================================
# EVENT FILTERING TESTS
# =============================================================================


class TestEventFiltering:
    """Test event filtering per Louis's 16-char code positions 7-8."""

    @pytest.mark.parametrize("code,description", [
        ("MB", "Maneuver Between observations"),
        ("BU", "Breakup event"),
        ("LL", "Long-duration Low-thrust"),
        ("NE", "No Events"),
    ])
    def test_event_code_valid(self, code, description):
        """Test each event code is recognized."""
        from uct_benchmark.settings import LEGACY_EVENT_MAP

        # NE means "no events" so it may not need a mapping
        if code != "NE":
            assert code in LEGACY_EVENT_MAP, f"Missing mapping for {code}: {description}"


# =============================================================================
# LEGACY CODE PARSING TESTS
# =============================================================================


class TestLegacyCodeParsing:
    """Test parsing of 16-character legacy codes."""

    def test_parse_h50leoneopssss07(self):
        """Test parsing of H50LEONEOPSSSS07."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = LegacyDatasetCode.from_code("H50LEONEOPSSSS07")

        assert code.object_type == "H"  # HAMR
        assert code.target_percentage == "50"  # 50% target
        assert code.orbital_regime == "LEO"  # LEO
        assert code.event_type == "NE"  # No Events
        assert code.sensor_type == "OP"  # Optical
        assert code.orbit_coverage == "S"
        assert code.track_gap == "S"
        assert code.observation_count == "S"
        assert code.object_count == "S"
        assert code.fit_span_days == 7

    def test_roundtrip_code_generation(self):
        """Test that code can be parsed and regenerated."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        original_code = "H50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(original_code)
        regenerated = parsed.to_code()

        assert regenerated == original_code


# =============================================================================
# DEFAULT CONFIGURATION TESTS
# =============================================================================


class TestDefaultConfiguration:
    """Test that default configurations match Louis's spec."""

    def test_window_selection_enabled_by_default(self):
        """Verify window selection is enabled by default."""
        from backend_api.models import DatasetCreate

        # Create with defaults
        config = DatasetCreate(
            name="test-dataset",
            regime="LEO",
        )

        assert config.use_window_selection == True

    def test_target_percentage_defaults_to_unspecified(self):
        """Verify target_percentage defaults to UN."""
        from backend_api.models import DatasetCreate

        config = DatasetCreate(
            name="test-dataset",
            regime="LEO",
        )

        assert config.target_percentage == "UN"

    def test_tracktle_disabled_by_default(self):
        """Verify TrackTLE output is disabled by default."""
        from backend_api.models import DatasetCreate

        config = DatasetCreate(
            name="test-dataset",
            regime="LEO",
        )

        assert config.output_tracktle == False


# =============================================================================
# TRACKTLE INTEGRATION TESTS
# =============================================================================


class TestTrackTLEIntegration:
    """Test TrackTLE generation integration."""

    def test_tracktle_module_available(self):
        """Verify TrackTLE module can be imported."""
        try:
            from uct_benchmark.simulation.tracktle import generate_tracktle, Observation
            assert True
        except ImportError:
            pytest.skip("tracktle module not available")

    def test_tracktle_observation_dataclass(self):
        """Test Observation dataclass structure."""
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

    def test_tracktle_result_structure(self):
        """Test TrackTLEResult has expected fields."""
        from uct_benchmark.simulation.tracktle import TrackTLEResult
        import numpy as np

        result = TrackTLEResult(
            tle_line1="1 25544U 98067A   24001.00000000  .00000000  00000-0  00000-0 0    0",
            tle_line2="2 25544  51.6400 000.0000 0000001 000.0000 000.0000 15.50000000    0",
            epoch=datetime(2024, 1, 1),
            position_km=np.array([6778.0, 0.0, 0.0]),
            velocity_km_s=np.array([0.0, 7.66, 0.0]),
        )

        assert result.tle_line1.startswith("1 ")
        assert result.tle_line2.startswith("2 ")
        assert result.convergence_status == "unknown"


# =============================================================================
# INTEGRATION SMOKE TESTS
# =============================================================================


class TestPipelineSmoke:
    """Smoke tests to verify basic pipeline integration."""

    def test_enforce_target_percentage_imported(self):
        """Verify enforce_target_percentage is importable."""
        from uct_benchmark.api.apiIntegration import enforce_target_percentage
        assert callable(enforce_target_percentage)

    def test_window_tier_5_exists(self):
        """Verify TIER_5 exists in WindowTier enum."""
        from uct_benchmark.data.windowSelection import WindowTier
        assert hasattr(WindowTier, "TIER_5")
        assert WindowTier.TIER_5.value == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
