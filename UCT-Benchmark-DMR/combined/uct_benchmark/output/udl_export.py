# -*- coding: utf-8 -*-
"""
UDL Export Module

This module provides utilities for exporting datasets to UDL-compatible format
for the UCT Benchmark. The export format is designed to:
1. Decorrelate observations from ground truth (remove satNo)
2. Provide ground truth mapping separately for evaluation
3. Include comprehensive metadata for reproducibility

Output structure:
    {dataset_name}/
        observations.json    # Decorrelated observations (no satNo)
        truth.json          # Ground truth mapping (track_id → satNo)
        metadata.json       # Dataset metadata with legacy code
        manifest.json       # File checksums for integrity verification

Author: UCT Benchmark Team
Date: 2026
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


def compute_file_checksum(filepath: Path, algorithm: str = "sha256") -> str:
    """
    Compute checksum of a file.

    Args:
        filepath: Path to the file
        algorithm: Hash algorithm to use (default: sha256)

    Returns:
        Hexadecimal checksum string
    """
    hash_func = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def decorrelate_observations(
    obs_df: pd.DataFrame,
    id_columns: List[str] = None,
    seed: Optional[int] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Decorrelate observations from ground truth for UCT benchmarking.

    This function:
    1. Removes identifying columns (satNo, idOnOrbit, origObjectId, etc.)
    2. Assigns new sequential track_id values
    3. Optionally shuffles track assignments for additional decorrelation
    4. Creates a truth mapping DataFrame for evaluation

    The decorrelated observations can be released to benchmark participants,
    while the truth mapping is kept for evaluation.

    Args:
        obs_df: DataFrame of observations with ground truth columns
        id_columns: List of columns to remove. Defaults to standard ID columns.
        seed: Random seed for reproducible shuffling (None = no shuffling)

    Returns:
        Tuple of (decorrelated_obs_df, truth_mapping_df)
        - decorrelated_obs_df: Observations with IDs removed, track_id assigned
        - truth_mapping_df: Mapping from track_id to original satNo
    """
    if id_columns is None:
        id_columns = [
            "satNo",
            "satNumber",
            "noradId",
            "idOnOrbit",
            "origObjectId",
            "objectId",
            "catalogId",
            "intlDesignator",
            "objectName",
        ]

    # Make a copy to avoid modifying original
    decorrelated_df = obs_df.copy()

    # Get the primary ID column (satNo or similar)
    primary_id_col = None
    for col in ["satNo", "satNumber", "noradId"]:
        if col in decorrelated_df.columns:
            primary_id_col = col
            break

    if primary_id_col is None:
        logger.warning("No primary ID column found. Creating dummy truth mapping.")
        # Assign sequential track IDs without ground truth
        decorrelated_df["track_id"] = range(len(decorrelated_df))
        truth_mapping = pd.DataFrame({"track_id": [], "satNo": []})
        return decorrelated_df, truth_mapping

    # Create truth mapping before removing IDs
    # Group observations by satellite and assign track IDs
    unique_sats = decorrelated_df[primary_id_col].unique()

    if seed is not None:
        np.random.seed(seed)
        # Shuffle satellite order for additional decorrelation
        np.random.shuffle(unique_sats)

    # Create mapping: track_id -> satNo
    sat_to_track = {sat: i + 1 for i, sat in enumerate(unique_sats)}

    # Assign track_id to observations
    decorrelated_df["track_id"] = decorrelated_df[primary_id_col].map(sat_to_track)

    # Create truth mapping DataFrame
    truth_mapping = pd.DataFrame([
        {"track_id": track_id, "satNo": int(sat_no)}
        for sat_no, track_id in sat_to_track.items()
    ]).sort_values("track_id")

    # Remove identifying columns
    columns_to_remove = [col for col in id_columns if col in decorrelated_df.columns]
    decorrelated_df = decorrelated_df.drop(columns=columns_to_remove)

    # Log what was removed
    if columns_to_remove:
        logger.info(f"Removed identifying columns: {columns_to_remove}")

    logger.info(
        f"Decorrelation complete: {len(unique_sats)} satellites -> "
        f"{len(unique_sats)} tracks, {len(decorrelated_df)} observations"
    )

    return decorrelated_df, truth_mapping


def generate_manifest(
    output_dir: Path,
    files: List[str],
    algorithm: str = "sha256",
) -> Dict[str, Any]:
    """
    Generate a manifest with checksums for all output files.

    Args:
        output_dir: Directory containing the files
        files: List of filenames to include in manifest
        algorithm: Hash algorithm to use

    Returns:
        Manifest dictionary with file checksums and metadata
    """
    manifest = {
        "version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
        "algorithm": algorithm,
        "files": {},
    }

    for filename in files:
        filepath = output_dir / filename
        if filepath.exists():
            manifest["files"][filename] = {
                "checksum": compute_file_checksum(filepath, algorithm),
                "size_bytes": filepath.stat().st_size,
            }
        else:
            logger.warning(f"File not found for manifest: {filepath}")

    return manifest


def export_dataset_for_udl(
    obs_df: pd.DataFrame,
    output_dir: Path,
    dataset_name: str,
    legacy_code: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    include_raw: bool = False,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Export a dataset to UDL-compatible format for benchmarking.

    Creates a directory structure with decorrelated observations,
    ground truth mapping, metadata, and integrity manifest.

    Output structure:
        {dataset_name}/
            observations.json    # Decorrelated observations
            truth.json          # Ground truth (track_id → satNo)
            metadata.json       # Dataset metadata
            manifest.json       # File checksums
            [raw_observations.json]  # Optional: Original data with IDs

    Args:
        obs_df: DataFrame of observations to export
        output_dir: Base output directory
        dataset_name: Name for the dataset (used as subdirectory name)
        legacy_code: 16-character legacy dataset code (optional)
        metadata: Additional metadata to include (optional)
        include_raw: If True, also export raw observations with IDs (for debugging)
        seed: Random seed for reproducible decorrelation

    Returns:
        Dictionary with export results including paths and statistics
    """
    # Create output directory
    dataset_dir = output_dir / dataset_name
    dataset_dir.mkdir(parents=True, exist_ok=True)

    export_results = {
        "dataset_name": dataset_name,
        "output_dir": str(dataset_dir),
        "legacy_code": legacy_code,
        "export_time": datetime.now(timezone.utc).isoformat() + "Z",
        "files": [],
        "statistics": {},
    }

    # Step 1: Decorrelate observations
    logger.info(f"Decorrelating observations for dataset: {dataset_name}")
    decorrelated_obs, truth_mapping = decorrelate_observations(obs_df, seed=seed)

    # Step 2: Prepare observations for export
    # Convert datetime columns to ISO format strings
    obs_export = decorrelated_obs.copy()
    for col in obs_export.columns:
        if pd.api.types.is_datetime64_any_dtype(obs_export[col]):
            obs_export[col] = obs_export[col].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Handle any remaining NaN values
    obs_export = obs_export.where(pd.notnull(obs_export), None)

    # Convert to records for JSON export
    observations_data = {
        "format_version": "1.0",
        "dataset_name": dataset_name,
        "legacy_code": legacy_code,
        "observation_count": len(obs_export),
        "track_count": obs_export["track_id"].nunique() if "track_id" in obs_export.columns else 0,
        "columns": list(obs_export.columns),
        "observations": obs_export.to_dict(orient="records"),
    }

    # Step 3: Export observations.json
    obs_path = dataset_dir / "observations.json"
    with open(obs_path, "w") as f:
        json.dump(observations_data, f, indent=2, default=str)
    export_results["files"].append("observations.json")
    logger.info(f"Exported observations to: {obs_path}")

    # Step 4: Export truth.json
    truth_data = {
        "format_version": "1.0",
        "dataset_name": dataset_name,
        "description": "Ground truth mapping from track_id to NORAD catalog number (satNo)",
        "track_count": len(truth_mapping),
        "mappings": truth_mapping.to_dict(orient="records"),
    }

    truth_path = dataset_dir / "truth.json"
    with open(truth_path, "w") as f:
        json.dump(truth_data, f, indent=2)
    export_results["files"].append("truth.json")
    logger.info(f"Exported truth mapping to: {truth_path}")

    # Step 5: Build and export metadata.json
    export_metadata = {
        "format_version": "1.0",
        "dataset_name": dataset_name,
        "legacy_code": legacy_code,
        "created_at": datetime.now(timezone.utc).isoformat() + "Z",
        "statistics": {
            "observation_count": len(obs_df),
            "track_count": len(truth_mapping),
            "columns": list(decorrelated_obs.columns),
        },
    }

    # Add legacy code breakdown if provided
    if legacy_code and len(legacy_code) == 16:
        export_metadata["legacy_code_breakdown"] = {
            "object_type": legacy_code[0],
            "target_percentage": legacy_code[1:3],
            "orbital_regime": legacy_code[3:6],
            "event": legacy_code[6:8],
            "sensor_type": legacy_code[8:10],
            "orbit_coverage": legacy_code[10],
            "track_gap": legacy_code[11],
            "observation_count_level": legacy_code[12],
            "object_count": legacy_code[13],
            "fitspan_days": legacy_code[14:16],
        }

    # Add custom metadata if provided
    if metadata:
        export_metadata["custom"] = metadata

    # Add time range if available
    time_cols = ["obTime", "observationTime", "epoch", "time"]
    for col in time_cols:
        if col in obs_df.columns:
            try:
                times = pd.to_datetime(obs_df[col])
                export_metadata["statistics"]["time_range"] = {
                    "start": times.min().isoformat(),
                    "end": times.max().isoformat(),
                    "duration_days": (times.max() - times.min()).total_seconds() / 86400,
                }
                break
            except Exception:
                pass

    metadata_path = dataset_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(export_metadata, f, indent=2, default=str)
    export_results["files"].append("metadata.json")
    logger.info(f"Exported metadata to: {metadata_path}")

    # Step 6: Optionally export raw observations (with IDs) for debugging
    if include_raw:
        raw_export = obs_df.copy()
        for col in raw_export.columns:
            if pd.api.types.is_datetime64_any_dtype(raw_export[col]):
                raw_export[col] = raw_export[col].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        raw_export = raw_export.where(pd.notnull(raw_export), None)

        raw_data = {
            "format_version": "1.0",
            "dataset_name": dataset_name,
            "note": "RAW DATA - Contains ground truth IDs. For debugging only.",
            "observation_count": len(raw_export),
            "columns": list(raw_export.columns),
            "observations": raw_export.to_dict(orient="records"),
        }

        raw_path = dataset_dir / "raw_observations.json"
        with open(raw_path, "w") as f:
            json.dump(raw_data, f, indent=2, default=str)
        export_results["files"].append("raw_observations.json")
        logger.info(f"Exported raw observations to: {raw_path}")

    # Step 7: Generate and export manifest
    manifest = generate_manifest(dataset_dir, export_results["files"])
    manifest["dataset_name"] = dataset_name
    manifest["legacy_code"] = legacy_code

    manifest_path = dataset_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    export_results["files"].append("manifest.json")
    logger.info(f"Exported manifest to: {manifest_path}")

    # Compile final statistics
    export_results["statistics"] = {
        "observation_count": len(obs_df),
        "decorrelated_observation_count": len(decorrelated_obs),
        "track_count": len(truth_mapping),
        "file_count": len(export_results["files"]),
        "total_size_bytes": sum(
            (dataset_dir / f).stat().st_size
            for f in export_results["files"]
            if (dataset_dir / f).exists()
        ),
    }

    logger.info(
        f"UDL export complete: {dataset_name} - "
        f"{export_results['statistics']['observation_count']} observations, "
        f"{export_results['statistics']['track_count']} tracks"
    )

    return export_results


def verify_udl_export(export_dir: Path) -> Dict[str, Any]:
    """
    Verify the integrity of a UDL export using the manifest.

    Args:
        export_dir: Path to the exported dataset directory

    Returns:
        Verification results with status and any errors
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "files_verified": [],
    }

    # Load manifest
    manifest_path = export_dir / "manifest.json"
    if not manifest_path.exists():
        results["valid"] = False
        results["errors"].append("Manifest file not found")
        return results

    with open(manifest_path) as f:
        manifest = json.load(f)

    algorithm = manifest.get("algorithm", "sha256")

    # Verify each file
    for filename, file_info in manifest.get("files", {}).items():
        filepath = export_dir / filename
        if not filepath.exists():
            results["valid"] = False
            results["errors"].append(f"File not found: {filename}")
            continue

        # Verify checksum
        actual_checksum = compute_file_checksum(filepath, algorithm)
        expected_checksum = file_info.get("checksum")

        if actual_checksum != expected_checksum:
            results["valid"] = False
            results["errors"].append(
                f"Checksum mismatch for {filename}: "
                f"expected {expected_checksum}, got {actual_checksum}"
            )
        else:
            results["files_verified"].append(filename)

        # Verify size
        actual_size = filepath.stat().st_size
        expected_size = file_info.get("size_bytes")
        if expected_size and actual_size != expected_size:
            results["warnings"].append(
                f"Size mismatch for {filename}: "
                f"expected {expected_size}, got {actual_size}"
            )

    logger.info(
        f"UDL export verification: {'PASSED' if results['valid'] else 'FAILED'} - "
        f"{len(results['files_verified'])} files verified"
    )

    return results


def load_udl_export(
    export_dir: Path,
    verify: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Load a UDL export for evaluation.

    Args:
        export_dir: Path to the exported dataset directory
        verify: If True, verify integrity before loading

    Returns:
        Tuple of (observations_df, truth_mapping_df, metadata)

    Raises:
        ValueError: If verification fails (when verify=True)
    """
    if verify:
        verification = verify_udl_export(export_dir)
        if not verification["valid"]:
            raise ValueError(
                f"UDL export verification failed: {verification['errors']}"
            )

    # Load observations
    obs_path = export_dir / "observations.json"
    with open(obs_path) as f:
        obs_data = json.load(f)
    observations_df = pd.DataFrame(obs_data["observations"])

    # Load truth mapping
    truth_path = export_dir / "truth.json"
    with open(truth_path) as f:
        truth_data = json.load(f)
    truth_mapping_df = pd.DataFrame(truth_data["mappings"])

    # Load metadata
    metadata_path = export_dir / "metadata.json"
    with open(metadata_path) as f:
        metadata = json.load(f)

    logger.info(
        f"Loaded UDL export: {len(observations_df)} observations, "
        f"{len(truth_mapping_df)} truth mappings"
    )

    return observations_df, truth_mapping_df, metadata
