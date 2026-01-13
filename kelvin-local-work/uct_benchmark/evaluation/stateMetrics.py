# -*- coding: utf-8 -*-
"""
Created on Wed Jun 11 13:40:12 2025

@author: Gabriel Lundin (optimized by ChatGPT)
"""

from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy.stats import chi2

from uct_benchmark.api.apiIntegration import TLEToSV
import uct_benchmark.config as config


# --- Helper Functions ---
def _propagate_single(args):
    """Helper function to allow multiprocessing of state propagation"""

    state, cov, t_start, t_end, satPars, propagator = args
    # Number of monte carlo sample points
    N = config.monteCarloPoints
    return propagator(state, cov, t_start, t_end, N, satPars)


def _propagate_single_TLE(args):
    """Helper function to allow multiprocessing of TLE propagation"""

    line1, line2, t_end, propagator = args
    return propagator(line1, line2, t_end)


def _propRef(ref_orbits, cand_orbits, propagator):
    """
    Internal function to propagate reference orbits to candidate ones.
    Returns the propagated references.
    """

    # Extract relevant epochs and reference values
    candidateEpochs = pd.to_datetime(cand_orbits["epoch"].values)
    referenceEpochs = pd.to_datetime(ref_orbits["epoch"].values)
    state_cols = ["xpos", "ypos", "zpos", "xvel", "yvel", "zvel"]
    referenceStates = ref_orbits[state_cols].values
    referenceCovs = ref_orbits["cov_matrix"].values
    mass = ref_orbits["mass"].values
    area = ref_orbits["crossSection"].values
    drag = ref_orbits["dragCoeff"].values
    solar = ref_orbits["solarRadPressCoeff"].values

    # Prepare arguments for parallel execution
    args_list = [
        (
            referenceStates[j],
            referenceCovs[j],
            referenceEpochs[j],
            candidateEpochs[j],
            [mass[j], area[j], drag[j], solar[j]],
            propagator,
        )
        for j in range(len(ref_orbits))
    ]

    # Run propagation in parallel
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(_propagate_single, args_list))

    # Separate results
    propagatedStates, propagatedCovs = zip(*results)

    # Format into dataframe
    propagatedReference = pd.DataFrame(
        {
            "xpos": [vec[0] for vec in propagatedStates],
            "ypos": [vec[1] for vec in propagatedStates],
            "zpos": [vec[2] for vec in propagatedStates],
            "xvel": [vec[3] for vec in propagatedStates],
            "yvel": [vec[4] for vec in propagatedStates],
            "zvel": [vec[5] for vec in propagatedStates],
            "cov_matrix": propagatedCovs,
        }
    )
    return propagatedReference


def _propRef_TLE(ref_orbits, cand_orbits, propagator):
    """
    Internal function to propagate TLE reference orbits to candidate ones.
    Returns the propagated references.
    """

    # Extract relevant epochs and reference values
    candidate_epochs = pd.to_datetime([d["epoch"] for d in cand_orbits["elset"]])
    ref_line1 = ref_orbits["line1"].tolist()
    ref_line2 = ref_orbits["line2"].tolist()

    # Prepare arguments for parallel execution
    args_list = [
        (ref_line1[j], ref_line2[j], candidate_epochs[j], propagator)
        for j in range(len(ref_orbits))
    ]

    # Run propagation in parallel
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(_propagate_single_TLE, args_list))

    # Separate results
    prop_line1, prop_line2, prop_state = zip(*results)

    # Deal with list unwrapping
    if isinstance(prop_line1[0], list):
        prop_line1 = tuple(x[0] for x in prop_line1)
    if isinstance(prop_line2[0], list):
        prop_line2 = tuple(x[0] for x in prop_line2)
    if isinstance(prop_state[0], list) and len(prop_state[0]) == 1:
        prop_state = tuple(x[0] for x in prop_state)

    # Format into dataframe
    propagated_reference = pd.DataFrame(
        {
            "line1": prop_line1,
            "line2": prop_line2,
            "state": prop_state,
        }
    )
    return propagated_reference


def _compute_MD(truth, estimation):
    """
    Computes the Mahalanobis Distance for a set of state vectors.

    Args:
        truth (Pandas DataFrame): A dataframe of truth state vectors.
        estimation (Pandas DataFrame): A dataframe of estimated state vectors.
        Dataframes are assumed to be correlated and sorted in order, and have identical epochs for each pair.

    Returns:
        Numpy Array: List of **squared** Mahalanobis Distances keyed by index.

    Raises:
        ValueError: If truth and estimation have varying sizes.

    """

    # Error handling
    if truth.shape[0] != estimation.shape[0]:
        raise ValueError("Inputs must have same number of vectors.")

    state_cols = ["xpos", "ypos", "zpos", "xvel", "yvel", "zvel"]
    x_true = truth[state_cols].values
    x_est = estimation[state_cols].values
    MD = np.zeros(len(x_true))

    # Compute MD
    for i in range(len(x_true)):
        delta = x_est[i] - x_true[i]
        cov = truth["cov_matrix"].iloc[i] + estimation["cov_matrix"].iloc[i]
        try:
            cov_inv = np.linalg.pinv(cov)
            if not _is_psd(cov_inv):
                cov_inv = _safe_inverse_psd(cov)
            MD[i] = delta.T @ cov_inv @ delta
        except np.linalg.LinAlgError:
            MD[i] = np.nan
    return MD


def _compute_NEES(truth, estimation):
    """
    Computes the Normalized Estimation Error Squared for a set of state vectors.

    Args:
        truth (Pandas DataFrame): A dataframe of truth state vectors.
        estimation (Pandas DataFrame): A dataframe of estimated state vectors.
        Dataframes are assumed to be correlated and sorted in order, and have identical epochs for each pair.

    Returns:
        Numpy Array: List of Normalized Estimation Error Squared keyed by index.

    Raises:
        ValueError: If truth and estimation have varying sizes.

    """

    # Error handling
    if truth.shape[0] != estimation.shape[0]:
        raise ValueError("Inputs must have same number of vectors.")

    state_cols = ["xpos", "ypos", "zpos", "xvel", "yvel", "zvel"]
    x_true = truth[state_cols].values
    x_est = estimation[state_cols].values
    NEES = np.zeros(len(x_true))

    # Compute NEES
    for i in range(len(x_true)):
        delta = x_est[i] - x_true[i]
        cov = estimation["cov_matrix"].iloc[i]
        try:
            cov_inv = np.linalg.pinv(cov)
            if not _is_psd(cov_inv):
                cov_inv = _safe_inverse_psd(cov)
            NEES[i] = delta.T @ cov_inv @ delta
        except np.linalg.LinAlgError:
            NEES[i] = np.nan
    return NEES


def _safe_inverse_psd(cov, tol=1e-10):
    # Helper function to perform near-singular inverses
    cov_inv = np.linalg.pinv(cov)
    cov_inv = (cov_inv + cov_inv.T) / 2  # enforce symmetry
    eigvals, eigvecs = np.linalg.eigh(cov_inv)
    eigvals_clipped = np.clip(eigvals, tol, None)
    return eigvecs @ np.diag(eigvals_clipped) @ eigvecs.T


def _is_psd(matrix):
    return np.all(np.linalg.eigvalsh(matrix) >= -1e-10)


def stateMetrics(ref, candidate, propagator, elset_mode=False):
    """
    Computes various useful statistical scores for orbit residuals.

    Args:
        ref (Pandas DataFrame): A dataframe of reference orbits.
        candidate (Pandas DataFrame): A dataframe of candidate orbits.
        Dataframes are assumed to be correlated by satellite number ('satNo' column) and equal length.
        propagator (function): An orbit propagator to propagate orbits.
            SV Inputs: 6D state, 6x6 cov matrix, initial time, final time, satellite parameters (list of [mass,area,dragCoeff,solarRadPresCoeff])
            SV Outputs: 6D state, 6x6 cov matrix
            TLE Inputs: TLE line 1, TLE line 2, final time
            TLE Outputs: TLE line 1, TLE line 2, 6D state
        elset_mode (bool): If True, takes in TLE inputs. Defaults to False/state vector mode.

    Returns:
        stats (Pandas DataFrame): Various statistical results for each orbit.

    Raises:
        ValueError: If ref and candidate have varying sizes.

    """
    # Ensure the reference and candidate datasets have the same number of orbits
    if ref.shape[0] < candidate.shape[0]:
        raise ValueError("Inputs must have same number of vectors.")
    elif ref.shape[0] > candidate.shape[0]:
        ref = ref[ref["satNo"].isin(candidate["satNo"])]

    point_size = ref.shape[0]
    stats = pd.DataFrame()
    stats["satNo"] = ref["satNo"].copy()

    if elset_mode:
        # Propagate reference to candidate epochs
        prop_ref = _propRef_TLE(ref, candidate, propagator)

        prop_states = prop_ref["state"].values

        # Obtain candidate state vectors from TLEs
        cand_states = [
            TLEToSV(l1, l2)
            for l1, l2 in zip(candidate["line1"].tolist(), candidate["line2"].tolist())
        ]

        # Euclidean Error Norms
        delta = np.vstack(cand_states) - np.vstack(prop_states)
        stats["Total Error Norm"] = np.linalg.norm(delta, axis=1)
        pos_delta = delta[:, :3]
        stats["Position Error Norm"] = np.linalg.norm(pos_delta, axis=1)
        vel_delta = delta[:, 3:]
        stats["Velocity Error Norm"] = np.linalg.norm(vel_delta, axis=1)
    else:
        state_cols = ["xpos", "ypos", "zpos", "xvel", "yvel", "zvel"]
        pos_cols = ["xpos", "ypos", "zpos"]
        vel_cols = ["xvel", "yvel", "zvel"]

        # Propagate reference to candidate epochs
        prop_ref = _propRef(ref, candidate, propagator)

        # Mahalanobis Distance and p-score
        MD = _compute_MD(prop_ref, candidate)
        stats["Mahalanobis Distance"] = MD
        stats["MD P-Score"] = 1 - chi2.cdf(MD, df=6)

        # Euclidean Error Norms
        delta = candidate[state_cols].values - prop_ref[state_cols].values
        stats["Total Error Norm"] = np.linalg.norm(delta, axis=1)

        delta = candidate[pos_cols].values - prop_ref[pos_cols].values
        stats["Position Error Norm"] = np.linalg.norm(delta, axis=1)

        delta = candidate[vel_cols].values - prop_ref[vel_cols].values
        stats["Velocity Error Norm"] = np.linalg.norm(delta, axis=1)

        # Bias
        bias = candidate[state_cols].values - prop_ref[state_cols].values
        stats[[f"{col} Bias" for col in state_cols]] = bias / point_size
        stats["Total Bias"] = np.sum(bias / point_size, axis=1)

        # NEES and p-score
        NEES = _compute_NEES(ref, candidate)
        stats["NEES"] = NEES
        stats["NEES P-Score"] = 1 - chi2.cdf(NEES, df=6)

    return stats
