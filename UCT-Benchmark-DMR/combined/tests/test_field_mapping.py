# -*- coding: utf-8 -*-
"""
Tests for field name normalization utility.

Per Feb 19, 2026 transcript:
  "Different field names (VX vs XVEL) currently cause errors.
   Future: add flexible field name mapping."
"""

import pandas as pd
import pytest

from uct_benchmark.utils.field_mapping import (
    get_canonical_name,
    normalize_columns,
    normalize_record,
    normalize_submission,
    validate_required_fields,
)


class TestGetCanonicalName:
    """Tests for individual field name resolution."""

    def test_canonical_name_unchanged(self):
        assert get_canonical_name("xpos") == "xpos"
        assert get_canonical_name("xvel") == "xvel"

    def test_velocity_aliases(self):
        assert get_canonical_name("vx") == "xvel"
        assert get_canonical_name("VX") == "xvel"
        assert get_canonical_name("x_vel") == "xvel"
        assert get_canonical_name("vy") == "yvel"
        assert get_canonical_name("VZ") == "zvel"

    def test_position_aliases(self):
        assert get_canonical_name("x_pos") == "xpos"
        assert get_canonical_name("pos_y") == "ypos"

    def test_grouped_ops_aliases(self):
        assert get_canonical_name("grouped_ops") == "grouped_ops"
        assert get_canonical_name("sourcedData") == "grouped_ops"
        assert get_canonical_name("sourced_data") == "grouped_ops"

    def test_source_data_types_aliases(self):
        assert get_canonical_name("source_data_types") == "source_data_types"
        assert get_canonical_name("sourcedDataTypes") == "source_data_types"

    def test_unknown_field_passes_through(self):
        assert get_canonical_name("someCustomField") == "someCustomField"
        assert get_canonical_name("algorithm") == "algorithm"

    def test_case_insensitive_lookup(self):
        assert get_canonical_name("XPOS") == "xpos"
        assert get_canonical_name("Epoch") == "epoch"


class TestNormalizeColumns:
    """Tests for DataFrame column normalization."""

    def test_renames_velocity_columns(self):
        df = pd.DataFrame({"vx": [1], "vy": [2], "vz": [3]})
        result = normalize_columns(df)
        assert list(result.columns) == ["xvel", "yvel", "zvel"]

    def test_preserves_unknown_columns(self):
        df = pd.DataFrame({"xpos": [1], "custom_field": [2]})
        result = normalize_columns(df)
        assert "xpos" in result.columns
        assert "custom_field" in result.columns

    def test_mixed_canonical_and_alias(self):
        df = pd.DataFrame({"xpos": [1], "VX": [2], "epoch": [3]})
        result = normalize_columns(df)
        assert set(result.columns) == {"xpos", "xvel", "epoch"}


class TestNormalizeRecord:
    """Tests for single record normalization."""

    def test_normalizes_uctp_record(self):
        record = {
            "sourcedData": ["obs1", "obs2"],
            "sourcedDataTypes": ["EO", "EO"],
            "vx": 1.0,
            "vy": 2.0,
            "vz": 3.0,
            "epoch": "2026-01-01T00:00:00",
        }
        result = normalize_record(record)
        assert "grouped_ops" in result
        assert "source_data_types" in result
        assert "xvel" in result
        assert result["xvel"] == 1.0

    def test_preserves_unknown_keys(self):
        record = {"algorithm": "myAlgo", "rms": 0.5}
        result = normalize_record(record)
        assert result["algorithm"] == "myAlgo"


class TestNormalizeSubmission:
    """Tests for full submission normalization."""

    def test_normalizes_list_of_records(self):
        submission = [
            {"sourcedData": ["obs1"], "vx": 1.0, "vy": 2.0, "vz": 3.0},
            {"sourcedData": ["obs2"], "VX": 4.0, "VY": 5.0, "VZ": 6.0},
        ]
        result = normalize_submission(submission)
        assert all("grouped_ops" in r for r in result)
        assert all("xvel" in r for r in result)

    def test_empty_submission(self):
        assert normalize_submission([]) == []


class TestValidateRequiredFields:
    """Tests for required field validation."""

    def test_all_present(self):
        record = {
            "grouped_ops": ["obs1"],
            "epoch": "2026-01-01",
            "xpos": 1, "ypos": 2, "zpos": 3,
            "xvel": 4, "yvel": 5, "zvel": 6,
        }
        missing = validate_required_fields(record)
        assert missing == []

    def test_missing_fields(self):
        record = {"epoch": "2026-01-01", "xpos": 1}
        missing = validate_required_fields(record)
        assert "grouped_ops" in missing
        assert "ypos" in missing
