# -*- coding: utf-8 -*-
"""
Datetime parsing utilities.

Consolidated from duplicate implementations across:
- uct_benchmark/simulation/simulateObservations.py
- uct_benchmark/data/dataManipulation.py
- backend_api/jobs/workers.py
"""

from datetime import datetime
from typing import Union

import pandas as pd


def parse_datetime(dt_value: Union[str, datetime, pd.Timestamp]) -> datetime:
    """
    Parse datetime from various formats used across the codebase.

    Handles:
    - Python datetime objects (returned as-is)
    - Pandas Timestamp objects (converted to datetime)
    - ISO format strings with various timezone suffixes
    - Malformed datetime strings with both +00:00 and Z suffix

    Args:
        dt_value: Datetime value in various formats

    Returns:
        datetime: Parsed datetime object

    Examples:
        >>> parse_datetime("2025-01-15T12:30:45.123456Z")
        datetime.datetime(2025, 1, 15, 12, 30, 45, 123456)
        >>> parse_datetime("2025-01-15T12:30:45Z")
        datetime.datetime(2025, 1, 15, 12, 30, 45)
        >>> parse_datetime("2025-01-15T12:30:45+00:00Z")  # Malformed but handled
        datetime.datetime(2025, 1, 15, 12, 30, 45)
    """
    # Handle already-parsed values
    if isinstance(dt_value, datetime):
        return dt_value
    if isinstance(dt_value, pd.Timestamp):
        return dt_value.to_pydatetime()

    s = str(dt_value)

    # Fix malformed datetime with both +00:00 and Z suffix
    if "+00:00Z" in s:
        s = s.replace("+00:00Z", "Z")

    # Try standard formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
    ]

    for fmt in formats:
        try:
            # Remove Z for non-Z formats to allow parsing
            parse_str = s.replace("Z", "") if "Z" not in fmt else s
            result = datetime.strptime(parse_str, fmt.replace("Z", ""))
            # Remove timezone info to return naive datetime
            if result.tzinfo is not None:
                result = result.replace(tzinfo=None)
            return result
        except ValueError:
            continue

    # Fall back to pandas parsing
    return pd.to_datetime(s).to_pydatetime()


def ensure_datetime_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Ensure a DataFrame column contains datetime objects.

    Args:
        df: DataFrame to process
        column: Name of column to convert

    Returns:
        pd.DataFrame: DataFrame with converted column (copy, not in-place)
    """
    df = df.copy()
    # Check if column contains string data (handles both 'object' and 'string' dtypes)
    dtype_str = str(df[column].dtype).lower()
    if dtype_str in ("object", "string", "str") or "string" in dtype_str:
        df[column] = df[column].apply(parse_datetime)
    return df
