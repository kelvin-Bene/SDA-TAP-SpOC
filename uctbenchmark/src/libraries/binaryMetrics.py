# -*- coding: utf-8 -*-
"""
Created on Thu Jun 12 2025

@author: Lucan Kieser & Cameron Smith

updated on 2025-07-31
by Binyamin Stivi
"""

import pandas as pd
import urllib3
from sklearn.metrics import (
    accuracy_score,
    cohen_kappa_score,
    matthews_corrcoef,
    balanced_accuracy_score,
    f1_score,
    classification_report,
    recall_score
)
import ast
urllib3.disable_warnings()


def binaryMetrics(ref_obs, associated_orbits):
    """
    Compute binary classification metrics comparing true satellite associations with predicted ones.

    Parameters:
    ----------
    ref_obs : pd.DataFrame
        DataFrame containing reference observations with at least:
            - 'id': unique observation identifier
            - 'satNo': true satellite number (ground truth)

    associated_orbits : pd.DataFrame
        DataFrame containing predicted associations with at least:
            - 'satNo': predicted satellite number
            - 'sourcedData': list of observation IDs associated with that satellite

    Returns:
    -------
    pd.DataFrame
        A single-row DataFrame with binary classification metrics:
            - TotalObs
            - TotalCorrelated
            - TruePositives
            - FalsePositives
            - TrueNegatives (always 0; placeholder)
            - FalseNegatives
            - Accuracy
            - BalancedAccuracy
            - CohenKappa
            - MatthewsCorrCoef
            - F1Score
            - Sensitivity
            - Specificity
    """
    # Extract reference IDs and satellite numbers
    refPruned = ref_obs[['id', 'satNo']].copy()

    # --- Build list of (observation ID, predicted satNo) pairs ---
    obs_to_sat = []

    for _, row in associated_orbits.iterrows():
        satNo = row['satNo']
        for obs_id in row['sourcedData']:
            # Each observation ID is associated with this predicted satellite number
            obs_to_sat.append({'id': obs_id, 'satNo': satNo})

    # Create DataFrame from the (id, satNo) candidate associations
    ObsSatCandidates = pd.DataFrame(obs_to_sat)

    # --- Join predicted satNo with the true satNo from the reference ---
    merged = pd.merge(refPruned, ObsSatCandidates, on='id', how='left', suffixes=('_true', '_pred'))

    # Determine if the predicted satNo matches the true satNo for each observation
    merged['match'] = merged['satNo_true'] == merged['satNo_pred']

    # --- Compute binary classification counts ---
    total_obs = len(refPruned)                            # Total number of observations
    total_correlated = merged['satNo_pred'].notna().sum() # Number of observations with predictions
    true_positives = merged['match'].sum()                # Correctly predicted associations
    false_positives = total_correlated - true_positives   # Incorrect associations (wrong satNo)
    false_negatives = total_obs - total_correlated        # Observations with no predicted match
    true_negatives = 0                                    # Placeholder; not meaningful in this context due to one-sided matching logic


    # Prepare binary class vectors for metrics
    y_true = merged['match'].astype(int)
    y_pred = merged['satNo_pred'].notna().astype(int)

    # --- Compute standard classification metrics ---
    metrics_dict = {
        'TotalObs': [total_obs],
        'TotalCorrelated': [total_correlated],
        'TruePositives': [int(true_positives)],
        'FalsePositives': [int(false_positives)],
        'TrueNegatives': [true_negatives],
        'FalseNegatives': [int(false_negatives)],
        'Accuracy': [accuracy_score(y_true, y_pred)],
        'BalancedAccuracy': [balanced_accuracy_score(y_true, y_pred)],
        'CohenKappa': [cohen_kappa_score(y_true, y_pred)],
        'MatthewsCorrCoef': [matthews_corrcoef(y_true, y_pred)],
        'F1Score': [f1_score(y_true, y_pred, zero_division=0)],
        'Sensitivity': [recall_score(y_true, y_pred, zero_division=0)],
        'Specifcity': [recall_score(y_true, y_pred, pos_label=0)]

    }

    return pd.DataFrame(metrics_dict)
