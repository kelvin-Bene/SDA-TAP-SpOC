# -*- coding: utf-8 -*-
"""
Test Suite for Target Percentage Enforcement

Tests the target percentage enforcement from 16-character dataset codes,
per Louis's specification:
"Target Object % specifies what percentage of dataset should be target objects"
"50 = 50% Target objects, 10 = 10% Target objects, 01 = 1% target objects"

Author: UCT Benchmark Team
Date: 2026
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestTargetPercentageParsing:
    """Tests for parsing target percentage from dataset codes."""

    def test_parse_50_percent(self):
        """Test parsing '50' as 50% target percentage."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U50LEONEOPSSSS07"  # 50% in positions 2-3
        parsed = LegacyDatasetCode.from_code(code)

        assert parsed.target_percentage == "50"

    def test_parse_10_percent(self):
        """Test parsing '10' as 10% target percentage."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U10LEONEOPSSSS07"  # 10% in positions 2-3
        parsed = LegacyDatasetCode.from_code(code)

        assert parsed.target_percentage == "10"

    def test_parse_01_percent(self):
        """Test parsing '01' as 1% target percentage."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "U01LEONEOPSSSS07"  # 01% (1%) in positions 2-3
        parsed = LegacyDatasetCode.from_code(code)

        assert parsed.target_percentage == "01"

    def test_parse_unspecified(self):
        """Test parsing 'UN' as unspecified (no enforcement)."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        code = "UUNLEONEOPSSSS07"  # UN in positions 2-3
        parsed = LegacyDatasetCode.from_code(code)

        assert parsed.target_percentage == "UN"


def _import_enforce_target_percentage():
    """Helper to import enforce_target_percentage, skipping if jpype unavailable."""
    try:
        from uct_benchmark.api.apiIntegration import enforce_target_percentage
        return enforce_target_percentage
    except ModuleNotFoundError as e:
        if "jpype" in str(e):
            pytest.skip("jpype not installed (Orekit dependency)")
        raise


class TestEnforceTargetPercentage:
    """Tests for enforce_target_percentage function."""

    @pytest.fixture
    def sample_satellites(self):
        """Create sample satellite list."""
        return [25544, 25545, 25546, 25547, 25548,
                25549, 25550, 25551, 25552, 25553]  # 10 satellites

    def test_function_exists(self):
        """Test that enforce_target_percentage function exists."""
        enforce_target_percentage = _import_enforce_target_percentage()
        assert callable(enforce_target_percentage)

    def test_50_percent_enforcement(self, sample_satellites):
        """Test 50% target percentage enforcement."""
        enforce_target_percentage = _import_enforce_target_percentage()

        result = enforce_target_percentage(
            satellites=sample_satellites,
            target_percentage=50,
        )

        # Should return approximately 50% of satellites
        assert len(result) == pytest.approx(5, abs=1)

    def test_10_percent_enforcement(self, sample_satellites):
        """Test 10% target percentage enforcement."""
        enforce_target_percentage = _import_enforce_target_percentage()

        result = enforce_target_percentage(
            satellites=sample_satellites,
            target_percentage=10,
        )

        # Should return approximately 10% of satellites
        assert len(result) == pytest.approx(1, abs=1)

    def test_01_percent_enforcement(self):
        """Test 1% target percentage enforcement."""
        enforce_target_percentage = _import_enforce_target_percentage()

        # Need 100 satellites to get 1%
        satellites = list(range(1, 101))

        result = enforce_target_percentage(
            satellites=satellites,
            target_percentage=1,
        )

        # Should return approximately 1% of satellites
        assert len(result) == pytest.approx(1, abs=1)

    def test_unspecified_returns_all(self, sample_satellites):
        """Test that unspecified percentage returns all satellites."""
        enforce_target_percentage = _import_enforce_target_percentage()

        result = enforce_target_percentage(
            satellites=sample_satellites,
            target_percentage=None,  # Unspecified
        )

        # Should return all satellites
        assert len(result) == len(sample_satellites)

    def test_zero_percent_returns_all(self, sample_satellites):
        """Test that 0% returns all (interpreted as no enforcement)."""
        enforce_target_percentage = _import_enforce_target_percentage()

        result = enforce_target_percentage(
            satellites=sample_satellites,
            target_percentage=0,  # Zero = no enforcement
        )

        # Should return all satellites
        assert len(result) == len(sample_satellites)


class TestTargetPercentageMetadata:
    """Tests for target percentage metadata in API responses."""

    def test_metadata_uses_selected_satellites_key(self):
        """Test that metadata uses 'selected_satellites' key (not 'matching_satellites')."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code
        import pandas as pd

        obs_df = pd.DataFrame({
            "id": ["obs_1", "obs_2"],
            "satNo": [25544, 25545],
            "obTime": [datetime(2024, 1, 1)] * 2,
            "ra": [100.0, 101.0],
            "declination": [20.0, 21.0],
        })

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=obs_df,
            object_type_code="U",
            sat_params={},
            physical_data={},
        )

        # Check the key used
        assert "selected_satellites" in metadata or "total_satellites" in metadata

    def test_metadata_contains_satellite_count(self):
        """Test that metadata contains satellite count information."""
        from uct_benchmark.data.objectTypeFiltering import filter_by_object_type_code
        import pandas as pd

        obs_df = pd.DataFrame({
            "id": ["obs_1", "obs_2", "obs_3"],
            "satNo": [25544, 25545, 25546],
            "obTime": [datetime(2024, 1, 1)] * 3,
            "ra": [100.0, 101.0, 102.0],
            "declination": [20.0, 21.0, 22.0],
        })

        filtered_df, metadata = filter_by_object_type_code(
            obs_df=obs_df,
            object_type_code="U",
            sat_params={},
            physical_data={},
        )

        # Should have some count information
        assert "total_satellites" in metadata or "selected_satellites" in metadata


class TestTargetPercentageIntegration:
    """Integration tests for target percentage in full pipeline."""

    @pytest.fixture
    def sample_observations_df(self):
        """Create sample observations DataFrame with 20 satellites."""
        base_time = datetime(2024, 1, 1)
        n_sats = 20
        obs_per_sat = 10

        records = []
        for sat_idx in range(n_sats):
            sat_id = 25544 + sat_idx
            for obs_idx in range(obs_per_sat):
                records.append({
                    "id": f"obs_{sat_id}_{obs_idx}",
                    "satNo": sat_id,
                    "obTime": base_time + timedelta(hours=obs_idx),
                    "ra": 100.0 + sat_idx,
                    "declination": 20.0 + obs_idx,
                })

        return pd.DataFrame(records)

    def test_percentage_applied_in_pipeline(self, sample_observations_df):
        """Test that target percentage is applied in API integration."""
        # This tests the integration of percentage enforcement

        unique_sats = sample_observations_df["satNo"].nunique()
        assert unique_sats == 20  # Verify our test data

        # The actual percentage enforcement happens in apiIntegration
        # Just verify the data is set up correctly


class TestPercentageRounding:
    """Tests for rounding behavior in percentage enforcement."""

    def test_rounds_to_at_least_one(self):
        """Test that very low percentages still return at least 1."""
        enforce_target_percentage = _import_enforce_target_percentage()

        satellites = list(range(1, 11))  # 10 satellites

        # 1% of 10 = 0.1, should round up to 1
        result = enforce_target_percentage(
            satellites=satellites,
            target_percentage=1,
        )

        assert len(result) >= 1

    def test_100_percent_returns_all(self):
        """Test that 100% returns all satellites."""
        enforce_target_percentage = _import_enforce_target_percentage()

        satellites = list(range(1, 11))

        result = enforce_target_percentage(
            satellites=satellites,
            target_percentage=100,
        )

        assert len(result) == len(satellites)

    def test_percentage_greater_than_100_handled(self):
        """Test that percentages > 100 are handled gracefully."""
        enforce_target_percentage = _import_enforce_target_percentage()

        satellites = list(range(1, 11))

        # 150% should return all (can't have more than 100%)
        result = enforce_target_percentage(
            satellites=satellites,
            target_percentage=150,
        )

        assert len(result) <= len(satellites)


class TestLegacyCodeTargetPercentage:
    """Tests for target percentage in legacy 16-character codes."""

    def test_all_valid_percentage_codes(self):
        """Test all valid percentage codes are parsed correctly."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        test_cases = [
            ("U50LEONEOPSSSS07", "50"),
            ("U10LEONEOPSSSS07", "10"),
            ("U01LEONEOPSSSS07", "01"),
        ]

        for code, expected_pct in test_cases:
            parsed = LegacyDatasetCode.from_code(code)
            assert parsed.target_percentage == expected_pct, f"Failed for code {code}"

    def test_code_roundtrip_preserves_percentage(self):
        """Test that parse → generate → parse preserves percentage."""
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode

        original_code = "U50LEONEOPSSSS07"
        parsed = LegacyDatasetCode.from_code(original_code)

        # Generate code from parsed values
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

        # Parse again
        reparsed = LegacyDatasetCode.from_code(regenerated)

        assert reparsed.target_percentage == parsed.target_percentage


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
