# -*- coding: utf-8 -*-
"""
Created on Wed Jun 11 13:40:12 2025

@author: Gabriel Lundin (optimized by ChatGPT)
"""

from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy.stats import chi2

import uct_benchmark.settings as config
from uct_benchmark.api.apiIntegration import TLEToSV

# Column name constants
STATE_COLUMNS = ["xpos", "ypos", "zpos", "xvel", "yvel", "zvel"]
POSITION_COLUMNS = ["xpos", "ypos", "zpos"]
VELOCITY_COLUMNS = ["xvel", "yvel", "zvel"]


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
    referenceStates = ref_orbits[STATE_COLUMNS].values
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

    x_true = truth[STATE_COLUMNS].values
    x_est = estimation[STATE_COLUMNS].values
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

    x_true = truth[STATE_COLUMNS].values
    x_est = estimation[STATE_COLUMNS].values
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
        # Propagate reference to candidate epochs
        prop_ref = _propRef(ref, candidate, propagator)

        # Mahalanobis Distance and p-score
        MD = _compute_MD(prop_ref, candidate)
        stats["Mahalanobis Distance"] = MD
        stats["MD P-Score"] = 1 - chi2.cdf(MD, df=6)

        # Euclidean Error Norms
        delta = candidate[STATE_COLUMNS].values - prop_ref[STATE_COLUMNS].values
        stats["Total Error Norm"] = np.linalg.norm(delta, axis=1)

        delta = candidate[POSITION_COLUMNS].values - prop_ref[POSITION_COLUMNS].values
        stats["Position Error Norm"] = np.linalg.norm(delta, axis=1)

        delta = candidate[VELOCITY_COLUMNS].values - prop_ref[VELOCITY_COLUMNS].values
        stats["Velocity Error Norm"] = np.linalg.norm(delta, axis=1)

        # Bias — per-pair, per-dimension difference (no averaging)
        bias = candidate[STATE_COLUMNS].values - prop_ref[STATE_COLUMNS].values
        stats[[f"{col} Bias" for col in STATE_COLUMNS]] = bias
        stats["Total Bias"] = np.sum(bias, axis=1)

        # NEES and p-score
        NEES = _compute_NEES(ref, candidate)
        stats["NEES"] = NEES
        stats["NEES P-Score"] = 1 - chi2.cdf(NEES, df=6)

    return stats


# =============================================================================
# ADDITIONAL METRICS PER LOUIS'S SPECIFICATION
# =============================================================================


def calculate_state_metrics_single(
    true_state: np.ndarray,
    estimated_state: np.ndarray,
    covariance: np.ndarray = None,
) -> dict:
    """
    Calculate comprehensive state estimation metrics for a single comparison.

    Per Louis's Benchmarking Documentation:
    - L2 Norm (position and velocity)
    - Per-dimension bias
    - Mahalanobis Distance with p-score
    - NEES (Normalized Estimation Error Squared) with p-score

    Args:
        true_state: 6-element state vector [x, y, z, vx, vy, vz] in km and km/s
        estimated_state: 6-element estimated state vector
        covariance: 6x6 covariance matrix (required for Mahalanobis and NEES)

    Returns:
        Dict with all calculated metrics
    """
    error = estimated_state - true_state

    # Position and velocity errors
    pos_error = error[:3]
    vel_error = error[3:]

    # L2 Norms
    l2_position = np.linalg.norm(pos_error)
    l2_velocity = np.linalg.norm(vel_error)
    l2_total = np.linalg.norm(error)

    # Per-dimension bias
    bias = {
        "x_bias_km": error[0],
        "y_bias_km": error[1],
        "z_bias_km": error[2],
        "vx_bias_km_s": error[3],
        "vy_bias_km_s": error[4],
        "vz_bias_km_s": error[5],
    }

    metrics = {
        "l2_position_km": l2_position,
        "l2_velocity_km_s": l2_velocity,
        "l2_total": l2_total,
        **bias,
    }

    # Mahalanobis Distance and NEES (require covariance)
    if covariance is not None and covariance.shape == (6, 6):
        try:
            # Mahalanobis distance
            cov_inv = np.linalg.pinv(covariance)
            if not _is_psd(cov_inv):
                cov_inv = _safe_inverse_psd(covariance)

            mahal_sq = error.T @ cov_inv @ error
            mahal_dist = np.sqrt(mahal_sq)

            # P-score for Mahalanobis (chi-squared with 6 DOF)
            mahal_p_score = 1 - chi2.cdf(mahal_sq, df=6)

            # NEES (same as Mahalanobis squared for single estimate)
            nees = mahal_sq
            nees_p_score = 1 - chi2.cdf(nees, df=6)

            metrics.update({
                "mahalanobis_distance": mahal_dist,
                "mahalanobis_squared": mahal_sq,
                "mahalanobis_p_score": mahal_p_score,
                "nees": nees,
                "nees_p_score": nees_p_score,
            })
        except np.linalg.LinAlgError:
            # Covariance not invertible
            metrics.update({
                "mahalanobis_distance": np.nan,
                "mahalanobis_squared": np.nan,
                "mahalanobis_p_score": np.nan,
                "nees": np.nan,
                "nees_p_score": np.nan,
            })

    return metrics


def calculate_residual_metrics(
    observations: pd.DataFrame,
    predicted_positions: pd.DataFrame,
    ra_col: str = "ra",
    dec_col: str = "dec",
) -> dict:
    """
    Calculate observation residual metrics per Louis's specification.

    Uses unit-sphere great circle distance for residuals.
    - Accuracy mode: Residuals from TRUE position
    - Precision mode: Residuals from ESTIMATED position

    Args:
        observations: DataFrame with observed RA/Dec in degrees
        predicted_positions: DataFrame with predicted RA/Dec in degrees
        ra_col: Column name for Right Ascension
        dec_col: Column name for Declination

    Returns:
        Dict with residual statistics in arcseconds
    """
    if observations.empty or predicted_positions.empty:
        return {
            "residual_count": 0,
            "residual_mean_arcsec": np.nan,
            "residual_std_arcsec": np.nan,
            "residual_rms_arcsec": np.nan,
            "residual_median_arcsec": np.nan,
            "residual_max_arcsec": np.nan,
            "residual_min_arcsec": np.nan,
        }

    residuals = []

    n_samples = min(len(observations), len(predicted_positions))

    for i in range(n_samples):
        obs_ra = np.radians(observations.iloc[i][ra_col])
        obs_dec = np.radians(observations.iloc[i][dec_col])
        pred_ra = np.radians(predicted_positions.iloc[i][ra_col])
        pred_dec = np.radians(predicted_positions.iloc[i][dec_col])

        # Great circle distance on unit sphere (Haversine formula)
        delta_ra = pred_ra - obs_ra
        delta_dec = pred_dec - obs_dec

        a = (np.sin(delta_dec / 2) ** 2 +
             np.cos(obs_dec) * np.cos(pred_dec) * np.sin(delta_ra / 2) ** 2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        # Convert to arcseconds
        residual_arcsec = np.degrees(c) * 3600
        residuals.append(residual_arcsec)

    residuals = np.array(residuals)

    return {
        "residual_count": len(residuals),
        "residual_mean_arcsec": float(np.mean(residuals)),
        "residual_std_arcsec": float(np.std(residuals)),
        "residual_rms_arcsec": float(np.sqrt(np.mean(residuals ** 2))),
        "residual_median_arcsec": float(np.median(residuals)),
        "residual_max_arcsec": float(np.max(residuals)),
        "residual_min_arcsec": float(np.min(residuals)),
    }


def calculate_batch_nees(
    errors: np.ndarray,
    covariances: np.ndarray,
    confidence_level: float = 0.95,
) -> dict:
    """
    Calculate NEES statistics over a batch of estimates.

    Per Louis's specification, NEES should be evaluated in aggregate.
    For consistent estimator, average NEES should be approximately equal
    to the state dimension (6).

    Args:
        errors: (N, 6) array of state errors
        covariances: (N, 6, 6) array of covariance matrices
        confidence_level: Confidence level for consistency test (default 0.95)

    Returns:
        Dict with batch NEES statistics and consistency test results
    """
    n_samples = len(errors)
    nees_values = []

    for i in range(n_samples):
        try:
            cov = covariances[i]
            cov_inv = np.linalg.pinv(cov)
            if not _is_psd(cov_inv):
                cov_inv = _safe_inverse_psd(cov)
            nees = errors[i].T @ cov_inv @ errors[i]
            if not np.isnan(nees) and not np.isinf(nees):
                nees_values.append(nees)
        except (np.linalg.LinAlgError, ValueError):
            continue

    if len(nees_values) == 0:
        return {
            "average_nees": np.nan,
            "expected_nees": 6.0,
            "nees_std": np.nan,
            "nees_lower_bound": np.nan,
            "nees_upper_bound": np.nan,
            "is_consistent": False,
            "n_samples": 0,
            "n_valid": 0,
        }

    nees_values = np.array(nees_values)
    n_valid = len(nees_values)

    # Average NEES
    avg_nees = np.mean(nees_values)
    std_nees = np.std(nees_values)

    # Chi-squared consistency test
    # Under H0 (consistent estimator), sum(NEES) ~ chi2(6*N)
    # Average NEES should be approximately 6 (state dimension)
    alpha = 1 - confidence_level
    dof = 6 * n_valid

    # Bounds for average NEES
    lower_bound = chi2.ppf(alpha / 2, dof) / n_valid
    upper_bound = chi2.ppf(1 - alpha / 2, dof) / n_valid

    is_consistent = lower_bound <= avg_nees <= upper_bound

    return {
        "average_nees": float(avg_nees),
        "expected_nees": 6.0,
        "nees_std": float(std_nees),
        "nees_lower_bound": float(lower_bound),
        "nees_upper_bound": float(upper_bound),
        "is_consistent": bool(is_consistent),
        "confidence_level": confidence_level,
        "n_samples": n_samples,
        "n_valid": n_valid,
    }


def calculate_radial_in_track_cross_track_errors(
    true_state: np.ndarray,
    estimated_state: np.ndarray,
) -> dict:
    """
    Calculate errors in Radial-In-track-Cross-track (RIC) frame.

    Per Louis's specification, RIC frame errors are useful for
    understanding the nature of orbit determination errors.

    Args:
        true_state: True state [x, y, z, vx, vy, vz] in km and km/s
        estimated_state: Estimated state in same units

    Returns:
        Dict with RIC errors in km and km/s
    """
    # Position and velocity
    r_true = true_state[:3]
    v_true = true_state[3:6]

    r_est = estimated_state[:3]
    v_est = estimated_state[3:6]

    # Build RIC frame from true state
    # Radial: unit vector along position
    r_hat = r_true / np.linalg.norm(r_true)

    # Cross-track: normal to orbital plane
    h = np.cross(r_true, v_true)  # Angular momentum
    c_hat = h / np.linalg.norm(h)

    # In-track: completes right-handed system
    i_hat = np.cross(c_hat, r_hat)

    # Rotation matrix from ECI to RIC
    R_eci_to_ric = np.array([r_hat, i_hat, c_hat])

    # Position error in RIC
    pos_error_eci = r_est - r_true
    pos_error_ric = R_eci_to_ric @ pos_error_eci

    # Velocity error in RIC
    vel_error_eci = v_est - v_true
    vel_error_ric = R_eci_to_ric @ vel_error_eci

    return {
        "radial_error_km": float(pos_error_ric[0]),
        "in_track_error_km": float(pos_error_ric[1]),
        "cross_track_error_km": float(pos_error_ric[2]),
        "radial_vel_error_km_s": float(vel_error_ric[0]),
        "in_track_vel_error_km_s": float(vel_error_ric[1]),
        "cross_track_vel_error_km_s": float(vel_error_ric[2]),
        "total_ric_position_error_km": float(np.linalg.norm(pos_error_ric)),
        "total_ric_velocity_error_km_s": float(np.linalg.norm(vel_error_ric)),
    }


def calculate_comprehensive_state_metrics(
    true_states: np.ndarray,
    estimated_states: np.ndarray,
    covariances: np.ndarray = None,
) -> dict:
    """
    Calculate comprehensive statistics over multiple state comparisons.

    Args:
        true_states: (N, 6) array of true states
        estimated_states: (N, 6) array of estimated states
        covariances: (N, 6, 6) array of covariance matrices (optional)

    Returns:
        Dict with aggregate statistics
    """
    n_samples = len(true_states)

    if n_samples == 0:
        return {"n_samples": 0, "status": "no_samples"}

    # Calculate individual metrics
    pos_errors = []
    vel_errors = []
    total_errors = []
    ric_radial = []
    ric_in_track = []
    ric_cross_track = []

    for i in range(n_samples):
        error = estimated_states[i] - true_states[i]
        pos_errors.append(np.linalg.norm(error[:3]))
        vel_errors.append(np.linalg.norm(error[3:]))
        total_errors.append(np.linalg.norm(error))

        # RIC errors
        ric = calculate_radial_in_track_cross_track_errors(
            true_states[i], estimated_states[i]
        )
        ric_radial.append(ric["radial_error_km"])
        ric_in_track.append(ric["in_track_error_km"])
        ric_cross_track.append(ric["cross_track_error_km"])

    pos_errors = np.array(pos_errors)
    vel_errors = np.array(vel_errors)
    total_errors = np.array(total_errors)

    result = {
        "n_samples": n_samples,
        # Position error statistics
        "position_error_mean_km": float(np.mean(pos_errors)),
        "position_error_std_km": float(np.std(pos_errors)),
        "position_error_rms_km": float(np.sqrt(np.mean(pos_errors ** 2))),
        "position_error_median_km": float(np.median(pos_errors)),
        "position_error_max_km": float(np.max(pos_errors)),
        "position_error_min_km": float(np.min(pos_errors)),
        # Velocity error statistics
        "velocity_error_mean_km_s": float(np.mean(vel_errors)),
        "velocity_error_std_km_s": float(np.std(vel_errors)),
        "velocity_error_rms_km_s": float(np.sqrt(np.mean(vel_errors ** 2))),
        "velocity_error_median_km_s": float(np.median(vel_errors)),
        "velocity_error_max_km_s": float(np.max(vel_errors)),
        "velocity_error_min_km_s": float(np.min(vel_errors)),
        # RIC statistics
        "radial_error_mean_km": float(np.mean(ric_radial)),
        "radial_error_std_km": float(np.std(ric_radial)),
        "in_track_error_mean_km": float(np.mean(ric_in_track)),
        "in_track_error_std_km": float(np.std(ric_in_track)),
        "cross_track_error_mean_km": float(np.mean(ric_cross_track)),
        "cross_track_error_std_km": float(np.std(ric_cross_track)),
    }

    # Add NEES statistics if covariances provided
    if covariances is not None:
        errors = estimated_states - true_states
        nees_stats = calculate_batch_nees(errors, covariances)
        result["nees_statistics"] = nees_stats

    return result
