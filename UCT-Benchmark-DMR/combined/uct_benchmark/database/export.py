"""
Export and import utilities for UCT Benchmark database.

Provides functions to export datasets to JSON/Parquet formats
and import existing data files into the database.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Union

import pandas as pd

if TYPE_CHECKING:
    from .connection import DatabaseManager


def export_dataset_to_json(
    db: "DatabaseManager",
    dataset_id: int,
    output_path: Optional[Union[str, Path]] = None,
    include_truth: bool = True,
) -> Path:
    """
    Export a dataset to the standard JSON format.

    This format matches the existing saveDataset() output for compatibility
    with UCTP algorithms.

    Args:
        db: DatabaseManager instance
        dataset_id: ID of the dataset to export
        output_path: Optional output path. If None, uses default location.
        include_truth: If True, include truth data for evaluation

    Returns:
        Path to the exported JSON file
    """
    # Get dataset metadata
    dataset = db.datasets.get_dataset(dataset_id=dataset_id)
    if dataset is None:
        raise ValueError(f"Dataset {dataset_id} not found")

    # Get observations with track assignments
    obs_df = db.datasets.get_dataset_observations(dataset_id)

    # Get reference data
    ref_df = db.datasets.get_dataset_references(dataset_id)

    # Build the output structure matching existing format
    output_data = {
        "metadata": {
            "name": dataset.get("name"),
            "code": dataset.get("code"),
            "tier": dataset.get("tier"),
            "orbital_regime": dataset.get("orbital_regime"),
            "time_window_start": _serialize_datetime(dataset.get("time_window_start")),
            "time_window_end": _serialize_datetime(dataset.get("time_window_end")),
            "observation_count": len(obs_df),
            "satellite_count": int(dataset.get("satellite_count", 0)),
            "created_at": _serialize_datetime(dataset.get("created_at")),
            "generation_params": dataset.get("generation_params", {}),
        },
        "observations": [],
    }

    # Build observations list (UCT format)
    for _, row in obs_df.iterrows():
        obs_entry = {
            "id": row["id"],
            "ob_time": _serialize_datetime(row["ob_time"]),
            "ra": float(row["ra"]) if pd.notna(row.get("ra")) else None,
            "declination": float(row["declination"]) if pd.notna(row.get("declination")) else None,
            "track_id": int(row["assigned_track_id"])
            if pd.notna(row.get("assigned_track_id"))
            else None,
            "uct": True,  # All observations in dataset are decorrelated
        }

        # Include truth data if requested
        if include_truth:
            obs_entry["orig_object_id"] = (
                int(row["assigned_object_id"])
                if pd.notna(row.get("assigned_object_id"))
                else int(row["sat_no"])
                if pd.notna(row.get("sat_no"))
                else None
            )

        # Add optional fields
        if pd.notna(row.get("sensor_name")):
            obs_entry["sensor_name"] = row["sensor_name"]
        if pd.notna(row.get("range_km")):
            obs_entry["range_km"] = float(row["range_km"])
        if pd.notna(row.get("range_rate_km_s")):
            obs_entry["range_rate_km_s"] = float(row["range_rate_km_s"])
        if pd.notna(row.get("azimuth")):
            obs_entry["azimuth"] = float(row["azimuth"])
        if pd.notna(row.get("elevation")):
            obs_entry["elevation"] = float(row["elevation"])

        output_data["observations"].append(obs_entry)

    # Include reference data if truth is requested
    if include_truth and not ref_df.empty:
        output_data["references"] = []
        for _, row in ref_df.iterrows():
            ref_entry = {
                "sat_no": int(row["sat_no"]),
                "sat_name": row.get("sat_name"),
                "orbital_regime": row.get("orbital_regime"),
            }

            # Parse grouped observation IDs
            grouped_ids = row.get("grouped_obs_ids")
            if grouped_ids:
                if isinstance(grouped_ids, str):
                    try:
                        grouped_ids = json.loads(grouped_ids)
                    except json.JSONDecodeError:
                        grouped_ids = []
                ref_entry["observation_ids"] = grouped_ids

            # Get state vector if available
            if pd.notna(row.get("state_vector_id")):
                sv = db.state_vectors.get(int(row["state_vector_id"]))
                if sv is not None:
                    ref_entry["state_vector"] = {
                        "epoch": _serialize_datetime(sv.get("epoch")),
                        "position_km": [
                            float(sv["x_pos"]),
                            float(sv["y_pos"]),
                            float(sv["z_pos"]),
                        ],
                        "velocity_km_s": [
                            float(sv["x_vel"]),
                            float(sv["y_vel"]),
                            float(sv["z_vel"]),
                        ],
                    }
                    if pd.notna(sv.get("covariance")):
                        cov = sv["covariance"]
                        if isinstance(cov, str):
                            cov = json.loads(cov)
                        ref_entry["state_vector"]["covariance"] = cov

            # Get element set if available
            if pd.notna(row.get("element_set_id")):
                elset = db.element_sets.get(int(row["element_set_id"]))
                if elset is not None:
                    ref_entry["tle"] = {
                        "line1": elset["line1"],
                        "line2": elset["line2"],
                        "epoch": _serialize_datetime(elset.get("epoch")),
                    }

            output_data["references"].append(ref_entry)

    # Determine output path
    if output_path is None:
        try:
            from uct_benchmark.settings import PROCESSED_DATA_DIR

            output_dir = PROCESSED_DATA_DIR / "datasets"
        except ImportError:
            output_dir = Path("data/processed/datasets")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{dataset['name']}.json"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, default=str)

    # Update dataset with export path
    db.datasets.update_dataset(dataset_id, json_path=str(output_path))

    return output_path


def export_observations_to_parquet(
    db: "DatabaseManager",
    output_path: Union[str, Path],
    sat_nos: Optional[List[int]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    compression: str = "zstd",
    row_group_size: int = 100_000,
) -> Path:
    """
    Export observations to Parquet format.

    Args:
        db: DatabaseManager instance
        output_path: Output file path
        sat_nos: Optional list of satellite numbers to filter
        start_time: Optional start time filter
        end_time: Optional end time filter
        compression: Compression algorithm (zstd, snappy, gzip)
        row_group_size: Rows per row group

    Returns:
        Path to the exported Parquet file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build query
    conditions = []
    params = []

    if sat_nos:
        placeholders = ", ".join(["?"] * len(sat_nos))
        conditions.append(f"sat_no IN ({placeholders})")
        params.extend(sat_nos)

    if start_time:
        conditions.append("ob_time >= ?")
        params.append(start_time)

    if end_time:
        conditions.append("ob_time <= ?")
        params.append(end_time)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT * FROM observations
        WHERE {where_clause}
        ORDER BY ob_time
    """

    df = db.observations.to_dataframe(query, tuple(params))

    # Write to Parquet
    df.to_parquet(
        output_path,
        engine="pyarrow",
        compression=compression,
        row_group_size=row_group_size,
        index=False,
    )

    return output_path


def import_dataset_from_json(
    db: "DatabaseManager",
    json_path: Union[str, Path],
    dataset_name: Optional[str] = None,
    import_observations: bool = True,
    import_references: bool = True,
) -> int:
    """
    Import a dataset from JSON format into the database.

    Args:
        db: DatabaseManager instance
        json_path: Path to the JSON file
        dataset_name: Optional override for dataset name
        import_observations: If True, import observation records
        import_references: If True, import reference/truth data

    Returns:
        ID of the created dataset
    """
    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})

    # Create dataset record
    name = dataset_name or metadata.get("name", json_path.stem)

    dataset_id = db.datasets.create_dataset(
        name=name,
        code=metadata.get("code"),
        tier=metadata.get("tier"),
        orbital_regime=metadata.get("orbital_regime"),
        time_window_start=_parse_datetime(metadata.get("time_window_start")),
        time_window_end=_parse_datetime(metadata.get("time_window_end")),
        generation_params=metadata.get("generation_params"),
    )

    observations = data.get("observations", [])
    references = data.get("references", [])

    # Import observations
    if import_observations and observations:
        obs_ids = []
        track_assignments = {}
        object_assignments = {}

        for obs in observations:
            obs_id = obs.get("id")
            if not obs_id:
                continue

            obs_ids.append(obs_id)

            if obs.get("track_id") is not None:
                track_assignments[obs_id] = obs["track_id"]
            if obs.get("orig_object_id") is not None:
                object_assignments[obs_id] = obs["orig_object_id"]

            # Insert observation into observations table if needed
            existing = db.observations.get_by_id(obs_id)
            if existing is None:
                # Build observation record
                obs_df = pd.DataFrame(
                    [
                        {
                            "id": obs_id,
                            "sat_no": obs.get("orig_object_id"),
                            "ob_time": _parse_datetime(obs.get("ob_time")),
                            "ra": obs.get("ra"),
                            "declination": obs.get("declination"),
                            "range_km": obs.get("range_km"),
                            "range_rate_km_s": obs.get("range_rate_km_s"),
                            "azimuth": obs.get("azimuth"),
                            "elevation": obs.get("elevation"),
                            "sensor_name": obs.get("sensor_name"),
                            "track_id": str(obs.get("track_id")) if obs.get("track_id") else None,
                            "is_uct": obs.get("uct", True),
                            "is_simulated": obs.get("is_simulated", False),
                            "data_mode": "SIMULATED" if obs.get("is_simulated") else "REAL",
                        }
                    ]
                )
                db.observations.bulk_insert(obs_df)

        # Link observations to dataset
        db.datasets.add_observations_to_dataset(
            dataset_id, obs_ids, track_assignments, object_assignments
        )

    # Import references
    if import_references and references:
        for ref in references:
            sat_no = ref.get("sat_no")
            if not sat_no:
                continue

            # Ensure satellite exists
            if db.satellites.get(sat_no) is None:
                db.satellites.create(
                    sat_no=sat_no,
                    name=ref.get("sat_name"),
                    orbital_regime=ref.get("orbital_regime"),
                )

            state_vector_id = None
            element_set_id = None

            # Import state vector if present
            sv_data = ref.get("state_vector")
            if sv_data:
                pos = sv_data.get("position_km", [0, 0, 0])
                vel = sv_data.get("velocity_km_s", [0, 0, 0])
                state_vector_id = db.state_vectors.create(
                    sat_no=sat_no,
                    epoch=_parse_datetime(sv_data.get("epoch")),
                    x_pos=pos[0],
                    y_pos=pos[1],
                    z_pos=pos[2],
                    x_vel=vel[0],
                    y_vel=vel[1],
                    z_vel=vel[2],
                    covariance=sv_data.get("covariance"),
                    source="IMPORTED",
                )

            # Import TLE if present
            tle_data = ref.get("tle")
            if tle_data:
                element_set_id = db.element_sets.create(
                    sat_no=sat_no,
                    line1=tle_data.get("line1", ""),
                    line2=tle_data.get("line2", ""),
                    epoch=_parse_datetime(tle_data.get("epoch")),
                    source="IMPORTED",
                )

            # Link reference to dataset
            db.datasets.add_references_to_dataset(
                dataset_id=dataset_id,
                sat_no=sat_no,
                state_vector_id=state_vector_id,
                element_set_id=element_set_id,
                grouped_obs_ids=ref.get("observation_ids"),
            )

    # Update dataset statistics
    obs_count = len(observations) if observations else 0
    sat_count = (
        len(set(ref.get("sat_no") for ref in references if ref.get("sat_no"))) if references else 0
    )

    db.datasets.update_dataset(
        dataset_id,
        status="complete",
        observation_count=obs_count,
        satellite_count=sat_count,
        json_path=str(json_path),
    )

    return dataset_id


def import_parquet_to_database(
    db: "DatabaseManager",
    parquet_path: Union[str, Path],
    table_name: str = "observations",
    on_conflict: str = "ignore",
) -> int:
    """
    Import data from a Parquet file into the database.

    Args:
        db: DatabaseManager instance
        parquet_path: Path to the Parquet file
        table_name: Target table name
        on_conflict: Conflict handling ("ignore", "replace")

    Returns:
        Number of records imported
    """
    parquet_path = Path(parquet_path)
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

    df = pd.read_parquet(parquet_path)

    if table_name == "observations":
        return db.observations.bulk_insert(df)
    elif table_name == "state_vectors":
        return db.state_vectors.bulk_insert(df)
    elif table_name == "element_sets":
        return db.element_sets.bulk_insert(df)
    elif table_name == "satellites":
        return db.satellites.bulk_upsert(df)
    else:
        raise ValueError(f"Unknown table: {table_name}")


def _serialize_datetime(dt: Any) -> Optional[str]:
    """Convert datetime to ISO format string."""
    if dt is None:
        return None
    # Handle pandas NaT (Not a Time)
    if pd.isna(dt):
        return None
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return str(dt)


def _parse_datetime(dt_str: Any) -> Optional[datetime]:
    """Parse datetime from string."""
    if dt_str is None:
        return None
    if isinstance(dt_str, datetime):
        return dt_str

    # Try various formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(str(dt_str), fmt)
        except ValueError:
            continue

    return None
