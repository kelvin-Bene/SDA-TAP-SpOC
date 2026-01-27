"""
Observation data ingestion for UCTP Lab.

Loads observations from various sources (JSON files, database, DataFrames)
and normalizes them into a standard format for pipeline processing.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import pandas as pd
from loguru import logger


# Standard column names expected by the pipeline
REQUIRED_COLUMNS = ["id", "ob_time", "ra", "declination"]
OPTIONAL_COLUMNS = ["sensor_name", "track_id", "sat_no", "senlon", "senlat", "senalt"]


def load_observations_from_json(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Load observations from a JSON file.

    Supports two formats:
    1. List of observation dicts (from dataset download)
    2. Dict with "observations" key (from dataset export)

    Returns:
        DataFrame with standardized column names.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Observation file not found: {path}")

    with open(path, "r") as f:
        data = json.load(f)

    if isinstance(data, dict) and "observations" in data:
        obs_list = data["observations"]
    elif isinstance(data, list):
        obs_list = data
    else:
        raise ValueError("Unrecognized JSON format: expected list or dict with 'observations' key")

    if not obs_list:
        logger.warning(f"No observations found in {path}")
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    df = pd.DataFrame(obs_list)
    return _normalize_columns(df)


def load_observations_from_database(dataset_id: int, db=None) -> pd.DataFrame:
    """
    Load observations for a dataset from the DuckDB database.

    Args:
        dataset_id: ID of the dataset to load.
        db: DatabaseManager instance. If None, uses get_db().

    Returns:
        DataFrame with standardized column names.
    """
    if db is None:
        from backend_api.database import get_db
        db = get_db()

    result = db.execute(
        """
        SELECT o.id, o.ob_time, o.ra, o.declination, o.sensor_name,
               o.track_id, o.sat_no
        FROM observations o
        JOIN dataset_observations dso ON o.id = dso.observation_id
        WHERE dso.dataset_id = ?
        ORDER BY o.ob_time
        """,
        (dataset_id,),
    )
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    if not rows:
        logger.warning(f"No observations found for dataset {dataset_id}")
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    df = pd.DataFrame(rows, columns=columns)
    return _normalize_columns(df)


def load_observations_from_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize an existing DataFrame to the standard pipeline format.

    Handles common column name variations (e.g., obTime -> ob_time, satNo -> sat_no).
    """
    return _normalize_columns(df.copy())


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and types to the standard pipeline format."""
    # Column name mapping for common variations
    rename_map = {
        "obTime": "ob_time",
        "ob_time": "ob_time",
        "satNo": "sat_no",
        "sat_no": "sat_no",
        "trackId": "track_id",
        "track_id": "track_id",
        "sensorName": "sensor_name",
        "sensor_name": "sensor_name",
    }

    # Apply renames where columns exist
    actual_renames = {}
    for old_name, new_name in rename_map.items():
        if old_name in df.columns and old_name != new_name:
            actual_renames[old_name] = new_name
    if actual_renames:
        df = df.rename(columns=actual_renames)

    # Validate required columns
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Parse timestamps
    if not pd.api.types.is_datetime64_any_dtype(df["ob_time"]):
        df["ob_time"] = pd.to_datetime(df["ob_time"], utc=True)

    # Ensure numeric types for coordinates
    df["ra"] = pd.to_numeric(df["ra"], errors="coerce")
    df["declination"] = pd.to_numeric(df["declination"], errors="coerce")

    # Drop rows with NaN coordinates
    before = len(df)
    df = df.dropna(subset=["ra", "declination"]).reset_index(drop=True)
    dropped = before - len(df)
    if dropped > 0:
        logger.warning(f"Dropped {dropped} observations with NaN coordinates")

    # Sort by time
    df = df.sort_values("ob_time").reset_index(drop=True)

    # Ensure string IDs
    df["id"] = df["id"].astype(str)

    return df
