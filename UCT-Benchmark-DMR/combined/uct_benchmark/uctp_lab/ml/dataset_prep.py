"""
Dataset preparation utilities for ML training in UCTP Lab.

Converts observation DataFrames and pipeline run outputs into
feature tensors suitable for training clustering or propagation
neural networks.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


def prepare_clustering_features(
    observations: pd.DataFrame,
    labels: Optional[Dict[int, List[str]]] = None,
    max_seq_len: int = 256,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Build feature matrix for clustering ML model.

    Each observation becomes a row with features:
        [ra, dec, unit_x, unit_y, unit_z, time_norm, angular_rate]

    Args:
        observations: DataFrame with [id, ob_time, ra, declination].
        labels: Optional ground-truth cluster labels (cluster_id -> list of obs IDs).
        max_seq_len: Truncate/pad to this length.

    Returns:
        (features, labels_array)
        features shape: (N, 7)
        labels_array shape: (N,) or None
    """
    obs = observations.sort_values("ob_time").reset_index(drop=True)
    n = min(len(obs), max_seq_len)

    features = np.zeros((n, 7), dtype=np.float32)

    for i in range(n):
        row = obs.iloc[i]
        ra = float(row["ra"])
        dec = float(row["declination"])

        ra_rad = np.deg2rad(ra)
        dec_rad = np.deg2rad(dec)
        ux = np.cos(dec_rad) * np.cos(ra_rad)
        uy = np.cos(dec_rad) * np.sin(ra_rad)
        uz = np.sin(dec_rad)

        features[i, 0] = ra / 360.0
        features[i, 1] = (dec + 90.0) / 180.0
        features[i, 2] = ux
        features[i, 3] = uy
        features[i, 4] = uz

    # Normalised time
    times = pd.to_datetime(obs.iloc[:n]["ob_time"])
    if len(times) > 1:
        t0 = times.iloc[0]
        t_sec = np.array([(t - t0).total_seconds() for t in times])
        t_range = t_sec.max() - t_sec.min()
        if t_range > 0:
            features[:, 5] = (t_sec - t_sec.min()) / t_range
    # Angular rate (finite difference)
    for i in range(1, n):
        dt = features[i, 5] - features[i - 1, 5]
        if dt > 0:
            dra = features[i, 0] - features[i - 1, 0]
            ddec = features[i, 1] - features[i - 1, 1]
            features[i, 6] = np.sqrt(dra ** 2 + ddec ** 2) / dt

    labels_array = None
    if labels is not None:
        id_to_label = {}
        for cluster_id, obs_ids in labels.items():
            for oid in obs_ids:
                id_to_label[oid] = cluster_id

        labels_array = np.full(n, -1, dtype=np.int64)
        for i in range(n):
            oid = obs.iloc[i]["id"]
            if oid in id_to_label:
                labels_array[i] = id_to_label[oid]

    return features, labels_array


def prepare_propagation_features(
    states: List[Dict],
    window_size: int = 10,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build input/target pairs for a propagation ML model.

    Given a sequence of state vectors, create sliding windows
    where the model predicts the next state from the previous
    window_size states.

    Args:
        states: List of dicts with 'state' (6-vector) and 'epoch'.
        window_size: Number of input states per sample.

    Returns:
        (inputs, targets)
        inputs shape: (N, window_size, 6)
        targets shape: (N, 6)
    """
    if len(states) < window_size + 1:
        logger.warning(
            f"Need at least {window_size + 1} states, got {len(states)}"
        )
        return np.zeros((0, window_size, 6)), np.zeros((0, 6))

    all_states = np.array([s["state"] for s in states], dtype=np.float32)

    # Normalise: position by 10000 km, velocity by 10 km/s
    norm = np.array([1e4, 1e4, 1e4, 10.0, 10.0, 10.0], dtype=np.float32)
    all_states = all_states / norm

    n_samples = len(all_states) - window_size
    inputs = np.zeros((n_samples, window_size, 6), dtype=np.float32)
    targets = np.zeros((n_samples, 6), dtype=np.float32)

    for i in range(n_samples):
        inputs[i] = all_states[i : i + window_size]
        targets[i] = all_states[i + window_size]

    return inputs, targets


def train_test_split_obs(
    observations: pd.DataFrame,
    test_fraction: float = 0.2,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split observations temporally into train/test sets."""
    obs = observations.sort_values("ob_time").reset_index(drop=True)
    split_idx = int(len(obs) * (1 - test_fraction))
    return obs.iloc[:split_idx].copy(), obs.iloc[split_idx:].copy()
