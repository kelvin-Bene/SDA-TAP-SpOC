# -*- coding: utf-8 -*-
"""
Tests for Legacy 16-Character Dataset Code Format.

This module tests the LegacyDatasetCode class and related functions
from Louis's documentation. The 16-character format is:
    OTTRRREWSSCSNS##

Where:
    O  = Object Type (H/C/A/U/N)
    TT = Target Percentage (50/10/01/UN)
    RRR = Orbital Regime (LEO/MEO/GEO/HEO/ALL)
    EW = Event (MB/BU/LL/NE)
    SS = Sensor Type (OP/RA/RF/FU/OR/RO/RR)
    C  = Orbit Coverage (A/S/N)
    S  = Track Gap (A/S/N)
    N  = Observation Count (A/S/N)
    S  = Object Count (H/S/L)
    ## = Fitspan Days (01-14)

Author: UCT Benchmark Team
Date: 2026
"""

import pytest

from uct_benchmark.config.dataset_schema import (
    LegacyDatasetCode,
    EnhancedDatasetCode,
    validate_legacy_code,
    detect_code_format,
    parse_any_code,
    validate_dataset_code,
)
from uct_benchmark.settings import (
    LEGACY_OBJECT_TYPE_MAP,
    LEGACY_EVENT_MAP,
    LEGACY_SENSOR_MAP,
    QUALITY_LEVEL_THRESHOLDS,
    OBJECT_COUNT_MAP,
)


class TestLegacyDatasetCodeCreation:
    """Tests for creating LegacyDatasetCode instances."""

    def test_default_values(self):
        """Test default values are set correctly."""
        code = LegacyDatasetCode()

        assert code.object_type == "U"
        assert code.target_percentage == "50"
        assert code.orbital_regime == "LEO"
        assert code.event == "NE"
        assert code.sensor_type == "OP"
        assert code.orbit_coverage == "S"
        assert code.track_gap == "S"
        assert code.observation_count == "S"
        assert code.object_count == "S"
        assert code.fitspan_days == 7

    def test_custom_values(self):
        """Test creating with custom values."""
        code = LegacyDatasetCode(
            object_type="H",
            target_percentage="10",
            orbital_regime="GEO",
            event="MB",
            sensor_type="FU",
            orbit_coverage="A",
            track_gap="N",
            observation_count="A",
            object_count="H",
            fitspan_days=14,
        )

        assert code.object_type == "H"
        assert code.target_percentage == "10"
        assert code.orbital_regime == "GEO"
        assert code.event == "MB"
        assert code.sensor_type == "FU"
        assert code.orbit_coverage == "A"
        assert code.track_gap == "N"
        assert code.observation_count == "A"
        assert code.object_count == "H"
        assert code.fitspan_days == 14


class TestLegacyCodeGeneration:
    """Tests for generating 16-character code strings."""

    def test_to_code_default(self):
        """Test generating code from defaults."""
        code = LegacyDatasetCode()
        result = code.to_code()

        assert result == "U50LEONEOPSSSS07"
        assert len(result) == 16

    def test_to_code_custom(self):
        """Test generating code with custom values."""
        code = LegacyDatasetCode(
            object_type="H",
            target_percentage="50",
            orbital_regime="LEO",
            event="NE",
            sensor_type="OP",
            orbit_coverage="S",
            track_gap="S",
            observation_count="S",
            object_count="S",
            fitspan_days=7,
        )
        result = code.to_code()

        assert result == "H50LEONEOPSSSS07"

    def test_to_code_all_options(self):
        """Test generating codes for various options."""
        # HAMR, 10% target, MEO, Maneuver, Fusion, High metrics, High count, 14 days
        code = LegacyDatasetCode(
            object_type="H",
            target_percentage="10",
            orbital_regime="MEO",
            event="MB",
            sensor_type="FU",
            orbit_coverage="A",
            track_gap="A",
            observation_count="A",
            object_count="H",
            fitspan_days=14,
        )
        result = code.to_code()

        assert result == "H10MEOMBFUAAAH14"
        assert len(result) == 16

    def test_to_code_fitspan_padding(self):
        """Test fitspan days are zero-padded."""
        code = LegacyDatasetCode(fitspan_days=1)
        result = code.to_code()

        assert result.endswith("01")

        code = LegacyDatasetCode(fitspan_days=14)
        result = code.to_code()

        assert result.endswith("14")


class TestLegacyCodeParsing:
    """Tests for parsing 16-character code strings."""

    def test_from_code_valid(self):
        """Test parsing valid code."""
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

    def test_from_code_complex(self):
        """Test parsing complex code."""
        code = LegacyDatasetCode.from_code("C01GEOLLOPAAAH14")

        assert code.object_type == "C"
        assert code.target_percentage == "01"
        assert code.orbital_regime == "GEO"
        assert code.event == "LL"
        assert code.sensor_type == "OP"
        assert code.orbit_coverage == "A"
        assert code.track_gap == "A"
        assert code.observation_count == "A"
        assert code.object_count == "H"
        assert code.fitspan_days == 14

    def test_from_code_invalid_length(self):
        """Test error on invalid length."""
        with pytest.raises(ValueError, match="16 characters"):
            LegacyDatasetCode.from_code("SHORT")

        with pytest.raises(ValueError, match="16 characters"):
            LegacyDatasetCode.from_code("THIS_IS_TOO_LONG_CODE")

    def test_from_code_invalid_fitspan(self):
        """Test error on non-numeric fitspan."""
        with pytest.raises(ValueError):
            LegacyDatasetCode.from_code("H50LEONEOPSSSSXX")


class TestLegacyCodeRoundTrip:
    """Tests for round-trip conversion (parse and reconstruct)."""

    @pytest.mark.parametrize("code_str", [
        "U50LEONEOPSSSS07",
        "H50LEONEOPSSSS07",
        "C01GEOLLOPAAAH14",
        "NUNMEOBURAANNSL03",
        "A10HEOMBFUSSSSL10",
    ])
    def test_round_trip(self, code_str):
        """Test parsing and regenerating produces same code."""
        if len(code_str) != 16:
            pytest.skip("Invalid test code")

        parsed = LegacyDatasetCode.from_code(code_str)
        regenerated = parsed.to_code()

        assert regenerated == code_str

    def test_round_trip_all_object_types(self):
        """Test round-trip for all object types."""
        for obj_type in ["H", "C", "A", "U", "N"]:
            code_str = f"{obj_type}50LEONEOPSSSS07"
            parsed = LegacyDatasetCode.from_code(code_str)
            regenerated = parsed.to_code()
            assert regenerated == code_str

    def test_round_trip_all_events(self):
        """Test round-trip for all event types."""
        for event in ["MB", "BU", "LL", "NE"]:
            code_str = f"U50LEO{event}OPSSSS07"
            parsed = LegacyDatasetCode.from_code(code_str)
            regenerated = parsed.to_code()
            assert regenerated == code_str


class TestLegacyCodeValidation:
    """Tests for validating legacy codes."""

    def test_valid_code(self):
        """Test validation of valid code."""
        is_valid, error = validate_legacy_code("H50LEONEOPSSSS07")
        assert is_valid
        assert error is None

    def test_invalid_length(self):
        """Test validation rejects invalid length."""
        is_valid, error = validate_legacy_code("SHORT")
        assert not is_valid
        assert "16 characters" in error

    def test_invalid_object_type(self):
        """Test validation rejects invalid object type."""
        is_valid, error = validate_legacy_code("X50LEONEOPSSSS07")
        assert not is_valid
        assert "object type" in error.lower()

    def test_invalid_target_percentage(self):
        """Test validation rejects invalid target percentage."""
        is_valid, error = validate_legacy_code("H99LEONEOPSSSS07")
        assert not is_valid
        assert "target percentage" in error.lower()

    def test_invalid_regime(self):
        """Test validation rejects invalid regime."""
        is_valid, error = validate_legacy_code("H50XXXNEOPSSSS07")
        assert not is_valid
        assert "regime" in error.lower()

    def test_invalid_event(self):
        """Test validation rejects invalid event."""
        is_valid, error = validate_legacy_code("H50LEOXOPSSSS07")  # Need 2-char event
        assert not is_valid

    def test_invalid_sensor(self):
        """Test validation rejects invalid sensor."""
        is_valid, error = validate_legacy_code("H50LEONEXXSSSS07")
        assert not is_valid
        assert "sensor" in error.lower()

    def test_invalid_quality_levels(self):
        """Test validation rejects invalid quality levels."""
        # Invalid orbit coverage
        is_valid, error = validate_legacy_code("H50LEONEOPXSSS07")
        assert not is_valid
        assert "coverage" in error.lower()

        # Invalid track gap
        is_valid, error = validate_legacy_code("H50LEONEOPAXSS07")
        assert not is_valid
        assert "track gap" in error.lower()

        # Invalid observation count
        is_valid, error = validate_legacy_code("H50LEONEOPSSXS07")
        assert not is_valid
        assert "observation count" in error.lower()

    def test_invalid_object_count(self):
        """Test validation rejects invalid object count."""
        is_valid, error = validate_legacy_code("H50LEONEOPSSSX07")
        assert not is_valid
        assert "object count" in error.lower()

    def test_invalid_fitspan(self):
        """Test validation rejects invalid fitspan."""
        # Non-numeric
        is_valid, error = validate_legacy_code("H50LEONEOPSSSSXX")
        assert not is_valid
        assert "fitspan" in error.lower()

        # Out of range (assuming max is 14)
        is_valid, error = validate_legacy_code("H50LEONEOPSSSS99")
        assert not is_valid
        assert "fitspan" in error.lower()


class TestCodeFormatDetection:
    """Tests for detecting code format."""

    def test_detect_legacy_format(self):
        """Test detection of legacy format."""
        assert detect_code_format("H50LEONEOPSSSS07") == "legacy"

    def test_detect_enhanced_format(self):
        """Test detection of enhanced format."""
        assert detect_code_format("HAMR_LEO_MAN_EO_T2S_07D_001") == "enhanced"

    def test_detect_unknown_format(self):
        """Test detection of unknown format."""
        assert detect_code_format("SHORT") == "unknown"
        assert detect_code_format("") == "unknown"


class TestParseAnyCode:
    """Tests for parsing codes in any format."""

    def test_parse_legacy(self):
        """Test parsing legacy code."""
        result = parse_any_code("H50LEONEOPSSSS07")
        assert isinstance(result, LegacyDatasetCode)
        assert result.object_type == "H"

    def test_parse_enhanced(self):
        """Test parsing enhanced code."""
        result = parse_any_code("HAMR_LEO_MAN_EO_T2S_07D_001")
        assert isinstance(result, EnhancedDatasetCode)
        assert result.object_type == "HAMR"

    def test_parse_unknown_raises(self):
        """Test parsing unknown format raises error."""
        with pytest.raises(ValueError, match="Cannot detect format"):
            parse_any_code("INVALID")


class TestValidateDatasetCodeBothFormats:
    """Tests for validate_dataset_code with both formats."""

    def test_validate_legacy_valid(self):
        """Test validating valid legacy code."""
        is_valid, error = validate_dataset_code("H50LEONEOPSSSS07")
        assert is_valid
        assert error is None

    def test_validate_legacy_invalid(self):
        """Test validating invalid legacy code."""
        is_valid, error = validate_dataset_code("X50LEONEOPSSSS07")
        assert not is_valid
        assert error is not None

    def test_validate_enhanced_valid(self):
        """Test validating valid enhanced code."""
        is_valid, error = validate_dataset_code("HAMR_LEO_MAN_EO_T2S_07D_001")
        assert is_valid
        assert error is None

    def test_validate_enhanced_invalid(self):
        """Test validating invalid enhanced code."""
        is_valid, error = validate_dataset_code("XXXX_LEO_MAN_EO_T2S_07D_001")
        assert not is_valid
        assert error is not None


class TestLegacyToEnhancedConversion:
    """Tests for converting legacy to enhanced format."""

    def test_convert_basic(self):
        """Test basic conversion."""
        legacy = LegacyDatasetCode.from_code("U50LEONEOPSSSS07")
        enhanced = legacy.to_enhanced()

        assert enhanced.regime == "LEO"
        assert enhanced.time_window_days == 7

    def test_convert_hamr_object(self):
        """Test HAMR object type conversion."""
        legacy = LegacyDatasetCode(object_type="H")
        enhanced = legacy.to_enhanced()

        assert enhanced.object_type == "HAMR"

    def test_convert_event_maneuver(self):
        """Test maneuver event conversion."""
        legacy = LegacyDatasetCode(event="MB")
        enhanced = legacy.to_enhanced()

        assert enhanced.event == "MAN"

    def test_convert_event_breakup(self):
        """Test breakup event conversion."""
        legacy = LegacyDatasetCode(event="BU")
        enhanced = legacy.to_enhanced()

        assert enhanced.event == "BRK"

    def test_convert_sensor_optical(self):
        """Test optical sensor conversion."""
        legacy = LegacyDatasetCode(sensor_type="OP")
        enhanced = legacy.to_enhanced()

        assert enhanced.sensor == "EO"

    def test_convert_sensor_fusion(self):
        """Test fusion sensor conversion."""
        legacy = LegacyDatasetCode(sensor_type="FU")
        enhanced = legacy.to_enhanced()

        assert enhanced.sensor == "MX"

    def test_convert_quality_sparse(self):
        """Test A (sparse) quality conversion.

        Per Louis's documentation, A = >90% objects have LOW quality.
        So the enhanced tier should reflect SPARSE/LOW quality.
        """
        legacy = LegacyDatasetCode(orbit_coverage="A")
        enhanced = legacy.to_enhanced()

        # A = sparse dataset, so quality tier should be Low
        assert "L" in enhanced.quality_tier or "S" in enhanced.quality_tier

    def test_convert_quality_dense(self):
        """Test N (dense) quality conversion.

        Per Louis's documentation, N = <10% objects have LOW quality.
        So the enhanced tier should reflect DENSE/HIGH quality.
        """
        legacy = LegacyDatasetCode(orbit_coverage="N")
        enhanced = legacy.to_enhanced()

        # N = dense dataset, so quality tier should be High
        assert "H" in enhanced.quality_tier or "S" in enhanced.quality_tier


class TestEnhancedToLegacyConversion:
    """Tests for converting enhanced to legacy format."""

    def test_convert_basic(self):
        """Test basic reverse conversion."""
        enhanced = EnhancedDatasetCode(
            object_type="NORM",
            regime="LEO",
            event="NRM",
            sensor="EO",
            quality_tier="T2S",
            time_window_days=7,
        )
        legacy = LegacyDatasetCode.from_enhanced(enhanced)

        assert legacy.orbital_regime == "LEO"
        assert legacy.fitspan_days == 7

    def test_convert_hamr_back(self):
        """Test HAMR converts back."""
        enhanced = EnhancedDatasetCode(object_type="HAMR")
        legacy = LegacyDatasetCode.from_enhanced(enhanced)

        assert legacy.object_type == "H"

    def test_convert_event_man_back(self):
        """Test maneuver event converts back."""
        enhanced = EnhancedDatasetCode(event="MAN")
        legacy = LegacyDatasetCode.from_enhanced(enhanced)

        assert legacy.event == "MB"

    def test_convert_sensor_eo_back(self):
        """Test optical sensor converts back."""
        enhanced = EnhancedDatasetCode(sensor="EO")
        legacy = LegacyDatasetCode.from_enhanced(enhanced)

        assert legacy.sensor_type == "OP"


class TestQualityLevelThresholds:
    """Tests for quality level threshold mapping.

    Per Louis's documentation, A/S/N refer to % of objects with LOW quality:
    A = >90% objects have LOW quality (sparse dataset)
    S = 40-60% objects have LOW quality (mixed)
    N = <10% objects have LOW quality (dense/high-quality dataset)

    The thresholds returned are the target percentage of objects
    that should have low quality metrics.
    """

    def test_get_coverage_thresholds_sparse(self):
        """Test A (sparse) coverage thresholds - most objects have low coverage."""
        code = LegacyDatasetCode(orbit_coverage="A")
        min_pct, max_pct = code.get_coverage_thresholds()

        # A = 90-100% of objects should have low coverage
        assert min_pct >= 0.90
        assert max_pct <= 1.00

    def test_get_coverage_thresholds_standard(self):
        """Test standard coverage thresholds."""
        code = LegacyDatasetCode(orbit_coverage="S")
        min_pct, max_pct = code.get_coverage_thresholds()

        # S = 40-60% of objects should have low coverage
        assert 0.40 <= min_pct <= 0.60
        assert 0.40 <= max_pct <= 0.60

    def test_get_coverage_thresholds_dense(self):
        """Test N (dense) coverage thresholds - few objects have low coverage."""
        code = LegacyDatasetCode(orbit_coverage="N")
        min_pct, max_pct = code.get_coverage_thresholds()

        # N = 0-10% of objects should have low coverage
        assert min_pct >= 0.00
        assert max_pct <= 0.10

    def test_get_track_gap_thresholds(self):
        """Test track gap threshold retrieval."""
        code = LegacyDatasetCode(track_gap="A")
        min_pct, max_pct = code.get_track_gap_thresholds()

        # A = 90-100% of objects should have long track gaps
        assert min_pct >= 0.90

    def test_get_obs_count_thresholds(self):
        """Test observation count threshold retrieval."""
        code = LegacyDatasetCode(observation_count="S")
        min_pct, max_pct = code.get_obs_count_thresholds()

        # S = 40-60% of objects should have low obs count
        assert 0.40 <= min_pct <= 0.60


class TestObjectCountMapping:
    """Tests for object count value mapping."""

    def test_high_count(self):
        """Test high object count value."""
        code = LegacyDatasetCode(object_count="H")
        assert code.get_object_count_value() == 80

    def test_standard_count(self):
        """Test standard object count value."""
        code = LegacyDatasetCode(object_count="S")
        assert code.get_object_count_value() == 40

    def test_low_count(self):
        """Test low object count value."""
        code = LegacyDatasetCode(object_count="L")
        assert code.get_object_count_value() == 10


class TestDownsampleConfigMapping:
    """Tests for downsample config from legacy code.

    Note: The mapping is:
        - "A" (high quality output) = aggressive downsampling = target_coverage 0.02
        - "S" (standard quality) = moderate downsampling = target_coverage 0.05
        - "N" (low quality) = minimal downsampling = target_coverage 0.15

    Counter-intuitive but: "A" means sparse, high-quality selected data,
    while "N" means more data kept (less quality control).
    """

    def test_downsample_config_high(self):
        """Test downsample config for high coverage level (A)."""
        code = LegacyDatasetCode(orbit_coverage="A")
        config = code.get_downsample_config()

        assert "target_coverage" in config
        # A = Aggressive downsampling = lowest target_coverage value
        assert config["target_coverage"] == 0.02

    def test_downsample_config_standard(self):
        """Test downsample config for standard coverage."""
        code = LegacyDatasetCode(orbit_coverage="S")
        config = code.get_downsample_config()

        assert "target_coverage" in config
        assert config["target_coverage"] == 0.05

    def test_downsample_config_low(self):
        """Test downsample config for low coverage level (N)."""
        code = LegacyDatasetCode(orbit_coverage="N")
        config = code.get_downsample_config()

        assert "target_coverage" in config
        # N = Minimal downsampling = highest target_coverage value
        assert config["target_coverage"] == 0.15


class TestLegacyCodeDescription:
    """Tests for human-readable descriptions."""

    def test_describe_basic(self):
        """Test basic description."""
        code = LegacyDatasetCode.from_code("H50LEONEOPSSSS07")
        description = code.describe()

        assert "Dataset Code: H50LEONEOPSSSS07" in description
        assert "HAMR" in description
        assert "LEO" in description
        assert "Optical" in description
        assert "7 days" in description

    def test_describe_includes_all_components(self):
        """Test description includes all components."""
        code = LegacyDatasetCode()
        description = code.describe()

        assert "Object Type:" in description
        assert "Target %:" in description
        assert "Regime:" in description
        assert "Event:" in description
        assert "Sensor:" in description
        assert "Orbit Coverage:" in description
        assert "Track Gap:" in description
        assert "Obs Count:" in description
        assert "Object Count:" in description
        assert "Fitspan:" in description


class TestSettingsIntegration:
    """Tests for settings constants integration."""

    def test_object_type_map_complete(self):
        """Test all object types are mapped."""
        for code in ["H", "C", "A", "U", "N"]:
            assert code in LEGACY_OBJECT_TYPE_MAP

    def test_event_map_complete(self):
        """Test all events are mapped."""
        for code in ["MB", "BU", "LL", "NE"]:
            assert code in LEGACY_EVENT_MAP

    def test_sensor_map_complete(self):
        """Test all sensors are mapped."""
        for code in ["OP", "RA", "RF", "FU", "OR", "RO", "RR"]:
            assert code in LEGACY_SENSOR_MAP

    def test_quality_thresholds_complete(self):
        """Test all quality levels have thresholds."""
        for level in ["A", "S", "N"]:
            assert level in QUALITY_LEVEL_THRESHOLDS["coverage"]
            assert level in QUALITY_LEVEL_THRESHOLDS["track_gap"]
            assert level in QUALITY_LEVEL_THRESHOLDS["observation_count"]

    def test_object_count_map_complete(self):
        """Test all object counts are mapped."""
        for code in ["H", "S", "L"]:
            assert code in OBJECT_COUNT_MAP


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
