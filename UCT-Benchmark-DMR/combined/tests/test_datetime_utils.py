# -*- coding: utf-8 -*-
"""Tests for datetime parsing utilities."""

import pytest
from datetime import datetime

import pandas as pd


class TestParseDatetime:
    """Tests for parse_datetime function."""

    def test_import_from_utils(self):
        """Verify function can be imported from uct_benchmark.utils."""
        from uct_benchmark.utils import parse_datetime

        assert callable(parse_datetime)

    def test_import_from_datetime_utils_module(self):
        """Verify function can be imported from datetime_utils module directly."""
        from uct_benchmark.utils.datetime_utils import parse_datetime

        assert callable(parse_datetime)

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            # Standard ISO format with microseconds and Z
            (
                "2025-01-15T12:30:45.123456Z",
                datetime(2025, 1, 15, 12, 30, 45, 123456),
            ),
            # Standard ISO format without microseconds
            (
                "2025-01-15T12:30:45Z",
                datetime(2025, 1, 15, 12, 30, 45),
            ),
            # ISO format without Z suffix
            (
                "2025-01-15T12:30:45.123456",
                datetime(2025, 1, 15, 12, 30, 45, 123456),
            ),
            # ISO format without microseconds or Z
            (
                "2025-01-15T12:30:45",
                datetime(2025, 1, 15, 12, 30, 45),
            ),
            # Malformed format with both +00:00 and Z (common bug in some systems)
            (
                "2025-01-15T12:30:45+00:00Z",
                datetime(2025, 1, 15, 12, 30, 45),
            ),
            # Malformed with microseconds
            (
                "2025-01-15T12:30:45.123456+00:00Z",
                datetime(2025, 1, 15, 12, 30, 45, 123456),
            ),
        ],
    )
    def test_parse_datetime_formats(self, input_str, expected):
        """Test parsing various datetime string formats."""
        from uct_benchmark.utils.datetime_utils import parse_datetime

        result = parse_datetime(input_str)
        assert result == expected, f"Expected {expected} for input '{input_str}', got {result}"

    def test_parse_datetime_object(self):
        """Test that datetime objects are returned unchanged."""
        from uct_benchmark.utils.datetime_utils import parse_datetime

        dt = datetime(2025, 1, 15, 12, 30, 45)
        result = parse_datetime(dt)
        assert result is dt  # Should be the same object

    def test_parse_pandas_timestamp(self):
        """Test that pandas Timestamps are converted correctly."""
        from uct_benchmark.utils.datetime_utils import parse_datetime

        ts = pd.Timestamp("2025-01-15 12:30:45")
        result = parse_datetime(ts)

        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 45


class TestEnsureDatetimeColumn:
    """Tests for ensure_datetime_column function."""

    def test_import_from_utils(self):
        """Verify function can be imported from uct_benchmark.utils."""
        from uct_benchmark.utils import ensure_datetime_column

        assert callable(ensure_datetime_column)

    def test_converts_string_column(self):
        """Test conversion of string column to datetime."""
        from uct_benchmark.utils.datetime_utils import ensure_datetime_column

        df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "obTime": [
                    "2025-01-15T12:30:45Z",
                    "2025-01-16T13:45:00Z",
                    "2025-01-17T14:00:30Z",
                ],
            }
        )

        original_dtype = str(df["obTime"].dtype)
        result = ensure_datetime_column(df, "obTime")

        # Should return a copy, not modify in place
        assert result is not df
        # Original dtype should be unchanged (string-like: 'object', 'string', or 'str')
        assert str(df["obTime"].dtype) == original_dtype

        # Converted column should have datetime values
        assert isinstance(result["obTime"].iloc[0], datetime)

    def test_does_not_modify_original(self):
        """Verify the function doesn't modify the original DataFrame."""
        from uct_benchmark.utils.datetime_utils import ensure_datetime_column

        df = pd.DataFrame(
            {
                "id": [1, 2],
                "obTime": ["2025-01-15T12:30:45Z", "2025-01-16T13:45:00Z"],
            }
        )
        original_dtype = df["obTime"].dtype

        ensure_datetime_column(df, "obTime")

        # Original should be unchanged
        assert df["obTime"].dtype == original_dtype

    def test_handles_malformed_timestamps(self):
        """Test handling of malformed timestamps with +00:00Z suffix."""
        from uct_benchmark.utils.datetime_utils import ensure_datetime_column

        df = pd.DataFrame(
            {
                "id": [1, 2],
                "obTime": [
                    "2025-01-15T12:30:45+00:00Z",  # Malformed
                    "2025-01-16T13:45:00Z",  # Normal
                ],
            }
        )

        result = ensure_datetime_column(df, "obTime")

        # Both should be parsed correctly
        assert isinstance(result["obTime"].iloc[0], datetime)
        assert isinstance(result["obTime"].iloc[1], datetime)
        assert result["obTime"].iloc[0].year == 2025
