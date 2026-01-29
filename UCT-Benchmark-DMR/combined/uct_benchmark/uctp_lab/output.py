"""
Output formatting for UCTP Lab pipeline results.

Formats pipeline results into the standard UCTP output JSON structure
that matches the evaluation pipeline expectations (orbitAssociation, binaryMetrics, stateMetrics).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger


def format_state_vector(
    id_state_vector: int,
    sourced_data: List[str],
    epoch: str,
    position_km: np.ndarray,
    velocity_km_s: np.ndarray,
    covariance: Optional[List[float]] = None,
    reference_frame: str = "J2000",
) -> Dict[str, Any]:
    """
    Format a single state vector for UCTP output.

    Args:
        id_state_vector: Sequential ID for this state vector.
        sourced_data: List of observation IDs that contributed.
        epoch: ISO-format epoch string.
        position_km: [x, y, z] position in km.
        velocity_km_s: [vx, vy, vz] velocity in km/s.
        covariance: 21-element upper-triangle covariance (optional).
        reference_frame: Reference frame name.

    Returns:
        Dictionary matching the UCTP output format.
    """
    # Default covariance if not provided (identity-scaled)
    if covariance is None:
        covariance = [1.0] * 21

    return {
        "idStateVector": id_state_vector,
        "sourcedData": sourced_data,
        "epoch": epoch,
        "xpos": float(position_km[0]),
        "ypos": float(position_km[1]),
        "zpos": float(position_km[2]),
        "xvel": float(velocity_km_s[0]),
        "yvel": float(velocity_km_s[1]),
        "zvel": float(velocity_km_s[2]),
        "cov": [float(c) for c in covariance],
        "uct": True,
        "referenceFrame": reference_frame,
    }


def build_output(
    clusters: List[Dict[str, Any]],
    reference_frame: str = "J2000",
) -> List[Dict[str, Any]]:
    """
    Build the full UCTP output from pipeline cluster results.

    Each cluster should contain:
    - "observation_ids": List[str] of observation IDs in the cluster
    - "state": np.ndarray [x,y,z,vx,vy,vz] in km, km/s
    - "epoch": str ISO timestamp
    - "covariance": Optional[List[float]] 21-element upper triangle

    Args:
        clusters: List of resolved cluster dictionaries.
        reference_frame: Reference frame for state vectors.

    Returns:
        List of state vector dictionaries in UCTP output format.
    """
    output = []
    for idx, cluster in enumerate(clusters):
        obs_ids = cluster.get("observation_ids", [])
        state = cluster.get("state")
        epoch = cluster.get("epoch", datetime.utcnow().isoformat())
        covariance = cluster.get("covariance")

        if state is None or len(state) < 6:
            logger.warning(f"Cluster {idx} has no valid state, skipping")
            continue

        state = np.asarray(state, dtype=float)
        output.append(format_state_vector(
            id_state_vector=idx,
            sourced_data=obs_ids,
            epoch=epoch,
            position_km=state[:3],
            velocity_km_s=state[3:6],
            covariance=covariance,
            reference_frame=reference_frame,
        ))

    logger.info(f"Built UCTP output with {len(output)} state vectors")
    return output


def save_output(output: List[Dict[str, Any]], file_path: str) -> str:
    """
    Save UCTP output to a JSON file.

    Args:
        output: List of state vector dictionaries.
        file_path: Path to save the JSON file.

    Returns:
        Absolute path to the saved file.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"Saved UCTP output to {path} ({len(output)} state vectors)")
    return str(path.resolve())
