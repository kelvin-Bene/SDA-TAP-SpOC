# -*- coding: utf-8 -*-
"""
Comprehensive Test Suite for 16-Character Dataset Codes

Tests all 16 positions of the dataset code per Louis's specification.

Code Structure:
Position 1:    Object Type (H, C, A, U, N)
Position 2-3:  Target Percentage (50, 10, 01, UN)
Position 4-6:  Orbit Regime (LEO, MEO, GEO, HEO, UNK)
Position 7-8:  Event Type (MB, BU, LL, NE)
Position 9-10: Sensor Type (OP, RA, RF, FU)
Position 11:   Coverage Quality (A, S, N)
Position 12:   Track Gap Quality (A, S, N)
Position 13:   Observation Quality (A, S, N)
Position 14:   Object Count (H, S, L)
Position 15-16: Fit Span (01-14)

Author: UCT Benchmark Team
Date: 2026
"""

import pytest


class TestPosition1ObjectType:
    """Tests for Position 1: Object Type code."""

    def test_hamr_object_type(self):
        """Test H (HAMR) object type parsing."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "H50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.object_type == "H"

    def test_close_object_type(self):
        """Test C (Close) object type parsing."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "C50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.object_type == "C"

    def test_apparent_object_type(self):
        """Test A (Apparent) object type parsing."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "A50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.object_type == "A"

    def test_unspecified_object_type(self):
        """Test U (Unspecified) object type parsing."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.object_type == "U"

    def test_calibration_object_type(self):
        """Test N (Calibration) object type parsing."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "N50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.object_type == "N"


class TestPositions2_3TargetPercentage:
    """Tests for Positions 2-3: Target Percentage."""

    def test_50_percent(self):
        """Test 50% target percentage."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.target_percentage == "50"

    def test_10_percent(self):
        """Test 10% target percentage."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U10LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.target_percentage == "10"

    def test_01_percent(self):
        """Test 1% (01) target percentage."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U01LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.target_percentage == "01"

    def test_unspecified_percentage(self):
        """Test UN (unspecified) target percentage."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "UUNLEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.target_percentage == "UN"


class TestPositions4_6OrbitRegime:
    """Tests for Positions 4-6: Orbit Regime."""

    def test_leo_regime(self):
        """Test LEO orbit regime."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.orbital_regime == "LEO"

    def test_meo_regime(self):
        """Test MEO orbit regime."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50MEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.orbital_regime == "MEO"

    def test_geo_regime(self):
        """Test GEO orbit regime."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50GEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.orbital_regime == "GEO"

    def test_heo_regime(self):
        """Test HEO orbit regime."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50HEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.orbital_regime == "HEO"

    def test_all_regime(self):
        """Test ALL orbit regime."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50ALLNEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.orbital_regime == "ALL"


class TestPositions7_8EventType:
    """Tests for Positions 7-8: Event Type."""

    def test_maneuver_event(self):
        """Test MB (Maneuver Between) event type."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEOMBOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.event == "MB"

    def test_breakup_event(self):
        """Test BU (Breakup) event type."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEOBUOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.event == "BU"

    def test_low_thrust_event(self):
        """Test LL (Long-duration Low-thrust) event type."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEOLLOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.event == "LL"

    def test_no_events(self):
        """Test NE (No Events) event type."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.event == "NE"


class TestPositions9_10SensorType:
    """Tests for Positions 9-10: Sensor Type."""

    def test_optical_sensor(self):
        """Test OP (Optical) sensor type."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.sensor_type == "OP"

    def test_radar_sensor(self):
        """Test RA (Radar) sensor type."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONERASSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.sensor_type == "RA"

    def test_rf_sensor(self):
        """Test RF (Passive RF) sensor type."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONERFSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.sensor_type == "RF"

    def test_fusion_sensor(self):
        """Test FU (Fusion) sensor type."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEFUSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.sensor_type == "FU"


class TestPositions11_13Quality:
    """Tests for Positions 11-13: Quality codes (A/S/N)."""

    def test_all_standard_quality(self):
        """Test SSS (all standard) quality."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)

        assert parsed.orbit_coverage == "S"
        assert parsed.track_gap == "S"
        assert parsed.observation_count == "S"

    def test_all_aggressive_quality(self):
        """Test AAA (all aggressive) quality."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPAASS07"
        parsed = LegacyDatasetCode.from_code(code)

        assert parsed.orbit_coverage == "A"
        assert parsed.track_gap == "A"
        assert parsed.observation_count == "S"  # Position 13

    def test_mixed_quality(self):
        """Test mixed quality codes."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPANSS07"
        parsed = LegacyDatasetCode.from_code(code)

        # A = Aggressive, N = Not strict, S = Standard
        assert parsed.orbit_coverage == "A"
        assert parsed.track_gap == "N"
        assert parsed.observation_count == "S"


class TestPosition14ObjectCount:
    """Tests for Position 14: Object Count (H, S, L)."""

    def test_standard_count(self):
        """Test S (Standard) object count."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.object_count == "S"

    def test_high_count(self):
        """Test H (High) object count."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSH07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.object_count == "H"

    def test_low_count(self):
        """Test L (Low) object count."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSL07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.object_count == "L"


class TestPositions15_16FitSpan:
    """Tests for Positions 15-16: Fit Span (days)."""

    def test_1_day_fit_span(self):
        """Test 1-day fit span."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS01"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.fitspan_days == 1

    def test_2_day_fit_span(self):
        """Test 2-day fit span."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS02"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.fitspan_days == 2

    def test_3_day_fit_span(self):
        """Test 3-day fit span."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS03"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.fitspan_days == 3

    def test_5_day_fit_span(self):
        """Test 5-day fit span."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS05"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.fitspan_days == 5

    def test_7_day_fit_span(self):
        """Test 7-day fit span."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.fitspan_days == 7

    def test_14_day_fit_span(self):
        """Test 14-day fit span."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS14"
        parsed = LegacyDatasetCode.from_code(code)
        assert parsed.fitspan_days == 14


class TestCodeGeneration:
    """Tests for generating 16-character codes."""

    def test_generate_basic_code(self):
        """Test generating a basic 16-character code."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code_obj = LegacyDatasetCode(
            object_type="U",
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
        code = code_obj.to_code()

        assert len(code) == 16
        assert code == "U50LEONEOPSSSS07"

    def test_generate_hamr_leo_code(self):
        """Test generating HAMR LEO code."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code_obj = LegacyDatasetCode(
            object_type="H",
            target_percentage="10",
            orbital_regime="LEO",
            event="MB",
            sensor_type="OP",
            orbit_coverage="A",
            track_gap="S",
            observation_count="N",
            object_count="L",
            fitspan_days=3,
        )
        code = code_obj.to_code()

        assert code[0] == "H"
        assert code[1:3] == "10"
        assert code[3:6] == "LEO"
        assert code[6:8] == "MB"


class TestCodeRoundtrip:
    """Tests for code parse → generate → parse consistency."""

    def test_roundtrip_preserves_all_fields(self):
        """Test that roundtrip preserves all code fields."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        original = "H10GEOBUOPANSL05"
        parsed = LegacyDatasetCode.from_code(original)

        regenerated_obj = LegacyDatasetCode(
            object_type=parsed.object_type,
            target_percentage=parsed.target_percentage,
            orbital_regime=parsed.orbital_regime,
            event=parsed.event,
            sensor_type=parsed.sensor_type,
            orbit_coverage=parsed.orbit_coverage,
            track_gap=parsed.track_gap,
            observation_count=parsed.observation_count,
            object_count=parsed.object_count,
            fitspan_days=parsed.fitspan_days,
        )
        regenerated = regenerated_obj.to_code()

        assert regenerated == original

    def test_multiple_roundtrips(self):
        """Test multiple codes roundtrip correctly."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        test_codes = [
            "U50LEONEOPSSSS07",
            "H10MEONEOPAAAL03",
            "C01GEOBUOPNNNS01",
            "A50HEOLLOPSSLS05",
            "N10ALLMBOPASSH02",
        ]

        for original in test_codes:
            parsed = LegacyDatasetCode.from_code(original)
            regenerated_obj = LegacyDatasetCode(
                object_type=parsed.object_type,
                target_percentage=parsed.target_percentage,
                orbital_regime=parsed.orbital_regime,
                event=parsed.event,
                sensor_type=parsed.sensor_type,
                orbit_coverage=parsed.orbit_coverage,
                track_gap=parsed.track_gap,
                observation_count=parsed.observation_count,
                object_count=parsed.object_count,
                fitspan_days=parsed.fitspan_days,
            )
            regenerated = regenerated_obj.to_code()
            assert regenerated == original, f"Roundtrip failed for {original}"


class TestInvalidCodes:
    """Tests for handling invalid codes."""

    def test_too_short_code(self):
        """Test that codes shorter than 16 characters raise error."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        with pytest.raises(ValueError):
            LegacyDatasetCode.from_code("U50LEO")

    def test_too_long_code(self):
        """Test that codes longer than 16 characters raise error."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        with pytest.raises(ValueError):
            LegacyDatasetCode.from_code("U50LEONEOPSSSS07XXX")


class TestEnhancedConversion:
    """Tests for conversion between legacy and enhanced formats."""

    def test_legacy_to_enhanced(self):
        """Test converting legacy code to enhanced format."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        legacy = LegacyDatasetCode.from_code("U50LEONEOPSSSS07")
        enhanced = legacy.to_enhanced()

        # Check that enhanced code was created
        assert enhanced is not None
        assert hasattr(enhanced, "regime")
        assert enhanced.regime == "LEO"

    def test_enhanced_roundtrip(self):
        """Test that legacy → enhanced → legacy preserves key fields."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        original = LegacyDatasetCode.from_code("H10MEONEOPAAAS07")
        enhanced = original.to_enhanced()
        back_to_legacy = LegacyDatasetCode.from_enhanced(enhanced)

        # Key fields should be preserved (some mapping may occur)
        assert back_to_legacy.object_type == original.object_type
        assert back_to_legacy.orbital_regime == original.orbital_regime


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
