"""
Model evaluation utilities for UCTP Lab ML module.

Computes clustering and propagation quality metrics against
ground-truth data.
"""

from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger


def evaluate_clustering_model(
    predictions: np.ndarray,
    ground_truth: np.ndarray,
) -> Dict[str, Any]:
    """
    Evaluate clustering predictions against ground truth labels.

    Args:
        predictions: Predicted cluster labels (N,).
        ground_truth: True cluster labels (N,).

    Returns:
        Dict with precision, recall, f1_score, adjusted_rand_index.
    """
    from sklearn.metrics import (
        adjusted_rand_score,
        homogeneity_completeness_v_measure,
    )

    # Filter out noise labels (-1) from ground truth for pairwise metrics
    mask = ground_truth >= 0
    if mask.sum() < 2:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "adjusted_rand_index": 0.0,
            "n_evaluated": int(mask.sum()),
        }

    pred_filtered = predictions[mask]
    gt_filtered = ground_truth[mask]

    ari = adjusted_rand_score(gt_filtered, pred_filtered)
    homo, comp, v_measure = homogeneity_completeness_v_measure(gt_filtered, pred_filtered)

    # Pairwise precision/recall
    n = len(gt_filtered)
    tp = fp = fn = 0
    for i in range(n):
        for j in range(i + 1, min(i + 100, n)):  # sample pairs for efficiency
            same_pred = pred_filtered[i] == pred_filtered[j]
            same_gt = gt_filtered[i] == gt_filtered[j]
            if same_pred and same_gt:
                tp += 1
            elif same_pred and not same_gt:
                fp += 1
            elif not same_pred and same_gt:
                fn += 1

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-10)

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "adjusted_rand_index": round(ari, 4),
        "homogeneity": round(homo, 4),
        "completeness": round(comp, 4),
        "v_measure": round(v_measure, 4),
        "n_evaluated": int(mask.sum()),
    }


def evaluate_propagation_model(
    predictions: np.ndarray,
    targets: np.ndarray,
    denorm_factors: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Evaluate propagation predictions against target states.

    Args:
        predictions: Predicted state vectors (N, 6).
        targets: True state vectors (N, 6).
        denorm_factors: Factors to denormalise values
            (default: [1e4, 1e4, 1e4, 10, 10, 10]).

    Returns:
        Dict with position_rms_km, velocity_rms_km_s, and per-component errors.
    """
    if denorm_factors is None:
        denorm_factors = np.array([1e4, 1e4, 1e4, 10.0, 10.0, 10.0])

    pred_real = predictions * denorm_factors
    tgt_real = targets * denorm_factors

    errors = pred_real - tgt_real

    pos_errors = errors[:, :3]
    vel_errors = errors[:, 3:]

    pos_rms = float(np.sqrt(np.mean(pos_errors ** 2)))
    vel_rms = float(np.sqrt(np.mean(vel_errors ** 2)))

    return {
        "position_rms_km": round(pos_rms, 4),
        "velocity_rms_km_s": round(vel_rms, 6),
        "mean_pos_error_km": round(float(np.mean(np.linalg.norm(pos_errors, axis=1))), 4),
        "mean_vel_error_km_s": round(float(np.mean(np.linalg.norm(vel_errors, axis=1))), 6),
        "max_pos_error_km": round(float(np.max(np.linalg.norm(pos_errors, axis=1))), 4),
        "n_samples": len(predictions),
    }
