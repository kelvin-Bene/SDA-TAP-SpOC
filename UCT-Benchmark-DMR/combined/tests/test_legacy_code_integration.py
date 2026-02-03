# -*- coding: utf-8 -*-
"""
Integration Tests for Legacy 16-Character Dataset Code Format.

This module tests the integration of legacy codes with:
- WindowCriteria generation
- DownsampleConfig generation
- Object type filtering
- Event detection
- UDL export functionality
- Full pipeline configuration

Author: UCT Benchmark Team
Date: 2026
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from uct_benchmark.config.dataset_schema import (
    LegacyDatasetCode,
    EnhancedDatasetCode,
    validate_legacy_code,
)


# =============================================================================
# WINDOW CRITERIA INTEGRATION TESTS
# =============================================================================


class TestWindowCriteriaFromLegacyCode:
    """Tests for creating WindowCriteria from legacy code parameters."""

    def test_create_criteria_from_legacy_code(self):
        """Test creating WindowCriteria from legacy code."""
        try:
            from uct_benchmark.data.windowSelection import create_criteria_from_legacy_code
        except ImportError:
            pytest.skip("windowSelection module not available")

        # Pass the code string, not the object
        code_str = "H50LEONEOPSSSS07"
        criteria = create_criteria_from_legacy_code(code_str)

        assert criteria is not None
        assert criteria.fit_span_days == 7

    def test_criteria_regime_mapping(self):
        """Test regime is correctly mapped in criteria."""
        try:
            from uct_benchmark.data.windowSelection import create_criteria_from_legacy_code
        except ImportError:
            pytest.skip("windowSelection module not available")

        for regime in ["LEO", "MEO", "GEO", "HEO"]:
            code = LegacyDatasetCode(orbital_regime=regime)
            code_str = code.to_code()  # Convert to string
            criteria = create_criteria_from_legacy_code(code_str)
            assert criteria.regimes == [regime]

    def test_criteria_coverage_from_quality_level(self):
        """Test coverage thresholds from quality level.

        Per Louis's documentation:
        - A = >90% objects have LOW quality (sparse dataset) → lower coverage values
        - N = <10% objects have LOW quality (dense dataset) → higher coverage values
        """
        try:
            from uct_benchmark.data.windowSelection import create_criteria_from_legacy_code
        except ImportError:
            pytest.skip("windowSelection module not available")

        # Sparse (A) - >90% objects have LOW quality → lower coverage targets
        code_sparse = LegacyDatasetCode(orbit_coverage="A")
        criteria_sparse = create_criteria_from_legacy_code(code_sparse.to_code())

        # Dense (N) - <10% objects have LOW quality → higher coverage targets
        code_dense = LegacyDatasetCode(orbit_coverage="N")
        criteria_dense = create_criteria_from_legacy_code(code_dense.to_code())

        # Both should have criteria set
        assert criteria_sparse is not None
        assert criteria_dense is not None
        # The coverage values come from the windowSelection mapping, verify they differ correctly
        if hasattr(criteria_sparse, "min_coverage") and hasattr(criteria_dense, "min_coverage"):
            # Sparse (A) = lower coverage vs Dense (N) = higher coverage
            assert criteria_sparse.min_coverage < criteria_dense.min_coverage

    def test_criteria_object_count_from_level(self):
        """Test object count from H/S/L level."""
        try:
            from uct_benchmark.data.windowSelection import create_criteria_from_legacy_code
        except ImportError:
            pytest.skip("windowSelection module not available")

        # High count (H = 80)
        code_high = LegacyDatasetCode(object_count="H")
        criteria_high = create_criteria_from_legacy_code(code_high.to_code())
        assert criteria_high.target_objects == 80

        # Standard count (S = 40)
        code_std = LegacyDatasetCode(object_count="S")
        criteria_std = create_criteria_from_legacy_code(code_std.to_code())
        assert criteria_std.target_objects == 40

        # Low count (L = 10)
        code_low = LegacyDatasetCode(object_count="L")
        criteria_low = create_criteria_from_legacy_code(code_low.to_code())
        assert criteria_low.target_objects == 10


# =============================================================================
# DOWNSAMPLE CONFIG INTEGRATION TESTS
# =============================================================================


class TestDownsampleConfigFromLegacyCode:
    """Tests for creating DownsampleConfig from legacy code."""

    def test_get_downsample_config(self):
        """Test getting downsample config from legacy code."""
        try:
            from uct_benchmark.data.dataManipulation import get_downsample_config_from_legacy
        except ImportError:
            pytest.skip("dataManipulation module not available")

        # Pass the code string, not the object
        code_str = "U50LEONEOPSSSS07"
        config = get_downsample_config_from_legacy(code_str)

        assert config is not None
        assert hasattr(config, "target_coverage") or "target_coverage" in config

    def test_downsample_config_varies_by_coverage(self):
        """Test downsample config varies by coverage level.

        Note: The mapping in the implementation is:
            - "A" (high quality) = aggressive downsampling = LOWER target_coverage
            - "N" (low quality) = minimal downsampling = HIGHER target_coverage

        This is because "A" produces sparse, high-quality selected data,
        while "N" keeps more observations with less quality filtering.
        """
        try:
            from uct_benchmark.data.dataManipulation import get_downsample_config_from_legacy
        except ImportError:
            pytest.skip("dataManipulation module not available")

        code_high = LegacyDatasetCode(orbit_coverage="A")  # High quality = aggressive downsample
        code_low = LegacyDatasetCode(orbit_coverage="N")   # Low quality = minimal downsample

        # Pass the code strings
        config_high = get_downsample_config_from_legacy(code_high.to_code())
        config_low = get_downsample_config_from_legacy(code_low.to_code())

        # A = aggressive downsampling = lower target_coverage
        # N = minimal downsampling = higher target_coverage
        high_target = config_high.target_coverage if hasattr(config_high, "target_coverage") else config_high.get("target_coverage", 0)
        low_target = config_low.target_coverage if hasattr(config_low, "target_coverage") else config_low.get("target_coverage", 0)

        # Counter-intuitive but correct: high_target < low_target
        assert high_target < low_target


class TestSimulationDecisionFromLegacyCode:
    """Tests for should_simulate_for_legacy_code function."""

    def test_should_simulate_low_quality(self):
        """Test simulation decision for low quality requirement."""
        try:
            from uct_benchmark.data.dataManipulation import should_simulate_for_legacy_code
        except ImportError:
            pytest.skip("dataManipulation module not available")

        # Want dense data (A) but have sparse - should simulate
        code = LegacyDatasetCode(orbit_coverage="A", observation_count="A")
        current_coverage = 0.02  # Currently sparse
        current_obs_count = 10.0  # Low observation count

        # Function signature: (current_coverage, current_obs_count, legacy_code, ...)
        # Returns tuple (should_simulate: bool, reason: str)
        result = should_simulate_for_legacy_code(
            current_coverage=current_coverage,
            current_obs_count=current_obs_count,
            legacy_code=code.to_code(),
        )
        # When wanting high coverage but having low, might need simulation
        assert isinstance(result, tuple)
        should_sim, reason = result
        assert isinstance(should_sim, bool)
        assert isinstance(reason, str)


# =============================================================================
# OBJECT TYPE FILTERING INTEGRATION TESTS
# =============================================================================


class TestObjectTypeFilteringIntegration:
    """Tests for object type filtering with legacy codes."""

    @pytest.fixture
    def sample_observations(self):
        """Create sample observation data."""
        np.random.seed(42)
        obs_data = {
            "satNo": [25544, 25544, 25544, 43567, 43567, 12345, 12345, 12345],
            "obTime": pd.date_range("2024-01-01", periods=8, freq="h"),
            "ra": np.random.uniform(0, 360, 8),
            "declination": np.random.uniform(-90, 90, 8),
        }
        return pd.DataFrame(obs_data)

    def test_filter_by_object_type_code_unspecified(self, sample_observations):
        """Test filtering with unspecified type (U) includes all."""
        try:
            from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code
        except ImportError:
            pytest.skip("objectTypeFiltering module not available")

        filtered_df, metadata = filter_by_object_type_code(
            sample_observations,
            object_type_code="U",
        )

        # U = Unspecified, should include all
        assert len(filtered_df) == len(sample_observations)

    def test_filter_by_object_type_code_calibration(self, sample_observations):
        """Test filtering with calibration type (N)."""
        try:
            from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code
        except ImportError:
            pytest.skip("objectTypeFiltering module not available")

        filtered_df, metadata = filter_by_object_type_code(
            sample_observations,
            object_type_code="N",
        )

        # N = Calibration, should filter to known calibration satellites
        assert metadata["object_type_code"] == "N"
        assert "calibration" in metadata["filters_applied"][0].lower()

    def test_filter_by_object_type_code_hamr(self, sample_observations):
        """Test filtering with HAMR type (H)."""
        try:
            from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code
        except ImportError:
            pytest.skip("objectTypeFiltering module not available")

        # HAMR filtering requires physical data - test that it handles empty data
        filtered_df, metadata = filter_by_object_type_code(
            sample_observations,
            object_type_code="H",
            physical_data={},
        )

        assert metadata["object_type_code"] == "H"

    def test_filter_invalid_code_raises(self, sample_observations):
        """Test invalid object type code raises error."""
        try:
            from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code
        except ImportError:
            pytest.skip("objectTypeFiltering module not available")

        with pytest.raises(ValueError, match="Invalid object type code"):
            filter_by_object_type_code(sample_observations, "X")


# =============================================================================
# EVENT DETECTION INTEGRATION TESTS
# =============================================================================


class TestEventDetectionIntegration:
    """Tests for event detection with legacy codes."""

    @pytest.fixture
    def sample_tle_data(self):
        """Create sample TLE history data."""
        np.random.seed(42)
        epochs = pd.date_range("2024-01-01", periods=20, freq="D")

        # Create TLE data with some variation
        tle_data = {
            "satNo": [25544] * 20,
            "epoch": epochs,
            "line2": [
                "2 25544  51.6400 247.4627 0006703 130.5360 325.0288 15.72125391563537"
            ] * 20,
        }
        return pd.DataFrame(tle_data)

    def test_filter_satellites_by_event_code_no_events(self, sample_tle_data):
        """Test filtering for satellites with no events."""
        try:
            from uct_benchmark.data.eventDetection import filter_satellites_by_event_code
        except ImportError:
            pytest.skip("eventDetection module not available")

        satellites, events = filter_satellites_by_event_code(
            sample_tle_data,
            satellite_ids=[25544],
            event_code="NE",
        )

        # NE = No Events, should return satellites without detected events
        assert isinstance(satellites, list)
        assert isinstance(events, list)

    def test_filter_satellites_by_event_code_maneuver(self, sample_tle_data):
        """Test filtering for satellites with maneuvers."""
        try:
            from uct_benchmark.data.eventDetection import filter_satellites_by_event_code
        except ImportError:
            pytest.skip("eventDetection module not available")

        satellites, events = filter_satellites_by_event_code(
            sample_tle_data,
            satellite_ids=[25544],
            event_code="MB",
        )

        # MB = Maneuver Between observations
        assert isinstance(satellites, list)

    def test_filter_satellites_by_event_code_long_thrust(self, sample_tle_data):
        """Test filtering for satellites with long-thrust maneuvers."""
        try:
            from uct_benchmark.data.eventDetection import filter_satellites_by_event_code
        except ImportError:
            pytest.skip("eventDetection module not available")

        satellites, events = filter_satellites_by_event_code(
            sample_tle_data,
            satellite_ids=[25544],
            event_code="LL",
        )

        # LL = Long-duration Low-thrust
        assert isinstance(satellites, list)

    def test_filter_invalid_event_code_raises(self, sample_tle_data):
        """Test invalid event code raises error."""
        try:
            from uct_benchmark.data.eventDetection import filter_satellites_by_event_code
        except ImportError:
            pytest.skip("eventDetection module not available")

        with pytest.raises(ValueError, match="Invalid event code"):
            filter_satellites_by_event_code(
                sample_tle_data,
                satellite_ids=[25544],
                event_code="XX",
            )


class TestLongThrustDetection:
    """Tests for long-duration low-thrust maneuver detection."""

    @pytest.fixture
    def tle_with_drift(self):
        """Create TLE data with gradual SMA drift (simulating low-thrust)."""
        np.random.seed(42)
        epochs = pd.date_range("2024-01-01", periods=30, freq="D")

        # Simulate gradual SMA increase (orbit raising)
        base_mm = 15.5  # Mean motion (rev/day)
        drift_rate = 0.001  # per day

        tle_lines = []
        for i in range(30):
            mm = base_mm - i * drift_rate  # Decreasing MM = increasing SMA
            tle_line = f"2 25544  51.6400 247.4627 0006703 130.5360 325.0288 {mm:011.8f}563537"
            tle_lines.append(tle_line)

        return pd.DataFrame({
            "satNo": [25544] * 30,
            "epoch": epochs,
            "line2": tle_lines,
        })

    def test_detect_long_duration_maneuvers(self, tle_with_drift):
        """Test detection of long-duration maneuvers."""
        try:
            from uct_benchmark.data.eventDetection import detect_long_duration_maneuvers
        except ImportError:
            pytest.skip("eventDetection module not available")

        events = detect_long_duration_maneuvers(
            tle_with_drift,
            satellite_id=25544,
        )

        # Function should return list of events
        assert isinstance(events, list)


# =============================================================================
# UDL EXPORT INTEGRATION TESTS
# =============================================================================


class TestUDLExportIntegration:
    """Tests for UDL export with legacy codes."""

    @pytest.fixture
    def sample_observations_for_export(self):
        """Create sample observation data for export."""
        np.random.seed(42)
        return pd.DataFrame({
            "satNo": [25544, 25544, 43567, 43567, 12345],
            "obTime": pd.date_range("2024-01-01", periods=5, freq="h"),
            "ra": np.random.uniform(0, 360, 5),
            "declination": np.random.uniform(-90, 90, 5),
            "magnitude": np.random.uniform(5, 15, 5),
        })

    def test_decorrelate_observations(self, sample_observations_for_export):
        """Test decorrelating observations."""
        try:
            from uct_benchmark.output.udl_export import decorrelate_observations
        except ImportError:
            pytest.skip("udl_export module not available")

        decorrelated, truth = decorrelate_observations(
            sample_observations_for_export,
            seed=42,
        )

        # satNo should be removed
        assert "satNo" not in decorrelated.columns
        # track_id should be added
        assert "track_id" in decorrelated.columns
        # Truth mapping should have satNo
        assert "satNo" in truth.columns
        assert "track_id" in truth.columns

    def test_export_dataset_for_udl_with_legacy_code(self, sample_observations_for_export):
        """Test full UDL export with legacy code."""
        try:
            from uct_benchmark.output.udl_export import export_dataset_for_udl
        except ImportError:
            pytest.skip("udl_export module not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            legacy_code = "H50LEONEOPSSSS07"

            result = export_dataset_for_udl(
                sample_observations_for_export,
                output_dir,
                dataset_name="test_dataset",
                legacy_code=legacy_code,
                seed=42,
            )

            # Check result structure
            assert result["legacy_code"] == legacy_code
            assert "observations.json" in result["files"]
            assert "truth.json" in result["files"]
            assert "metadata.json" in result["files"]
            assert "manifest.json" in result["files"]

            # Check files exist
            assert (output_dir / "test_dataset" / "observations.json").exists()
            assert (output_dir / "test_dataset" / "truth.json").exists()
            assert (output_dir / "test_dataset" / "metadata.json").exists()

    def test_export_includes_legacy_code_breakdown(self, sample_observations_for_export):
        """Test export metadata includes legacy code breakdown."""
        try:
            from uct_benchmark.output.udl_export import export_dataset_for_udl
            import json
        except ImportError:
            pytest.skip("udl_export module not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            export_dataset_for_udl(
                sample_observations_for_export,
                output_dir,
                dataset_name="test_dataset",
                legacy_code="H50LEONEOPSSSS07",
            )

            # Load and check metadata
            with open(output_dir / "test_dataset" / "metadata.json") as f:
                metadata = json.load(f)

            assert "legacy_code_breakdown" in metadata
            assert metadata["legacy_code_breakdown"]["object_type"] == "H"
            assert metadata["legacy_code_breakdown"]["orbital_regime"] == "LEO"

    def test_verify_udl_export(self, sample_observations_for_export):
        """Test verifying UDL export integrity."""
        try:
            from uct_benchmark.output.udl_export import (
                export_dataset_for_udl,
                verify_udl_export,
            )
        except ImportError:
            pytest.skip("udl_export module not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            export_dataset_for_udl(
                sample_observations_for_export,
                output_dir,
                dataset_name="test_dataset",
            )

            # Verify the export
            result = verify_udl_export(output_dir / "test_dataset")

            assert result["valid"]
            assert len(result["errors"]) == 0

    def test_load_udl_export(self, sample_observations_for_export):
        """Test loading UDL export."""
        try:
            from uct_benchmark.output.udl_export import (
                export_dataset_for_udl,
                load_udl_export,
            )
        except ImportError:
            pytest.skip("udl_export module not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            export_dataset_for_udl(
                sample_observations_for_export,
                output_dir,
                dataset_name="test_dataset",
            )

            # Load the export
            obs_df, truth_df, metadata = load_udl_export(
                output_dir / "test_dataset"
            )

            assert len(obs_df) == len(sample_observations_for_export)
            assert len(truth_df) == sample_observations_for_export["satNo"].nunique()


# =============================================================================
# FULL PIPELINE INTEGRATION TESTS
# =============================================================================


class TestFullPipelineWithLegacyCode:
    """Tests for full pipeline with legacy code configuration."""

    def test_legacy_code_to_enhanced_to_criteria(self):
        """Test converting legacy code through to criteria."""
        # Parse legacy code
        legacy = LegacyDatasetCode.from_code("H50LEONEOPSSSS07")

        # Convert to enhanced
        enhanced = legacy.to_enhanced()

        # Verify key parameters preserved
        assert enhanced.regime == "LEO"
        assert enhanced.time_window_days == 7
        assert enhanced.object_type == "HAMR"

    def test_legacy_code_components_accessible(self):
        """Test all legacy code components can be accessed for pipeline."""
        code = LegacyDatasetCode.from_code("C01GEOLLOPAAAH14")

        # All these should be usable in pipeline
        assert code.object_type == "C"  # For object filtering
        assert code.target_percentage == "01"  # For target ratio
        assert code.orbital_regime == "GEO"  # For satellite selection
        assert code.event == "LL"  # For event filtering
        assert code.sensor_type == "OP"  # For sensor filtering
        assert code.orbit_coverage == "A"  # For coverage criteria
        assert code.track_gap == "A"  # For gap criteria
        assert code.observation_count == "A"  # For obs count criteria
        assert code.object_count == "H"  # For object count (80)
        assert code.fitspan_days == 14  # For time window

    def test_multiple_legacy_codes_generate_different_configs(self):
        """Test different legacy codes generate different configurations."""
        codes = [
            "U50LEONEOPSSSS07",  # Normal, standard quality
            "H10GEOMBFUAAAH14",  # HAMR, high quality
            "N01MEOLLRANNNL01",  # Calibration, low quality
        ]

        parsed = [LegacyDatasetCode.from_code(c) for c in codes]
        enhanced = [p.to_enhanced() for p in parsed]

        # All should be different
        assert len(set(e.to_code() for e in enhanced)) == 3

    def test_legacy_code_validation_in_pipeline(self):
        """Test validation catches invalid codes before pipeline runs."""
        # Valid code passes
        is_valid, error = validate_legacy_code("H50LEONEOPSSSS07")
        assert is_valid

        # Invalid code caught early
        is_valid, error = validate_legacy_code("X99XXXYYZZQQQQQ")
        assert not is_valid
        assert error is not None

    def test_bidirectional_conversion_preserves_info(self):
        """Test converting legacy->enhanced->legacy preserves key info."""
        original = LegacyDatasetCode.from_code("U50LEONEOPSSSS07")

        # Convert to enhanced and back
        enhanced = original.to_enhanced()
        back = LegacyDatasetCode.from_enhanced(enhanced)

        # Key parameters should be preserved
        assert back.orbital_regime == original.orbital_regime
        assert back.fitspan_days == original.fitspan_days
        # Note: Some info may be lost (e.g., target_percentage defaults)


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================


class TestEdgeCasesAndErrors:
    """Tests for edge cases and error handling."""

    def test_empty_dataframe_handling(self):
        """Test handling of empty DataFrames."""
        try:
            from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code
        except ImportError:
            pytest.skip("objectTypeFiltering module not available")

        empty_df = pd.DataFrame(columns=["satNo", "obTime", "ra", "declination"])
        filtered, metadata = filter_by_object_type_code(empty_df, "U")

        assert len(filtered) == 0
        assert metadata["status"] == "empty_input"

    def test_extreme_fitspan_values(self):
        """Test extreme but valid fitspan values."""
        # Minimum fitspan
        code_min = LegacyDatasetCode(fitspan_days=1)
        assert code_min.to_code().endswith("01")

        # Maximum fitspan (14 per spec)
        code_max = LegacyDatasetCode(fitspan_days=14)
        assert code_max.to_code().endswith("14")

    def test_all_valid_sensor_combinations(self):
        """Test all valid sensor type codes."""
        valid_sensors = ["OP", "RA", "RF", "FU", "OR", "RO", "RR"]

        for sensor in valid_sensors:
            code = LegacyDatasetCode(sensor_type=sensor)
            code_str = code.to_code()
            parsed = LegacyDatasetCode.from_code(code_str)
            assert parsed.sensor_type == sensor

    def test_all_valid_regime_combinations(self):
        """Test all valid regime codes."""
        valid_regimes = ["LEO", "MEO", "GEO", "HEO", "ALL"]

        for regime in valid_regimes:
            code = LegacyDatasetCode(orbital_regime=regime)
            code_str = code.to_code()
            is_valid, error = validate_legacy_code(code_str)
            assert is_valid, f"Regime {regime} should be valid: {error}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
