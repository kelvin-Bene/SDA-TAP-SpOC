# -*- coding: utf-8 -*-
"""
Created on Thu Jun 12 2025

@author: Lucan Kieser & Cameron Smith

updated on 2025-07-31
by Binyamin Stivi

updated on 2026-01
True Negatives support per Louis's Benchmarking Documentation

Per Louis's documentation:
- TP: Observation correctly matched to reference satellite
- TN: Non-reference observation correctly NOT matched
- FP: Observation incorrectly matched to wrong satellite
- FN: Reference observation not matched

True Negatives require **non-reference satellite observations** in the dataset.
These are observations that the algorithm should NOT match to any candidate orbit.
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    cohen_kappa_score,
    f1_score,
    matthews_corrcoef,
    recall_score,
)


def binaryMetrics(
    ref_obs: pd.DataFrame,
    associated_orbits: pd.DataFrame,
    non_ref_observations: Optional[pd.DataFrame] = None,
    reference_satellites: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Compute binary classification metrics comparing true satellite associations with predicted ones.

    Per Louis's Benchmarking Documentation:
    - True Positive (TP): Observation correctly matched to reference satellite
    - True Negative (TN): Non-reference observation correctly NOT matched
    - False Positive (FP): Observation incorrectly matched to wrong satellite
    - False Negative (FN): Reference observation not matched

    Parameters:
    ----------
    ref_obs : pd.DataFrame
        DataFrame containing reference observations with at least:
            - 'id': unique observation identifier
            - 'satNo': true satellite number (ground truth)

    associated_orbits : pd.DataFrame
        DataFrame containing predicted associations with at least:
            - 'satNo': predicted satellite number
            - 'grouped_ops': list of observation IDs associated with that satellite
              (legacy alias 'sourcedData' is also accepted for backwards compatibility)

    non_ref_observations : pd.DataFrame, optional
        DataFrame containing non-reference observations (from satellites NOT in reference set).
        Used for True Negative calculation. Must have:
            - 'id': unique observation identifier
            - 'source_norad_id': the actual satellite (for ground truth verification)
        If None, TN=0 (backwards compatible behavior).

    reference_satellites : List[int], optional
        List of NORAD IDs that are in the reference set. Used to verify that
        non-ref observations are truly non-reference. If None, inferred from ref_obs.

    Returns:
    -------
    pd.DataFrame
        A single-row DataFrame with binary classification metrics:
            - TotalObs: Total reference observations
            - TotalCorrelated: Reference observations with predictions
            - TruePositives: Correctly matched reference observations
            - FalsePositives: Incorrectly matched observations (wrong satNo)
            - TrueNegatives: Non-ref observations correctly NOT matched
            - FalseNegatives: Reference observations not matched
            - Accuracy: (TP+TN)/(TP+TN+FP+FN)
            - BalancedAccuracy: sklearn balanced_accuracy_score
            - CohenKappa: Cohen's kappa coefficient
            - MatthewsCorrCoef: Matthews correlation coefficient
            - F1Score: Harmonic mean of precision and recall
            - Sensitivity: TP/(TP+FN) aka Recall
            - Specificity: TN/(TN+FP)
            - Precision: TP/(TP+FP)
            - NonRefObsCount: Number of non-reference observations
            - NonRefMatched: Non-ref observations incorrectly matched (should be 0)
    """
    # Extract reference IDs and satellite numbers
    refPruned = ref_obs[["id", "satNo"]].copy()

    # Infer reference satellites if not provided
    if reference_satellites is None:
        reference_satellites = ref_obs["satNo"].unique().tolist()
    reference_satellite_set = set(reference_satellites)

    # --- Build list of (observation ID, predicted satNo) pairs ---
    obs_to_sat = []

    # Determine the column name for grouped observation IDs
    # Accept both 'grouped_ops' (canonical) and 'sourcedData' (legacy)
    _grouped_col = "grouped_ops" if "grouped_ops" in associated_orbits.columns else "sourcedData"

    for _, row in associated_orbits.iterrows():
        satNo = row["satNo"]
        for obs_id in row[_grouped_col]:
            # Each observation ID is associated with this predicted satellite number
            obs_to_sat.append({"id": obs_id, "satNo": satNo})

    # Create DataFrame from the (id, satNo) candidate associations
    if obs_to_sat:
        ObsSatCandidates = pd.DataFrame(obs_to_sat)
    else:
        # Handle empty predictions case
        ObsSatCandidates = pd.DataFrame(columns=["id", "satNo"])

    # Get set of all matched observation IDs
    matched_obs_ids = set(ObsSatCandidates["id"].unique()) if not ObsSatCandidates.empty else set()

    # --- Join predicted satNo with the true satNo from the reference ---
    merged = pd.merge(refPruned, ObsSatCandidates, on="id", how="left", suffixes=("_true", "_pred"))

    # Determine if the predicted satNo matches the true satNo for each observation
    merged["match"] = merged["satNo_true"] == merged["satNo_pred"]

    # --- Compute binary classification counts for REFERENCE observations ---
    total_obs = len(refPruned)  # Total number of reference observations
    total_correlated = merged["satNo_pred"].notna().sum()  # Reference obs with predictions
    true_positives = merged["match"].sum()  # Correctly predicted associations
    false_positives = total_correlated - true_positives  # Incorrect associations (wrong satNo)
    false_negatives = total_obs - total_correlated  # Reference obs with no predicted match

    # --- Compute True Negatives from NON-REFERENCE observations ---
    true_negatives = 0
    non_ref_obs_count = 0
    non_ref_matched = 0

    if non_ref_observations is not None and not non_ref_observations.empty:
        # Count non-reference observations
        non_ref_obs_count = len(non_ref_observations)

        # Check which non-ref observations were incorrectly matched
        # An incorrect match = the algorithm assigned the observation to some satellite
        non_ref_ids = set(non_ref_observations["id"].unique())

        # Count how many non-ref observations were matched (this is bad - algorithm shouldn't match them)
        non_ref_matched = len(non_ref_ids & matched_obs_ids)

        # True Negatives = non-ref observations that the algorithm correctly did NOT match
        true_negatives = non_ref_obs_count - non_ref_matched

        # Also add to false_positives: non-ref observations matched to reference satellites
        # (These are observations the algorithm thought belonged to a reference satellite but didn't)
        if non_ref_matched > 0:
            # Check if they were matched to reference satellites
            non_ref_matched_to_ref = 0
            for obs_id in (non_ref_ids & matched_obs_ids):
                matched_sat = ObsSatCandidates[ObsSatCandidates["id"] == obs_id]["satNo"].iloc[0]
                if matched_sat in reference_satellite_set:
                    non_ref_matched_to_ref += 1
            # Add these to false positives
            false_positives += non_ref_matched_to_ref

    # Build binary class vectors from the confusion matrix counts so that
    # sklearn metrics are mathematically consistent with the manual ones.
    # Previous code derived y_true/y_pred from different columns of `merged`,
    # producing semantically mismatched vectors (e.g. FN mapped to sklearn-TN).
    tp = int(true_positives)
    fp = int(false_positives)
    tn = int(true_negatives)
    fn = int(false_negatives)
    y_true = [1] * tp + [1] * fn + [0] * fp + [0] * tn
    y_pred = [1] * tp + [0] * fn + [1] * fp + [0] * tn

    # --- Compute metrics with True Negatives ---
    # Custom accuracy including TN: (TP+TN)/(TP+TN+FP+FN)
    total_count = true_positives + true_negatives + false_positives + false_negatives
    custom_accuracy = (true_positives + true_negatives) / total_count if total_count > 0 else 0.0

    # Specificity: TN/(TN+FP)
    specificity_denom = true_negatives + false_positives
    custom_specificity = true_negatives / specificity_denom if specificity_denom > 0 else 0.0

    # Precision: TP/(TP+FP)
    precision_denom = true_positives + false_positives
    precision = true_positives / precision_denom if precision_denom > 0 else 0.0

    # --- Compute standard classification metrics ---
    metrics_dict = {
        "TotalObs": [total_obs],
        "TotalCorrelated": [int(total_correlated)],
        "TruePositives": [int(true_positives)],
        "FalsePositives": [int(false_positives)],
        "TrueNegatives": [int(true_negatives)],
        "FalseNegatives": [int(false_negatives)],
        "Accuracy": [custom_accuracy],  # Now includes TN
        "BalancedAccuracy": [balanced_accuracy_score(y_true, y_pred) if len(y_true) > 0 else 0.0],
        "CohenKappa": [cohen_kappa_score(y_true, y_pred) if len(y_true) > 1 else 0.0],
        "MatthewsCorrCoef": [matthews_corrcoef(y_true, y_pred) if len(y_true) > 1 else 0.0],
        "F1Score": [f1_score(y_true, y_pred, zero_division=0)],
        "Sensitivity": [recall_score(y_true, y_pred, zero_division=0)],
        "Specificity": [custom_specificity],  # Now uses TN
        "Precision": [precision],
        "NonRefObsCount": [non_ref_obs_count],
        "NonRefMatched": [non_ref_matched],
    }

    return pd.DataFrame(metrics_dict)


def calculate_binary_metrics(
    matches: List[Dict[str, Any]],
    reference_satellites: List[int],
    total_observations: int,
    non_ref_observations: Optional[List[Dict[str, Any]]] = None,
    algorithm_non_ref_matches: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Calculate binary classification metrics from match results.

    This is an alternative interface for calculating metrics when data
    is in dictionary/list format rather than DataFrames.

    Per Louis's Benchmarking Documentation:
    - True Positive (TP): Observation correctly matched to reference satellite
    - True Negative (TN): Non-reference observation correctly NOT matched
    - False Positive (FP): Observation incorrectly matched to wrong satellite
    - False Negative (FN): Reference observation not matched

    Args:
        matches: List of match dictionaries with 'obs_id', 'true_sat', 'pred_sat'
        reference_satellites: NORAD IDs of reference satellites
        total_observations: Total reference satellite observations
        non_ref_observations: Observations from non-reference satellites (for TN)
        algorithm_non_ref_matches: Algorithm's matches to non-reference obs

    Returns:
        Dict with all binary metrics

    True Negative calculation:
        TN = non_ref_observations that algorithm correctly did NOT match
           = len(non_ref_observations) - len(algorithm_non_ref_matches)
    """
    reference_set = set(reference_satellites)

    # Count TP, FP from matches
    true_positives = 0
    false_positives = 0

    for match in matches:
        true_sat = match.get("true_sat")
        pred_sat = match.get("pred_sat")

        if true_sat == pred_sat and true_sat in reference_set:
            true_positives += 1
        elif pred_sat is not None:
            false_positives += 1

    # False Negatives = observations not matched
    matched_count = len([m for m in matches if m.get("pred_sat") is not None])
    false_negatives = total_observations - matched_count

    # True Negatives from non-reference observations
    if non_ref_observations is not None:
        non_ref_count = len(non_ref_observations)
        incorrectly_matched = len(algorithm_non_ref_matches) if algorithm_non_ref_matches else 0
        true_negatives = non_ref_count - incorrectly_matched
    else:
        true_negatives = 0
        non_ref_count = 0
        incorrectly_matched = 0

    # Calculate derived metrics
    total = true_positives + true_negatives + false_positives + false_negatives

    accuracy = (true_positives + true_negatives) / total if total > 0 else 0.0

    precision_denom = true_positives + false_positives
    precision = true_positives / precision_denom if precision_denom > 0 else 0.0

    recall_denom = true_positives + false_negatives
    recall = true_positives / recall_denom if recall_denom > 0 else 0.0

    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    specificity_denom = true_negatives + false_positives
    specificity = true_negatives / specificity_denom if specificity_denom > 0 else 0.0

    return {
        "true_positives": true_positives,
        "true_negatives": true_negatives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "specificity": specificity,
        "non_ref_observation_count": non_ref_count,
        "non_ref_incorrectly_matched": incorrectly_matched,
    }
