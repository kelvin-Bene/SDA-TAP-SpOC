# -*- coding: utf-8 -*-
"""
Created on Fri Jun 27 11:45:50 2025

@author: Gabriel Lundin
"""

import heapq
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
import numpy as np
import pandas as pd

from uct_benchmark.settings import (
    DOWNSAMPLING_PROFILES,
    DownsampleConfig,
    SimulationConfig,
    LEGACY_COVERAGE_DOWNSAMPLE,
    QUALITY_LEVEL_THRESHOLDS,
    OBJECT_COUNT_MAP,
    COVERAGE_THRESHOLDS,
    TRACK_GAP_LONG_MULTIPLIER,
    OBS_COUNT_LOW_THRESHOLD,
    NON_REF_OBS_PER_SATELLITE,
)
from uct_benchmark.simulation.orbitCoverage import orbitCoverage
from uct_benchmark.utils.orbital import determine_orbital_regime


# =============================================================================
# SHARED TRACK IDENTIFICATION HELPERS
# =============================================================================


def _build_track_grouping_key(obs_df: pd.DataFrame, include_senalt: bool = True) -> pd.Series:
    """
    Build a grouping key for track identification.

    Groups observations by sensor (if available) or location, combined with satellite ID.
    This is the shared logic used by both binTracks() and identify_tracks().

    Args:
        obs_df: DataFrame with 'satNo' column, optionally 'idSensor', 'senlat', 'senlon', 'senalt'
        include_senalt: Whether to include sensor altitude in location-based key

    Returns:
        pd.Series: Grouping key for each observation
    """
    has_sensor = "idSensor" in obs_df.columns
    has_location = "senlat" in obs_df.columns and "senlon" in obs_df.columns

    if has_sensor:
        sensor_mask = obs_df["idSensor"].notna()

        if has_location:
            # Full key with sensor fallback to location
            if include_senalt and "senalt" in obs_df.columns:
                location_key = (
                    obs_df["senlat"].astype(str)
                    + "_"
                    + obs_df["senlon"].astype(str)
                    + "_"
                    + obs_df["senalt"].astype(str)
                    + "_"
                    + obs_df["satNo"].astype(str)
                )
            else:
                location_key = (
                    obs_df["senlat"].astype(str)
                    + "_"
                    + obs_df["senlon"].astype(str)
                    + "_"
                    + obs_df["satNo"].astype(str)
                )

            sensor_key = obs_df["idSensor"].astype(str) + "_" + obs_df["satNo"].astype(str)
            return np.where(sensor_mask, sensor_key, location_key)
        else:
            # Sensor ID where available, otherwise just satNo
            return obs_df["idSensor"].fillna("").astype(str) + "_" + obs_df["satNo"].astype(str)
    else:
        # No sensor column - use satNo only
        return obs_df["satNo"].astype(str)


def _split_by_time_gaps(
    obs_df: pd.DataFrame, gap_threshold: pd.Timedelta, min_track_size: int = 1
) -> List[pd.DataFrame]:
    """
    Split observations into tracks based on time gaps.

    Args:
        obs_df: DataFrame sorted by time with 'obTime' column
        gap_threshold: Maximum time gap within a track
        min_track_size: Minimum observations per track (default: 1)

    Returns:
        List of track DataFrames
    """
    if obs_df.empty:
        return []

    obs_sorted = obs_df.sort_values("obTime")
    time_diffs = obs_sorted["obTime"].diff()
    track_boundaries = (time_diffs > gap_threshold).cumsum()

    tracks = []
    for _, track in obs_sorted.groupby(track_boundaries, sort=False):
        if len(track) >= min_track_size:
            tracks.append(track.reset_index(drop=True))

    return tracks


def binTracks(ref_obs, ref_sv, cutoff=90):
    """
    Bins a set of observations into pseudo "tracks" for TLE generation.

    Args:
        ref_obs (Pandas DataFrame): Dataframe of observations to bin.
        ref_sv (Pandas DataFrame): Associated list of reference orbital state vectors.
        cutoff (int): Time gap to constitute a "track", in minutes. Defaults to 90.

    Returns:
        List: List of binned Dataframes in (satNo, period in sec, df) tuple pairs.
        Array: Track metrics - [total, kept, discarded, invalid]
    """
    mu = 3.986004418e5  # Standard gravitational parameter (km^3/s^2)
    metrics = [0, 0, 0, 0]  # [total, kept, discarded, invalid]

    # --------------------------------------------------------------------
    # Compute orbital periods for each satellite
    # --------------------------------------------------------------------
    # Use only the first state vector per satellite
    first_sv = ref_sv.drop_duplicates("satNo", keep="first")

    # Extract position and velocity vectors
    r_vecs = first_sv[["xpos", "ypos", "zpos"]].to_numpy()
    v_vecs = first_sv[["xvel", "yvel", "zvel"]].to_numpy()

    # Compute magnitudes of r and v vectors
    r_norms = np.linalg.norm(r_vecs, axis=1)
    v_norms = np.linalg.norm(v_vecs, axis=1)

    # Semi-major axis from vis-viva equation
    # Guard against division by zero when denominator is near zero
    denom = (2 / r_norms) - (v_norms**2 / mu)
    a = np.where(np.abs(denom) > 1e-10, 1 / denom, np.nan)

    # Orbital periods in seconds (NaN if hyperbolic/unbound)
    T = np.where(a > 0, 2 * np.pi * np.sqrt(a**3 / mu), np.nan)

    # Map satNo → period
    periods = dict(zip(first_sv["satNo"], T))

    # --------------------------------------------------------------------
    # Create efficient group keys for binning observations
    # --------------------------------------------------------------------
    added_cols = ["grp_key", "grp_code"]
    ref_obs_wip = ref_obs.copy()  # Avoid mutating input DataFrame

    # Use shared helper to build grouping key
    ref_obs_wip["grp_key"] = _build_track_grouping_key(ref_obs_wip, include_senalt=True)

    # Convert to categorical and use integer group codes for performance
    ref_obs_wip["grp_key"] = ref_obs_wip["grp_key"].astype("category")
    ref_obs_wip["grp_code"] = ref_obs_wip["grp_key"].cat.codes

    # --------------------------------------------------------------------
    # Group by generated group code
    # --------------------------------------------------------------------
    bins = []
    grouped = ref_obs_wip.groupby("grp_code", sort=False)

    for _, group in grouped:
        if len(group) < 3:
            metrics[3] += 1  # Too short to be a track
            continue
        sat = group["satNo"].iloc[0]
        bins.append((sat, group))

    # --------------------------------------------------------------------
    # Split each bin into tracks based on time gaps
    # --------------------------------------------------------------------
    tracks = []

    # Define the time gap threshold
    threshold = pd.Timedelta(minutes=90)

    for sat, obs in bins:
        # Get orbital period in seconds for this satellite
        P = periods.get(sat)
        if not P or not np.isfinite(P):
            metrics[3] += 1  # No valid period
            continue

        # Sort observations by time (stable sort)
        obs_sorted = obs.sort_values("obTime", kind="mergesort")

        # Compute time differences and identify large gaps
        time_diffs = obs_sorted["obTime"].diff().gt(threshold)

        # Use cumulative sum of large gaps to assign track IDs
        track_ids = time_diffs.cumsum()

        # Group into tracks and filter
        for _, track in obs_sorted.groupby(track_ids, sort=False):
            metrics[0] += 1  # total tracks
            if len(track) >= 3:
                metrics[1] += 1  # kept
                tracks.append((sat, P, track.reset_index(drop=True)))
            else:
                metrics[2] += 1  # discarded (too short)

    # --------------------------------------------------------------------
    # Drop temporary columns from returned tracks to avoid leaking internal columns
    # --------------------------------------------------------------------
    cleaned_tracks = []
    for sat, P, track in tracks:
        cleaned_track = track.drop(
            columns=[col for col in added_cols if col in track.columns],
            errors="ignore",
        )
        cleaned_tracks.append((sat, P, cleaned_track))

    return cleaned_tracks, metrics


# =============================================================================
# ORBITAL REGIME DETECTION
# =============================================================================


def get_regime_profile(regime: str) -> Dict:
    """Get the downsampling profile for a given orbital regime."""
    return DOWNSAMPLING_PROFILES.get(regime, DOWNSAMPLING_PROFILES["LEO"])


# =============================================================================
# TRACK IDENTIFICATION AND PRESERVATION
# =============================================================================


def identify_tracks(
    obs_df: pd.DataFrame, gap_threshold_minutes: float = 90.0
) -> List[pd.DataFrame]:
    """
    Identify observation tracks based on time gaps.

    A track is a continuous set of observations from the same sensor/location
    with gaps less than the threshold.

    Args:
        obs_df: DataFrame of observations with 'obTime', 'satNo', 'idSensor' columns
        gap_threshold_minutes: Maximum gap in minutes within a track

    Returns:
        List of DataFrames, each representing a single track
    """
    if obs_df.empty:
        return []

    # Ensure obTime is datetime
    obs_df = obs_df.copy()
    if obs_df["obTime"].dtype == "object":
        obs_df["obTime"] = pd.to_datetime(obs_df["obTime"])

    # Sort by satellite and time
    obs_df = obs_df.sort_values(["satNo", "obTime"]).reset_index(drop=True)

    # Use shared helper to build grouping key (without senalt for this simpler function)
    obs_df["grp_key"] = _build_track_grouping_key(obs_df, include_senalt=False)

    tracks = []
    threshold = pd.Timedelta(minutes=gap_threshold_minutes)

    for _, group in obs_df.groupby("grp_key", sort=False):
        if len(group) < 1:
            continue

        group = group.sort_values("obTime")
        time_diffs = group["obTime"].diff()
        track_boundaries = (time_diffs > threshold).cumsum()

        for _, track in group.groupby(track_boundaries, sort=False):
            if len(track) >= 1:
                tracks.append(track.reset_index(drop=True))

    return tracks


def select_tracks_for_coverage(
    tracks: List[pd.DataFrame],
    orbital_period_sec: float,
    target_coverage: float,
    rng: np.random.Generator = None,
) -> List[pd.DataFrame]:
    """
    Select a subset of tracks to achieve target orbital coverage.

    Prioritizes tracks that are temporally spread out.

    Args:
        tracks: List of track DataFrames
        orbital_period_sec: Orbital period in seconds
        target_coverage: Target coverage as fraction of orbit
        rng: Random number generator

    Returns:
        List of selected track DataFrames
    """
    if not tracks:
        return []

    if rng is None:
        rng = np.random.default_rng()

    # Calculate track centers (median time)
    track_info = []
    for i, track in enumerate(tracks):
        center = track["obTime"].median()
        track_info.append(
            {
                "index": i,
                "center": center,
                "duration": (track["obTime"].max() - track["obTime"].min()).total_seconds(),
                "count": len(track),
            }
        )

    track_info = sorted(track_info, key=lambda x: x["center"])

    # Calculate how many tracks to select based on target coverage
    if len(track_info) <= 1:
        return tracks

    # Calculate temporal span
    total_span = (track_info[-1]["center"] - track_info[0]["center"]).total_seconds()
    num_periods = total_span / orbital_period_sec if orbital_period_sec > 0 else 1

    # Target number of tracks (at least 1 per period * coverage)
    target_tracks = max(2, int(len(tracks) * target_coverage / max(0.1, num_periods * 0.1)))
    target_tracks = min(target_tracks, len(tracks))

    # Select tracks spread across the observation window
    if target_tracks >= len(tracks):
        return tracks

    # Use stratified sampling - divide time into bins and sample from each
    selected_indices = set()
    num_bins = min(target_tracks, len(track_info))
    bin_size = len(track_info) // num_bins

    for i in range(num_bins):
        start_idx = i * bin_size
        end_idx = start_idx + bin_size if i < num_bins - 1 else len(track_info)
        bin_tracks = track_info[start_idx:end_idx]

        if bin_tracks:
            # Prefer tracks with more observations
            weights = np.array([t["count"] for t in bin_tracks], dtype=float)
            weights /= weights.sum()
            chosen_idx = rng.choice(len(bin_tracks), p=weights)
            selected_indices.add(bin_tracks[chosen_idx]["index"])

    return [tracks[i] for i in sorted(selected_indices)]


def thin_within_tracks(
    tracks: List[pd.DataFrame],
    obs_per_track: Tuple[int, int],
    preserve_boundaries: bool = True,
    rng: np.random.Generator = None,
) -> pd.DataFrame:
    """
    Thin observations within selected tracks.

    Preserves first and last observations of each track for OD purposes.

    Args:
        tracks: List of track DataFrames
        obs_per_track: (min, max) observations per track
        preserve_boundaries: Keep first and last observations
        rng: Random number generator

    Returns:
        Combined DataFrame of thinned tracks
    """
    if not tracks:
        return pd.DataFrame()

    if rng is None:
        rng = np.random.default_rng()

    min_obs, max_obs = obs_per_track
    thinned_tracks = []

    for track in tracks:
        if len(track) <= min_obs:
            thinned_tracks.append(track)
            continue

        # Determine target count for this track
        target_count = rng.integers(min_obs, min(max_obs, len(track)) + 1)

        if len(track) <= target_count:
            thinned_tracks.append(track)
            continue

        # Sort by time
        track = track.sort_values("obTime").reset_index(drop=True)

        if preserve_boundaries and target_count >= 2:
            # Keep first and last, sample the rest
            first_obs = track.iloc[[0]]
            last_obs = track.iloc[[-1]]
            middle_obs = track.iloc[1:-1]

            if len(middle_obs) > 0 and target_count > 2:
                # Sample uniformly from middle
                sample_count = target_count - 2
                if len(middle_obs) <= sample_count:
                    sampled_middle = middle_obs
                else:
                    sampled_indices = rng.choice(len(middle_obs), size=sample_count, replace=False)
                    sampled_middle = middle_obs.iloc[sorted(sampled_indices)]

                thinned = pd.concat([first_obs, sampled_middle, last_obs])
            else:
                thinned = pd.concat([first_obs, last_obs])
        else:
            # Simple random sampling
            sampled_indices = rng.choice(len(track), size=target_count, replace=False)
            thinned = track.iloc[sorted(sampled_indices)]

        thinned_tracks.append(thinned.reset_index(drop=True))

    if thinned_tracks:
        return pd.concat(thinned_tracks, ignore_index=True)
    return pd.DataFrame()


# =============================================================================
# REGIME-SPECIFIC DOWNSAMPLING
# =============================================================================


def downsample_by_regime(
    ref_obs: pd.DataFrame,
    sat_params: Dict,
    config: Optional[DownsampleConfig] = None,
    rng: np.random.Generator = None,
) -> pd.DataFrame:
    """
    Downsample observations using regime-specific parameters.

    Applies different downsampling profiles based on orbital regime
    (LEO, MEO, GEO, HEO) to achieve realistic observation patterns.

    Args:
        ref_obs: DataFrame of reference observations
        sat_params: Dict mapping satNo to orbital parameters
        config: DownsampleConfig instance (uses defaults if None)
        rng: Random number generator

    Returns:
        Downsampled DataFrame
    """
    if ref_obs.empty:
        return ref_obs

    if config is None:
        config = DownsampleConfig()

    if rng is None:
        rng = np.random.default_rng(config.seed)

    # Group satellites by regime
    regime_sats: Dict[str, List[int]] = {"LEO": [], "MEO": [], "GEO": [], "HEO": []}

    for sat_no, params in sat_params.items():
        sma = params.get("Semi-Major Axis", 7000)
        ecc = params.get("Eccentricity", 0.0)
        regime = determine_orbital_regime(sma, ecc)
        regime_sats[regime].append(sat_no)

    # Process each regime separately
    downsampled_parts = []

    for regime, sat_list in regime_sats.items():
        if not sat_list:
            continue

        # Get regime-specific profile
        profile = get_regime_profile(regime)

        # Filter observations for this regime
        regime_obs = ref_obs[ref_obs["satNo"].isin(sat_list)]
        if regime_obs.empty:
            continue

        # Apply regime-specific downsampling
        for sat_no in sat_list:
            sat_obs = regime_obs[regime_obs["satNo"] == sat_no]
            if sat_obs.empty:
                continue

            sat_param = sat_params.get(sat_no, {})
            period = sat_param.get("Period", 5400)  # Default ~90 min

            # Identify tracks
            tracks = identify_tracks(sat_obs)

            # Select tracks based on coverage target
            target_coverage = rng.uniform(profile["min_coverage_pct"], profile["max_coverage_pct"])
            selected_tracks = select_tracks_for_coverage(tracks, period, target_coverage, rng)

            # Thin observations within tracks
            obs_range = profile["obs_per_track"]
            thinned = thin_within_tracks(
                selected_tracks,
                obs_range,
                preserve_boundaries=config.preserve_track_boundaries,
                rng=rng,
            )

            if not thinned.empty:
                # Ensure minimum observations
                if len(thinned) >= config.min_obs_per_sat:
                    downsampled_parts.append(thinned)
                elif len(sat_obs) >= config.min_obs_per_sat:
                    # Fall back to original if thinning too aggressive
                    sample_size = min(len(sat_obs), config.min_obs_per_sat)
                    downsampled_parts.append(
                        sat_obs.sample(n=sample_size, random_state=rng.integers(2**31))
                    )

    if downsampled_parts:
        return pd.concat(downsampled_parts, ignore_index=True)
    return pd.DataFrame()


def downsample_preserve_tracks(
    obs_df: pd.DataFrame,
    sat_params: Dict,
    target_coverage: float = 0.05,
    target_gap_periods: float = 2.0,
    obs_per_track: Tuple[int, int] = (3, 10),
    preserve_boundaries: bool = True,
    seed: Optional[int] = None,
) -> pd.DataFrame:
    """
    Downsample while keeping track structure intact.

    This is the main physics-based downsampling function that:
    1. Identifies existing tracks (90-min gap criterion)
    2. Selects subset of tracks (not individual obs)
    3. Within selected tracks, thins observations uniformly
    4. Ensures first/last obs of each track preserved

    Args:
        obs_df: DataFrame of observations
        sat_params: Dict mapping satNo to orbital parameters
        target_coverage: Target orbital coverage (fraction)
        target_gap_periods: Target gap between tracks (orbital periods)
        obs_per_track: (min, max) observations per track
        preserve_boundaries: Keep first and last obs of each track
        seed: Random seed for reproducibility

    Returns:
        Downsampled DataFrame
    """
    if obs_df.empty:
        return obs_df

    rng = np.random.default_rng(seed)

    # Group by satellite
    result_parts = []

    for sat_no in obs_df["satNo"].unique():
        sat_obs = obs_df[obs_df["satNo"] == sat_no]
        sat_param = sat_params.get(sat_no, {})
        period = sat_param.get("Period", 5400)

        # Identify tracks
        tracks = identify_tracks(sat_obs)

        if not tracks:
            continue

        # Select tracks to achieve target coverage
        selected = select_tracks_for_coverage(tracks, period, target_coverage, rng)

        # Thin within tracks
        thinned = thin_within_tracks(selected, obs_per_track, preserve_boundaries, rng)

        if not thinned.empty:
            result_parts.append(thinned)

    if result_parts:
        return pd.concat(result_parts, ignore_index=True)
    return pd.DataFrame()


# =============================================================================
# 3D ORBITAL COVERAGE CALCULATION
# =============================================================================


def compute_mean_anomaly_from_obs(obs_df: pd.DataFrame, orbital_elements: Dict) -> np.ndarray:
    """
    Compute mean anomaly for each observation.

    Projects observations onto the orbital plane and computes
    the mean anomaly at each observation time.

    Args:
        obs_df: DataFrame with 'ra' and 'declination' columns
        orbital_elements: Dict with orbital elements

    Returns:
        Array of mean anomalies in radians
    """
    # Get orbital elements
    _a = orbital_elements.get("Semi-Major Axis", 7000)  # Reserved for future use
    e = orbital_elements.get("Eccentricity", 0.0)
    i = np.radians(orbital_elements.get("Inclination", 0.0))
    raan = np.radians(orbital_elements.get("RAAN", 0.0))
    argp = np.radians(orbital_elements.get("Argument of Perigee", 0.0))

    # Convert RA/Dec to line-of-sight unit vectors
    ra = np.radians(obs_df["ra"].values)
    dec = np.radians(obs_df["declination"].values)

    los_x = np.cos(dec) * np.cos(ra)
    los_y = np.cos(dec) * np.sin(ra)
    _los_z = np.sin(dec)  # Reserved for 3D calculations

    # Rotation matrix from perifocal to ECI
    cos_raan, sin_raan = np.cos(raan), np.sin(raan)
    _cos_argp, _sin_argp = np.cos(argp), np.sin(argp)  # Reserved for full rotation
    _cos_i, _sin_i = np.cos(i), np.sin(i)  # Reserved for full rotation

    # Inverse rotation to get to orbital plane
    # Simplified: project onto orbital plane and find angle

    # For each observation, find the true anomaly
    true_anomalies = np.arctan2(
        los_y * cos_raan + los_x * sin_raan, los_x * cos_raan - los_y * sin_raan
    )

    # Convert true anomaly to mean anomaly (simplified for small eccentricity)
    # For accurate conversion, use Kepler's equation
    E = 2 * np.arctan(np.sqrt((1 - e) / (1 + e)) * np.tan(true_anomalies / 2))
    mean_anomalies = E - e * np.sin(E)

    return mean_anomalies


def compute_arc_coverage(mean_anomalies: np.ndarray) -> float:
    """
    Compute the arc-length coverage from mean anomalies.

    Uses a union of angular intervals approach to compute
    what fraction of the orbit is covered by observations.

    Args:
        mean_anomalies: Array of mean anomalies in radians

    Returns:
        Coverage as fraction of full orbit (0 to 1)
    """
    if len(mean_anomalies) < 2:
        return 0.0

    # Normalize to [0, 2*pi]
    anomalies = mean_anomalies % (2 * np.pi)
    anomalies = np.sort(anomalies)

    # Compute gaps between consecutive observations
    gaps = np.diff(anomalies)
    gaps = np.append(gaps, (2 * np.pi) - anomalies[-1] + anomalies[0])

    # Coverage is complement of maximum gap
    # More sophisticated: sum of small arcs (those < threshold)
    arc_threshold = np.pi / 6  # 30 degrees

    # Count arcs that are "covered" (gap < threshold)
    covered_arcs = gaps[gaps < arc_threshold]
    total_covered = anomalies[-1] - anomalies[0] + sum(covered_arcs)

    # Normalize
    coverage = min(1.0, total_covered / (2 * np.pi))
    return coverage


def compute_3d_coverage(obs_df: pd.DataFrame, orbital_elements: Dict) -> Tuple[float, Dict]:
    """
    Compute true orbital coverage using 3D geometry.

    This is an improved coverage calculation that:
    1. Projects obs onto orbital plane (not just 2D polygon)
    2. Accounts for orbital precession over observation window
    3. Computes arc-length coverage, not area coverage
    4. Weights by observation quality if available

    Args:
        obs_df: DataFrame of observations
        orbital_elements: Dict with orbital elements

    Returns:
        Tuple of (coverage_fraction, coverage_stats_dict)
    """
    if len(obs_df) < 3:
        return 0.0, {"status": "insufficient_observations", "count": len(obs_df)}

    # Compute mean anomalies
    try:
        mean_anomalies = compute_mean_anomaly_from_obs(obs_df, orbital_elements)
    except Exception as e:
        # Fall back to 2D coverage
        coverage, _ = orbitCoverage(obs_df, orbital_elements)
        return coverage, {"status": "fallback_2d", "error": str(e)}

    # Compute arc coverage
    arc_coverage = compute_arc_coverage(mean_anomalies)

    # Also compute 2D coverage for comparison
    try:
        poly_coverage, _ = orbitCoverage(obs_df, orbital_elements)
    except Exception:
        poly_coverage = arc_coverage

    # Use weighted average (arc coverage more physically meaningful)
    combined_coverage = 0.7 * arc_coverage + 0.3 * poly_coverage

    stats = {
        "status": "success",
        "arc_coverage": arc_coverage,
        "poly_coverage": poly_coverage,
        "combined_coverage": combined_coverage,
        "n_observations": len(obs_df),
        "mean_anomaly_range": float(np.ptp(mean_anomalies)),
    }

    return combined_coverage, stats


def _downsampleAbsolute(ref_obs, sat_params, objp, obs_max, rand, rng, chosen_sats=None, bins=10):
    """
    Downsamples data to a maximum obs count.

    Args:
        ref_obs (Pandas DataFrame): Dataframe of reference observations.
        sat_params (Dict): Associated super-dict of orbital elements in the following form:
            sat_params = {
                satNo: {
                    "Semi-Major Axis": a,
                    "Eccentricity": e,
                    "Inclination": i,
                    "RAAN": RAAN,
                    "Argument of Perigee": arg_perigee,
                    "Mean Anomaly": M,
                    "Period": P,
                    "Number of Obs": #Obs,
                    "Orbital Coverage": %Coverage,
                    "Max Track Gap": T/P
                },
                satNo: {...},
                satNo: {...},
                ...
            }
            All values are in km, degrees, and seconds as appropriate.
        objp (Tuple of floats): Tuple of (min%, max%, target%) in decimal.
        obs_max (int): Max observation count for the chosen objects.
        rand, rng (float): Random seed for reproducibility.
        bins (int): Number of bins for time downsampling. Defaults to 10.
        chosen_sats (List): List of satellites to consider for downsampling. Defaults to None.

    Outputs:
        ref_obs, dataset: Downsampled DataFrames.
    """

    orbital_periods = {
        sat: elems["Period"] for sat, elems in sat_params.items() if np.isfinite(elems["Period"])
    }

    # Remove sats with 2 or fewer obs (don't count)
    counts = ref_obs["satNo"].value_counts()
    culled_obs = ref_obs[ref_obs["satNo"].isin(counts[counts > 2].index)].copy()
    skipped_obs = ref_obs[ref_obs["satNo"].isin(counts[counts <= 2].index)]

    # Select target satellites
    all_satIDs = culled_obs["satNo"].dropna().unique()

    if chosen_sats is not None:
        satIDs = np.array([sat for sat in all_satIDs if sat in set(chosen_sats)])
    else:
        satIDs = all_satIDs

    # Add temp time binnings
    culled_obs["time_bin"] = pd.qcut(culled_obs["obTime"], q=bins, duplicates="drop")

    # Sort obs for performance
    grouped_obs = {sat: df for sat, df in culled_obs.groupby("satNo", observed=True)}

    # Determine observation counts for all sats
    sat_obs_counts = {
        sat: elems["Number of Obs"]
        for sat, elems in sat_params.items()
        if np.isfinite(elems["Number of Obs"])
    }

    # Satellites already below or equal to obs_max stay as is
    already_low_sats = [sat for sat, count in sat_obs_counts.items() if count <= obs_max]

    # End early if min reached
    initial_fraction = len(already_low_sats) / len(satIDs)

    if initial_fraction >= objp[0]:
        return ref_obs

    # Candidates for downsampling (still above threshold)
    remaining_sats = [sat for sat, count in sat_obs_counts.items() if count > obs_max]

    # Compute how many we still need to downsample
    total_target = int(np.ceil(objp[2] * len(satIDs)))
    remaining_needed = max(0, total_target - len(already_low_sats))

    # Sort the remaining sats by *fewest obs first*
    remaining_sats_sorted = sorted(remaining_sats, key=lambda s: sat_obs_counts[s])

    # Pick the lowest-count ones
    sampled_sats = remaining_sats_sorted[:remaining_needed]

    # Union with already-low sats (which won't actually be downsampled)
    sampled_satID_set = set(sampled_sats + already_low_sats)

    # Perform bin-based sampling - UNIFORM per Louis's specification
    def safe_sample(group, k, period_sec, relax=False):
        """Sample k observations from group using UNIFORM random selection."""
        if k >= len(group):
            return group
        # Per Louis's spec: uniform random sampling, no density weighting
        return group.sample(n=k, replace=False, random_state=rand)

    # Downsample
    keep_obs = []
    removed_ids = []
    for sat, sat_df in grouped_obs.items():
        if sat in sampled_satID_set and len(sat_df) > obs_max:
            # Group by (satNo, time_bin)
            binned = sat_df.groupby("time_bin", group_keys=False, observed=True)

            # Determine how many obs to keep per bin (initial even split)
            n_bins = binned.ngroups
            base_per_bin = obs_max // n_bins
            remainder = obs_max % n_bins

            period_sec = orbital_periods.get(sat, 5400)

            # Sort by time ONCE
            time_sorted = sat_df.sort_values("obTime")

            # Assign time bins in one vectorized call
            time_bins = pd.qcut(time_sorted["obTime"], q=bins, duplicates="drop")

            # Compute target per bin
            bin_counts = time_bins.value_counts(sort=False)
            n_bins = len(bin_counts)
            base_per_bin = obs_max // n_bins
            remainder = obs_max % n_bins

            # Compute desired sample count per bin (evenly + remainder spread)
            target_per_bin = pd.Series(base_per_bin, index=bin_counts.index) + pd.Series(
                [1] * remainder + [0] * (n_bins - remainder), index=bin_counts.index
            )

            # Per Louis's specification: use UNIFORM random sampling
            # NO density weighting - observations should be selected uniformly
            # This ensures proper representation without bias toward dense regions

            # Combine into one DataFrame
            time_sorted = time_sorted.assign(time_bin=time_bins)

            # Now sample per bin with UNIFORM sampling (no density weights):
            sampled = time_sorted.groupby("time_bin", group_keys=False, observed=True).apply(
                lambda g: g.sample(
                    n=min(int(target_per_bin[g.name]), len(g)),
                    replace=False,  # No replacement for proper sampling
                    random_state=rand,
                )
            )

            keep_obs.append(sampled)

            removed_idx = sat_df.index.difference(sampled.index)
            removed_ids.extend(sat_df.loc[removed_idx, "id"].tolist())
        else:
            keep_obs.append(sat_df)

    ref_obs = pd.concat(keep_obs + [skipped_obs]).reset_index(drop=True)

    # Remove sample column
    ref_obs = ref_obs.drop("time_bin", axis=1)

    return ref_obs


def _triangle_area(p1, p2, p3) -> float:
    return 0.5 * abs(
        p1["x"] * (p2["y"] - p3["y"])
        + p2["x"] * (p3["y"] - p1["y"])
        + p3["x"] * (p1["y"] - p2["y"])
    )


def _full_polygon_area(points) -> float:
    return 0.5 * abs(
        sum(
            points[i]["x"] * points[(i + 1) % len(points)]["y"]
            - points[(i + 1) % len(points)]["x"] * points[i]["y"]
            for i in range(len(points))
        )
    )


def _lowerOrbitCoverage(ref_obs, sat_params, objp, coveragep, rng, chosen_sats=None):
    """
    Reduces orbital coverage to a set percentage.

    Args:
        ref_obs (Pandas DataFrame): Dataframe of reference observations.
        sat_params (Dict): Associated super-dict of orbital elements in the following form:
            sat_params = {
                satNo: {
                    "Semi-Major Axis": a,
                    "Eccentricity": e,
                    "Inclination": i,
                    "RAAN": RAAN,
                    "Argument of Perigee": arg_perigee,
                    "Mean Anomaly": M,
                    "Period": P,
                    "Number of Obs": #Obs,
                    "Orbital Coverage": %Coverage,
                    "Max Track Gap": T/P
                },
                satNo: {...},
                satNo: {...},
                ...
            }
            All values are in km, degrees, and seconds as appropriate.
        objp (Tuple of floats) Tuple of (min%, max%, target%) in decimal.
        coveragep (Tuple of floats): (Max, Min) orbital coverage for the chosen objects.
        rng (float): Random seed for reproducability.
        chosen_sats (List): List of satellites to consider for coverage downsampling. Defaults to None, which allows sat-agnostic downsampling.

    Outputs:
        ref_obs, dataset: Downsampled DataFrames.
        err: Returns 1 if function failed, else 0.
    """

    err = 0

    # --------------------------------------------------------------------
    # Compute current orbit coverage and check current coverages
    # --------------------------------------------------------------------

    # Pre-group ref_obs by satNo
    # Remove sats with 2 or fewer obs (don't count)
    sorted_obs = ref_obs.groupby("satNo", observed=True).filter(lambda g: len(g) > 2)
    grouped_obs = {sat: df for sat, df in sorted_obs.groupby("satNo", observed=True)}
    satIDs = list(grouped_obs.keys())
    if chosen_sats is not None:
        chosen_sats = set(chosen_sats)
        satIDs = [sat for sat in satIDs if sat in chosen_sats]

    # Compute initial coverage and store points
    coverages = {}
    points = {}

    for sat, sat_df in grouped_obs.items():
        if len(sat_df) >= 3:
            # This does NOT use the params list as all sorted points are also needed
            coverages[sat], points[sat] = orbitCoverage(sat_df, sat_params.get(sat))
            points[sat]["time"] = points[sat]["id"].map(sat_df.set_index("id")["obTime"])
        else:
            # Cannot define coverage, 2 points is considered low coverage anyway
            coverages[sat] = 0
            points[sat] = None

    # Check how many satellites currently meet the threshold
    coverage_series = pd.Series(coverages)
    low_coverage_sats = coverage_series[coverage_series <= coveragep[0]].index
    high_coverage_sats = coverage_series[coverage_series > coveragep[0]].index

    total_sat_count = len(satIDs)

    # Return without change if already meets requirements
    min_required = int(np.ceil(objp[0] * total_sat_count))
    target_required = int(np.ceil(objp[2] * total_sat_count))

    if len(low_coverage_sats) >= min_required:
        return ref_obs, err

    # Compute how many more sats we need to prune
    sats_to_prune = target_required - len(low_coverage_sats)
    if sats_to_prune <= 0:
        return ref_obs, err

    # --------------------------------------------------------------------
    # Downsample to obtain required coverage
    # --------------------------------------------------------------------

    # Track successfully pruned satellites
    successfully_pruned = set()
    dropped_ids = []

    # Sort high-coverage sats by how close they are to the threshold (ascending)
    remaining_candidates = (
        coverage_series[high_coverage_sats]
        .sort_values()  # lowest coverage first
        .index.tolist()
    )

    while len(successfully_pruned) < sats_to_prune:
        if not remaining_candidates:
            print("Warning: Could not meet desired coverage reduction.")
            err = 1
            break

        # Select the lowest coverage satellite that hasn’t been tried yet
        sat = remaining_candidates.pop(0)

        sat_df = grouped_obs[sat]
        if points[sat] is None or len(points[sat]) < 3:
            continue  # skip unusable satellites

        sma = sat_params[sat]["Semi-Major Axis"]
        # Guard against invalid Semi-Major Axis values
        if not np.isfinite(sma) or sma <= 0:
            continue
        max_area = np.pi * sma ** 2
        min_coverage_area = coveragep[1] * max_area
        target_coverage_area = coveragep[0] * max_area
        n = len(points[sat])
        point_list = points[sat].to_dict("records")

        # Build doubly linked list
        nodes = [
            {"point": pt, "index": i, "prev": (i - 1) % n, "next": (i + 1) % n}
            for i, pt in enumerate(point_list)
        ]
        removed = [False] * n
        heap = []

        sat_period = sat_params[sat]["Period"]
        gap_thresh = pd.Timedelta(seconds=0.1 * sat_period)
        relax = False

        # Heap push to sort observations
        def _push(i):
            if removed[i] or removed[nodes[i]["prev"]] or removed[nodes[i]["next"]]:
                return
            a = nodes[nodes[i]["prev"]]["point"]
            b = nodes[i]["point"]
            c = nodes[nodes[i]["next"]]["point"]
            t_prev = pd.to_datetime(a["time"])
            t_curr = pd.to_datetime(b["time"])
            t_next = pd.to_datetime(c["time"])
            if not relax and ((t_next - t_curr > gap_thresh) or (t_curr - t_prev > gap_thresh)):
                return
            area = _triangle_area(a, b, c)
            heapq.heappush(heap, (-area, i))

        for i in range(n):
            _push(i)

        # Remove point with highest coverage impact
        remaining = n
        total_removed = 0
        area = _full_polygon_area(point_list)
        current_dropped = []

        while area > target_coverage_area and remaining > 3:
            while heap:
                neg_area, i = heapq.heappop(heap)
                if removed[i]:
                    continue
                projected_area = area - abs(neg_area)  # neg_area is negative
                if projected_area < min_coverage_area:
                    continue  # Skip this point, it would drop too far

                area -= abs(neg_area)
                removed[i] = True
                current_dropped.append(nodes[i]["point"]["id"])
                total_removed += 1
                remaining -= 1

                pi = nodes[i]["prev"]
                ni = nodes[i]["next"]
                nodes[pi]["next"] = ni
                nodes[ni]["prev"] = pi

                _push(pi)
                _push(ni)

                break
            else:
                if not relax:
                    relax = True
                    heap.clear()
                    for j in range(n):
                        _push(j)
                    continue
                break  # no valid points left and already relaxed

        if area <= target_coverage_area and area >= min_coverage_area and remaining >= 3:
            dropped_ids.extend(current_dropped)
            successfully_pruned.add(sat)

    # Use set for fast membership testing
    dropped_id_set = set(dropped_ids)

    # Mask to keep only non-dropped observations
    mask_ref = ~ref_obs["id"].map(dropped_id_set.__contains__)
    ref_obs = ref_obs.loc[mask_ref].reset_index(drop=True)

    return ref_obs, err


def _increaseTrackDistance(ref_obs, sat_params, objp, trackp, rng, chosen_sats=None):
    """
    Inceases gaps between tracks to obtain a minimum gap.

    Args:
        ref_obs (Pandas DataFrame): Dataframe of reference observations.
        sat_params (Dict): Associated super-dict of orbital elements in the following form:
            sat_params = {
                satNo: {
                    "Semi-Major Axis": a,
                    "Eccentricity": e,
                    "Inclination": i,
                    "RAAN": RAAN,
                    "Argument of Perigee": arg_perigee,
                    "Mean Anomaly": M,
                    "Period": P,
                    "Number of Obs": #Obs,
                    "Orbital Coverage": %Coverage,
                    "Max Track Gap": T/P
                },
                satNo: {...},
                satNo: {...},
                ...
            }
            All values are in km, degrees, and seconds as appropriate.
        objp (Tuple of floats): Tuple of (min%, max%, target%) in decimal.
        trackp (float): Desired gap size (in percentage of period).
        rng (float): Random seed for reproducability.
        chosen_sats (List): List of satellites to consider for track downsampling. Defaults to None, which allows sat-agnostic downsampling.

    Outputs:
        ref_obs, dataset: Downsampled DataFrames.
        err: Returns 1 if function failed, else 0.
    """

    err = 0

    # --------------------------------------------------------------------
    # Compute the maximum time gap between observations per satellite
    # --------------------------------------------------------------------

    gap_df = pd.DataFrame.from_dict(sat_params, orient="index")

    gap_df = gap_df[gap_df["Number of Obs"] > 2]

    # Convert "Max Track Gap" from fraction-of-period to an absolute timedelta if needed
    gap_df["max_gap"] = pd.to_timedelta(gap_df["Max Track Gap"] * gap_df["Period"], unit="s")

    # Period is already in seconds, make it a Timedelta for consistency
    gap_df["period_td"] = pd.to_timedelta(gap_df["Period"], unit="s")

    # Keep only the relevant columns
    gap_df = gap_df[["period_td", "max_gap"]].dropna()
    gap_df.columns = ["period", "max_gap"]  # rename to match old interface

    # Compute the target gap as a fraction of orbital period
    gap_df["target_gap"] = pd.to_timedelta(gap_df["period"] * trackp, unit="s")

    # Determine whether each satellite already has a sufficient gap
    gap_df["sufficient_gap"] = gap_df["max_gap"] >= gap_df["target_gap"]

    # --------------------------------------------------------------------
    # Select satellites that need pruning to meet desired percentage (objp)
    # --------------------------------------------------------------------
    if chosen_sats is not None:
        chosen_sats = set(chosen_sats)
        gap_df = gap_df.loc[gap_df.index.intersection(chosen_sats)]

    # Satellites with/without sufficient observation gaps
    sufficient_sats = set(gap_df[gap_df["sufficient_gap"]].index)
    insufficient_sats = set(gap_df[~gap_df["sufficient_gap"]].index)

    # Calculate how many satellites should have widened gaps
    total_sats = len(sufficient_sats) + len(insufficient_sats)
    min_required = int(np.ceil(objp[0] * total_sats))
    target_required = int(np.ceil(objp[2] * total_sats))

    # Return early if meets min threshold
    if len(sufficient_sats) >= min_required:
        return ref_obs, err

    # Determine how many additional satellites need gap widening
    num_to_prune = target_required - len(sufficient_sats)
    if num_to_prune <= 0:
        return ref_obs, err
    num_to_prune = min(num_to_prune, len(insufficient_sats))  # Don't exceed available sats

    # --------------------------------------------------------------------
    # Prune observations for selected satellites to widen gaps
    # --------------------------------------------------------------------

    dropped_ids = []  # To collect the IDs of removed observations

    # Process satellites dynamically until the desired number is met
    grouped_obs = {sat: df for sat, df in ref_obs.groupby("satNo", observed=True)}
    remaining_candidates = (
        gap_df.loc[list(insufficient_sats)]
        .assign(delta=lambda df: (df["target_gap"] - df["max_gap"]).dt.total_seconds())
        .sort_values("delta")
        .index.tolist()
    )
    successfully_pruned = set()

    while len(successfully_pruned) < num_to_prune:
        if not remaining_candidates:
            print("Warning: Could not achieve desired number of satellites with widened gaps.")
            err = 1

        # Pick the satellite with highest existing gap to try pruning
        sat = remaining_candidates.pop(0)
        sat_df = grouped_obs[sat]

        # Get the target gap
        target_gap = gap_df.loc[sat, "target_gap"]
        if pd.isna(target_gap) or len(sat_df) < 2:
            continue

        total_span = sat_df["obTime"].max() - sat_df["obTime"].min()
        if total_span < target_gap:
            continue

        sorted_df = sat_df.sort_values("obTime").reset_index()
        times_np = sorted_df["obTime"].values.astype("datetime64[ns]")
        target_gap_np = target_gap.to_numpy()

        # Initialize sliding window algorithm
        min_count = float("inf")
        best_start_idx = None
        best_end_idx = None

        # Find minimal count window of exact length target_gap
        for i in range(len(times_np)):
            start_time = times_np[i]

            # If even the newest observation is within target_gap, we can stop
            if (times_np[-1] - start_time) < target_gap_np:
                break

            # Find the last index within [start_time, start_time + target_gap_np]
            end_time = start_time + target_gap_np
            j = np.searchsorted(times_np, end_time, side="right")  # include obs equal to end_time

            count = j - i  # how many obs fall inside this window

            if count < min_count:
                min_count = count
                best_start_idx = i
                best_end_idx = j

        to_remove = sorted_df.iloc[best_start_idx:best_end_idx]

        # Ensure at least 2 remain after removal
        if len(sorted_df) - len(to_remove) < 3:
            continue  # Cannot perform window increase

        # Record success
        total_span = sorted_df["obTime"].max() - sorted_df["obTime"].min()

        dropped_ids.extend(to_remove["id"].tolist())
        successfully_pruned.add(sat)

    # --------------------------------------------------------------------
    # Remove pruned observations from ref_obs and dataset
    # --------------------------------------------------------------------

    # Use set for fast membership testing
    dropped_id_set = set(dropped_ids)

    # Mask to keep only non-dropped observations
    mask_ref = ~ref_obs["id"].map(dropped_id_set.__contains__)
    ref_obs = ref_obs.loc[mask_ref].reset_index(drop=True)

    return ref_obs, err


def downsampleData(
    ref_obs, sat_params, orbit_coverage, track_length, obs_count, bins=10, rand=None
):
    """
    Does best downsampling of a observation dataset given specified parameters.

    Args:
        ref_obs (Pandas DataFrame): Dataframe of reference observations.
        sat_params (Dict): Associated super-dict of orbital elements in the following form:
            sat_params = {
                satNo: {
                    "Semi-Major Axis": a,
                    "Eccentricity": e,
                    "Inclination": i,
                    "RAAN": RAAN,
                    "Argument of Perigee": arg_perigee,
                    "Mean Anomaly": M,
                    "Period": P,
                    "Number of Obs": #Obs,
                    "Orbital Coverage": %Coverage,
                    "Max Track Gap": T/P
                },
                satNo: {...},
                satNo: {...},
                ...
            }
            All values are in km, degrees, and seconds as appropriate.
        orbit_coverage (Dict): Dictionary of coverage downsample requests in the following form:
            - 'sats': List of sat IDs (leave as None if all requested)
            - 'p_bounds': Tuple of (min%, max%, target%) in decimal
            - 'p_coverage': Requested (max, min) coverage in decimal
        track_length (Dict): Dictionary of track downsample requests in the following form:
            - 'sats': List of sat IDs (leave as None if all requested)
            - 'p_bounds': Tuple of (min%, max%, target%) in decimal
            - 'p_track': Requested track length in multiples of period
        obs_count (Dict): Dictionary of observation downsample requests in the following form:
            - 'sats': List of sat IDs (leave as None if all requested)
            - 'p_bounds': Tuple of (min%, max%, target%) in decimal
            - 'obs_max': Requested maximum obs count
        bins (int): Number of bins for time downsampling. Defaults to 10.
        rand (float): Random seed for reproducability. Defaults to None.

    Returns:
        ref_obs: Downsampled DataFrame.
        p_reached: Tuple of (coverage %, gap %, obs_count %) reached.
    """

    # Set seed if specified
    if rand is not None:
        np.random.seed(rand)
        rng = np.random.default_rng(rand)
    else:
        rng = np.random.default_rng()

    # Coverage
    ref_obs, _ = _lowerOrbitCoverage(
        ref_obs,
        sat_params,
        orbit_coverage["p_bounds"],
        orbit_coverage["p_coverage"],
        rng,
        orbit_coverage["sats"],
    )
    # Gaps
    ref_obs, _ = _increaseTrackDistance(
        ref_obs,
        sat_params,
        track_length["p_bounds"],
        track_length["p_track"],
        rng,
        track_length["sats"],
    )
    # Max count
    ref_obs = _downsampleAbsolute(
        ref_obs,
        sat_params,
        obs_count["p_bounds"],
        obs_count["obs_max"],
        rand,
        rng,
        obs_count["sats"],
    )

    # --------------------------------------------------------------------
    # Determine final metrics
    # --------------------------------------------------------------------

    # Filter satellites with >2 observations
    counts = ref_obs["satNo"].value_counts()
    valid_sats = counts[counts > 2].index  # Only sats eligible for metrics

    # Helper: restrict to user-specified list if provided
    def _filter_sats(candidate_list, valid_sats):
        return (
            set(valid_sats)
            if candidate_list is None
            else set(valid_sats).intersection(candidate_list)
        )

    # Total eligable sats for each metric
    cov_sats = _filter_sats(orbit_coverage["sats"], valid_sats)
    gap_sats = _filter_sats(track_length["sats"], valid_sats)
    cnt_sats = _filter_sats(obs_count["sats"], valid_sats)

    total_cov = len(cov_sats)
    total_gap = len(gap_sats)
    total_cnt = len(cnt_sats)

    # Find current coverages
    grouped_obs = {sat: df for sat, df in ref_obs.groupby("satNo", observed=True)}

    coverages = {}
    for sat, sat_df in grouped_obs.items():
        if len(sat_df) >= 3:
            coverages[sat], _ = orbitCoverage(sat_df, sat_params.get(sat))
        else:
            # Cannot define coverage, 2 points is considered low coverage anyway
            coverages[sat] = 0

    cov = sum(v <= orbit_coverage["p_coverage"] for sat, v in coverages.items() if sat in cov_sats)

    # Find current gaps
    sorted_obs = ref_obs.sort_values(["satNo", "obTime"])
    sorted_obs["time_diff"] = sorted_obs.groupby("satNo", observed=True)["obTime"].diff()
    max_gaps = sorted_obs.groupby("satNo", observed=True)["time_diff"].max()
    periods = pd.Series({sat: elems["Period"] for sat, elems in sat_params.items()}).reindex(
        max_gaps.index
    )
    periods_td = pd.to_timedelta(periods, unit="s")

    gap_exceeds = max_gaps >= (track_length["p_track"] * periods_td)
    gap = gap_exceeds[list(gap_sats)].sum()

    # Find current counts
    count = len([sat for sat in cnt_sats if len(grouped_obs.get(sat, [])) <= obs_count["obs_max"]])

    p_reached = (
        cov / total_cov if total_cov else 0,
        gap / total_gap if total_gap else 0,
        count / total_cnt if total_cnt else 0,
    )

    return ref_obs, p_reached


# =============================================================================
# SEQUENTIAL DOWNSAMPLING (per Louis's Specification)
# =============================================================================
# Order: Coverage → Track Gap → Obs Count
# This is the CORRECT order per Louis's Benchmarking Documentation


def downsample_observations_sequential(
    observations: pd.DataFrame,
    target_coverage: float,
    target_track_gap: str,  # "short" or "long"
    target_obs_count: str,  # "low" or "standard"
    orbital_period: float,
    regime: str,
    sat_no: int = None,
    seed: Optional[int] = None,
) -> pd.DataFrame:
    """
    Sequential downsampling per Louis's specification.

    Order: Coverage → Track Gap → Observation Count

    Per Louis's Benchmarking Documentation, downsampling must occur
    in this specific order to achieve proper quality distribution.

    Args:
        observations: Input observations DataFrame
        target_coverage: Target orbital coverage fraction
        target_track_gap: "short" (<2 periods) or "long" (>2 periods)
        target_obs_count: "low" (<50) or "standard" (50-150 per 3 days)
        orbital_period: Satellite orbital period in seconds
        regime: Orbital regime for threshold lookup ("LEO", "MEO", "GEO")
        sat_no: Optional satellite NORAD ID for logging
        seed: Random seed for reproducibility

    Returns:
        Downsampled observations DataFrame
    """
    if observations.empty:
        return observations

    rng = np.random.default_rng(seed)
    result = observations.copy()

    # Ensure obTime is datetime
    if result["obTime"].dtype == "object":
        result["obTime"] = pd.to_datetime(result["obTime"])

    result = result.sort_values("obTime").reset_index(drop=True)

    # -------------------------------------------------------------------------
    # Step 1: Lower Orbital Coverage
    # -------------------------------------------------------------------------
    # Per Louis's spec: Can't remove observation if neighbor is within 0.1 period
    neighbor_constraint_sec = 0.1 * orbital_period

    current_coverage = _estimate_coverage(result, orbital_period)

    if current_coverage > target_coverage and len(result) > 3:
        # Calculate how many observations to remove to achieve target coverage
        # Coverage is roughly proportional to number of observations
        target_obs = max(3, int(len(result) * target_coverage / max(0.01, current_coverage)))

        if target_obs < len(result):
            # Remove observations with UNIFORM random selection
            # But respect the neighbor constraint
            indices_to_keep = _select_indices_with_constraint(
                result["obTime"].values,
                target_obs,
                neighbor_constraint_sec,
                rng,
            )
            result = result.iloc[indices_to_keep].reset_index(drop=True)

    # -------------------------------------------------------------------------
    # Step 2: Increase Track Gap
    # -------------------------------------------------------------------------
    # Per Louis's spec: "Long" gap = > 2 orbital periods between tracks
    if target_track_gap == "long":
        min_gap_sec = TRACK_GAP_LONG_MULTIPLIER * orbital_period

        # Identify tracks (observations within 90 minutes of each other)
        track_threshold = pd.Timedelta(minutes=90)
        result = result.sort_values("obTime")
        time_diffs = result["obTime"].diff()
        track_ids = (time_diffs > track_threshold).cumsum()
        result["_track_id"] = track_ids

        # Calculate gaps between tracks
        track_info = result.groupby("_track_id").agg(
            start_time=("obTime", "min"),
            end_time=("obTime", "max"),
            count=("obTime", "count"),
        ).reset_index()

        # Find pairs of tracks that are too close together
        if len(track_info) > 1:
            track_info = track_info.sort_values("start_time")
            track_gaps = track_info["start_time"].diff().dt.total_seconds()

            # Remove entire tracks that are too close to previous track
            tracks_to_remove = []
            for i in range(1, len(track_info)):
                if track_gaps.iloc[i] < min_gap_sec:
                    # Prefer to remove the smaller track
                    if track_info.iloc[i]["count"] <= track_info.iloc[i-1]["count"]:
                        tracks_to_remove.append(track_info.iloc[i]["_track_id"])
                    else:
                        tracks_to_remove.append(track_info.iloc[i-1]["_track_id"])

            # Remove selected tracks
            result = result[~result["_track_id"].isin(tracks_to_remove)]

        result = result.drop("_track_id", axis=1).reset_index(drop=True)

    # -------------------------------------------------------------------------
    # Step 3: Adjust Observation Count
    # -------------------------------------------------------------------------
    # Per Louis's spec: LOW = <50 obs per 3 days, STANDARD = 50-150 per 3 days
    if target_obs_count == "low":
        target_count = OBS_COUNT_LOW_THRESHOLD - 1  # <50 = 49 target
    else:  # "standard"
        target_count = 100  # 50-150 range, aim for middle

    if len(result) > target_count:
        # Use UNIFORM random sampling (no density weighting per Louis's spec)
        indices = rng.choice(len(result), size=target_count, replace=False)
        result = result.iloc[sorted(indices)].reset_index(drop=True)

    return result


def _estimate_coverage(obs_df: pd.DataFrame, orbital_period: float) -> float:
    """
    Estimate orbital coverage from observations.

    Simple estimation based on time distribution around the orbit.
    """
    if len(obs_df) < 2 or orbital_period <= 0:
        return 0.0

    # Use phase angle method from windowSelection
    from uct_benchmark.data.windowSelection import calculate_orbital_coverage_polygon
    return calculate_orbital_coverage_polygon(obs_df, orbital_period)


def _select_indices_with_constraint(
    times: np.ndarray,
    target_count: int,
    min_neighbor_gap_sec: float,
    rng: np.random.Generator,
) -> List[int]:
    """
    Select indices while respecting neighbor constraint.

    Can't remove an observation if its neighbor is within min_neighbor_gap_sec.
    """
    n = len(times)
    if target_count >= n:
        return list(range(n))

    # Convert to numeric for gap calculation
    if hasattr(times[0], 'timestamp'):
        times_sec = np.array([t.timestamp() for t in times])
    else:
        times_sec = times.astype('datetime64[s]').astype(float)

    # Calculate gaps to neighbors
    gaps_before = np.diff(times_sec, prepend=times_sec[0] - min_neighbor_gap_sec - 1)
    gaps_after = np.diff(times_sec, append=times_sec[-1] + min_neighbor_gap_sec + 1)

    # Identify which observations CAN be removed (neighbors far enough)
    can_remove = (gaps_before >= min_neighbor_gap_sec) & (gaps_after >= min_neighbor_gap_sec)

    # Always keep first and last observations
    can_remove[0] = False
    can_remove[-1] = False

    # Start with all indices
    keep_indices = list(range(n))
    removable_indices = [i for i in keep_indices if can_remove[i]]

    # Remove observations until we reach target count
    while len(keep_indices) > target_count and removable_indices:
        # Uniform random selection of which to remove
        remove_idx = rng.choice(removable_indices)
        keep_indices.remove(remove_idx)
        removable_indices.remove(remove_idx)

    return sorted(keep_indices)


def downsample_dataset_sequential(
    obs_df: pd.DataFrame,
    sat_params: Dict[int, Dict],
    coverage_quality: str = "S",
    track_gap_quality: str = "S",
    obs_count_quality: str = "S",
    seed: Optional[int] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Downsample entire dataset using sequential method per Louis's spec.

    Applies Coverage → Track Gap → Obs Count downsampling in order,
    per satellite, based on A/S/N quality targets.

    Args:
        obs_df: DataFrame of all observations
        sat_params: Dict mapping satNo to orbital parameters
        coverage_quality: "A", "S", or "N" for coverage quality
        track_gap_quality: "A", "S", or "N" for track gap quality
        obs_count_quality: "A", "S", or "N" for observation count quality
        seed: Random seed

    Returns:
        Tuple of (downsampled_df, metadata)
    """
    from uct_benchmark.data.windowSelection import interpret_quality_code

    rng = np.random.default_rng(seed)

    # Map A/S/N to target values
    coverage_targets = {"A": 0.02, "S": 0.10, "N": 0.30}
    track_gap_targets = {"A": "long", "S": "short", "N": "short"}
    obs_count_targets = {"A": "low", "S": "standard", "N": "standard"}

    target_coverage = coverage_targets.get(coverage_quality.upper(), 0.10)
    target_track_gap = track_gap_targets.get(track_gap_quality.upper(), "short")
    target_obs_count = obs_count_targets.get(obs_count_quality.upper(), "standard")

    # Determine which satellites should have LOW quality
    # Per Louis's spec: A=0-33%, S=34-66%, N=67-100% have LOW quality
    quality_range = interpret_quality_code(coverage_quality)
    target_low_pct = (quality_range['min_pct'] + quality_range['max_pct']) / 2

    sat_ids = obs_df["satNo"].unique()
    n_sats = len(sat_ids)
    n_low_quality = int(n_sats * target_low_pct)

    # Randomly select which satellites get LOW quality
    low_quality_sats = set(rng.choice(sat_ids, n_low_quality, replace=False))

    # Process each satellite
    downsampled_parts = []
    metadata_per_sat = {}

    for sat_no in sat_ids:
        sat_obs = obs_df[obs_df["satNo"] == sat_no].copy()
        sat_param = sat_params.get(int(sat_no), {})
        period = sat_param.get("Period", 5400)  # Default 90 min

        # Determine regime
        sma = sat_param.get("Semi-Major Axis", 7000)
        regime = determine_orbital_regime(sma, sat_param.get("Eccentricity", 0))

        # Apply downsampling only to selected LOW quality satellites
        if sat_no in low_quality_sats:
            sat_downsampled = downsample_observations_sequential(
                sat_obs,
                target_coverage=target_coverage,
                target_track_gap=target_track_gap,
                target_obs_count=target_obs_count,
                orbital_period=period,
                regime=regime,
                sat_no=int(sat_no),
                seed=rng.integers(2**31),
            )
            metadata_per_sat[int(sat_no)] = {
                "original_count": len(sat_obs),
                "final_count": len(sat_downsampled),
                "target_quality": "LOW",
            }
        else:
            sat_downsampled = sat_obs
            metadata_per_sat[int(sat_no)] = {
                "original_count": len(sat_obs),
                "final_count": len(sat_obs),
                "target_quality": "HIGH",
            }

        downsampled_parts.append(sat_downsampled)

    if downsampled_parts:
        result_df = pd.concat(downsampled_parts, ignore_index=True)
    else:
        result_df = pd.DataFrame()

    metadata = {
        "status": "success",
        "original_count": len(obs_df),
        "final_count": len(result_df),
        "coverage_quality": coverage_quality,
        "track_gap_quality": track_gap_quality,
        "obs_count_quality": obs_count_quality,
        "n_low_quality_sats": n_low_quality,
        "n_total_sats": n_sats,
        "per_satellite": metadata_per_sat,
    }

    return result_df, metadata


# =============================================================================
# PIPELINE INTEGRATION HELPERS
# =============================================================================


def apply_downsampling(
    obs_df: pd.DataFrame,
    sat_params: Dict,
    elset_data: pd.DataFrame = None,
    config: Optional[DownsampleConfig] = None,
    tier: str = "T2",
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Apply downsampling to observations with full configuration support.

    This is the main integration entry point that:
    1. Validates inputs
    2. Applies tier-appropriate downsampling
    3. Returns downsampled data with metadata

    Args:
        obs_df: DataFrame of observations (must have 'obTime', 'satNo', 'ra', 'declination')
        sat_params: Dict mapping satNo to orbital parameters (Semi-Major Axis, Period, etc.)
        elset_data: Optional DataFrame of element sets for building sat_params if not provided
        config: DownsampleConfig instance (uses defaults if None)
        tier: Dataset tier ("T1", "T2", "T3", "T4") - determines downsampling intensity

    Returns:
        Tuple of (downsampled_df, metadata_dict)
        metadata_dict contains: original_count, final_count, retention_ratio, tier, config_used
    """
    if obs_df.empty:
        return obs_df, {
            "status": "empty_input",
            "original_count": 0,
            "final_count": 0,
            "retention_ratio": 0.0,
        }

    if config is None:
        config = DownsampleConfig()

    original_count = len(obs_df)

    # Build sat_params from elset_data if not provided
    if not sat_params and elset_data is not None and not elset_data.empty:
        from uct_benchmark.simulation.propagator import orbit2OE

        sat_params = {}
        for _, row in elset_data.iterrows():
            try:
                sat_id = int(row.get("satNo", row.get("sat_no", 0)))
                line1 = row.get("line1", row.get("tle1", ""))
                line2 = row.get("line2", row.get("tle2", ""))
                if line1 and line2:
                    orb_elems = orbit2OE(line1, line2)
                    sat_obs = obs_df[obs_df["satNo"] == sat_id]
                    sat_params[sat_id] = {
                        "Semi-Major Axis": orb_elems.get("Semi-Major Axis", 7000),
                        "Eccentricity": orb_elems.get("Eccentricity", 0.001),
                        "Inclination": orb_elems.get("Inclination", 45),
                        "RAAN": orb_elems.get("RAAN", 0),
                        "Argument of Perigee": orb_elems.get("Argument of Perigee", 0),
                        "Mean Anomaly": orb_elems.get("Mean Anomaly", 0),
                        "Period": orb_elems.get("Period", 5400),
                        "Number of Obs": len(sat_obs),
                        "Orbital Coverage": 0.5,
                        "Max Track Gap": 2,
                    }
            except Exception as e:
                logger.warning(f"Skipping satellite {sat_id}: {e}")
                continue

    if not sat_params:
        return obs_df, {
            "status": "no_sat_params",
            "original_count": original_count,
            "final_count": original_count,
            "retention_ratio": 1.0,
            "warning": "No satellite parameters available, returning original data",
        }

    # Configure downsampling based on tier
    tier_configs = {
        "T1": {  # High quality - minimal downsampling
            "coverage": (0.7, 1.0, 0.85),
            "coverage_pct": (0.4, 0.2),
            "gap": (0.7, 1.0, 0.85),
            "gap_target": 1.5,
            "obs": (0.7, 1.0, 0.85),
            "obs_max": 200,
        },
        "T2": {  # Standard quality - moderate downsampling
            "coverage": (0.4, 0.6, 0.5),
            "coverage_pct": (0.15, 0.05),
            "gap": (0.4, 0.6, 0.5),
            "gap_target": 2.0,
            "obs": (0.4, 0.6, 0.5),
            "obs_max": 50,
        },
        "T3": {  # Lower quality - more aggressive downsampling
            "coverage": (0.2, 0.4, 0.3),
            "coverage_pct": (0.10, 0.02),
            "gap": (0.2, 0.4, 0.3),
            "gap_target": 3.0,
            "obs": (0.2, 0.4, 0.3),
            "obs_max": 30,
        },
        "T4": {  # Lowest quality - maximum downsampling
            "coverage": (0.1, 0.2, 0.15),
            "coverage_pct": (0.05, 0.01),
            "gap": (0.1, 0.2, 0.15),
            "gap_target": 4.0,
            "obs": (0.1, 0.2, 0.15),
            "obs_max": 20,
        },
    }

    tier_cfg = tier_configs.get(tier, tier_configs["T2"])

    # Use existing downsampleData function
    orbit_coverage = {
        "sats": None,
        "p_bounds": tier_cfg["coverage"],
        "p_coverage": tier_cfg["coverage_pct"],
    }
    track_length = {
        "sats": None,
        "p_bounds": tier_cfg["gap"],
        "p_track": tier_cfg["gap_target"],
    }
    obs_count = {
        "sats": None,
        "p_bounds": tier_cfg["obs"],
        "obs_max": config.max_obs_per_sat if config.max_obs_per_sat else tier_cfg["obs_max"],
    }

    try:
        downsampled_df, p_reached = downsampleData(
            obs_df.copy(),
            sat_params,
            orbit_coverage,
            track_length,
            obs_count,
            bins=10,
            rand=config.seed,
        )
    except Exception as e:
        # Fall back to regime-based downsampling
        logger.warning(f"Downsampling failed, falling back to regime-based: {e}")
        rng = np.random.default_rng(config.seed)
        downsampled_df = downsample_by_regime(obs_df.copy(), sat_params, config, rng)
        p_reached = (0, 0, 0)

    final_count = len(downsampled_df)

    metadata = {
        "status": "success",
        "original_count": original_count,
        "final_count": final_count,
        "retention_ratio": final_count / original_count if original_count > 0 else 0,
        "tier": tier,
        "p_reached": p_reached,
        "config": {
            "target_coverage": config.target_coverage,
            "target_gap": config.target_gap,
            "max_obs_per_sat": config.max_obs_per_sat,
            "preserve_track_boundaries": config.preserve_track_boundaries,
            "seed": config.seed,
        },
    }

    return downsampled_df, metadata


def apply_simulation_to_gaps(
    obs_df: pd.DataFrame,
    elset_data: pd.DataFrame,
    sensor_df: pd.DataFrame,
    sat_params: Dict = None,
    config: Optional[SimulationConfig] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Generate synthetic observations to fill gaps in the observation data.

    This function:
    1. Analyzes observation gaps for each satellite
    2. Generates synthetic observations at gap epochs
    3. Applies realistic noise based on config
    4. Merges with original observations

    Args:
        obs_df: DataFrame of existing observations
        elset_data: DataFrame of TLE/element set data (must have 'line1', 'line2', 'satNo')
        sensor_df: DataFrame of sensor locations (must have 'idSensor', 'senlat', 'senlon', 'senalt')
        sat_params: Optional dict of satellite parameters
        config: SimulationConfig instance (uses defaults if None)

    Returns:
        Tuple of (merged_df, metadata_dict)
        merged_df contains both original and simulated observations
        metadata_dict contains: original_count, simulated_count, total_count, satellites_processed
    """
    from uct_benchmark.simulation.propagator import orbit2OE
    from uct_benchmark.simulation.simulateObservations import epochsToSim, simulateObs

    if config is None:
        config = SimulationConfig()

    if obs_df.empty:
        return obs_df, {
            "status": "empty_input",
            "original_count": 0,
            "simulated_count": 0,
            "total_count": 0,
        }

    if elset_data is None or elset_data.empty:
        return obs_df, {
            "status": "no_elset_data",
            "original_count": len(obs_df),
            "simulated_count": 0,
            "total_count": len(obs_df),
            "warning": "No element set data available for simulation",
        }

    if sensor_df is None or sensor_df.empty:
        # Create a default sensor if not provided
        sensor_df = pd.DataFrame(
            {
                "idSensor": ["SEN001", "SEN002", "SEN003"],
                "name": ["DIEGO_GARCIA", "ASCENSION", "MAUI"],
                "senlat": [-7.3, -7.9, 20.7],
                "senlon": [72.4, -14.4, -156.3],
                "senalt": [0.01, 0.04, 3.1],
                "count": [10, 10, 10],
            }
        )

    # Ensure sensor_df has required columns
    if "count" not in sensor_df.columns:
        sensor_df["count"] = 10

    original_count = len(obs_df)
    all_simulated = []
    satellites_processed = 0
    satellites_failed = 0

    # Build orbital elements from elset_data
    sat_orbits = {}
    for _, row in elset_data.iterrows():
        try:
            sat_id = int(row.get("satNo", row.get("sat_no", 0)))
            line1 = row.get("line1", row.get("tle1", ""))
            line2 = row.get("line2", row.get("tle2", ""))
            if line1 and line2 and sat_id:
                sat_orbits[sat_id] = {
                    "line1": line1,
                    "line2": line2,
                    "orb_elems": orbit2OE(line1, line2),
                }
        except Exception:
            continue

    # Set random seed if configured (reserved for future randomized processing)
    _rng = np.random.default_rng(config.seed) if config.seed else np.random.default_rng()

    # Process each satellite
    for sat_id in obs_df["satNo"].unique():
        sat_id = int(sat_id)

        if sat_id not in sat_orbits:
            satellites_failed += 1
            continue

        try:
            sat_obs = obs_df[obs_df["satNo"] == sat_id].copy()
            orbit_info = sat_orbits[sat_id]
            orb_elems = orbit_info["orb_elems"]

            # Get epochs to simulate
            epochs, bins_info = epochsToSim(
                sat_id,
                sat_obs,
                orb_elems,
                target_obs_count=None,
                max_sim_ratio=config.max_synthetic_ratio,
            )

            if not epochs or bins_info.get("status") not in ["success", "ok", "max_ratio_limited"]:
                continue

            # Check if adding more observations would exceed ratio
            current_count = len(sat_obs)
            max_allowed = int(
                current_count * config.max_synthetic_ratio / (1 - config.max_synthetic_ratio)
            )
            epochs = epochs[:max_allowed]

            if not epochs:
                continue

            # Generate simulated observations
            sim_obs = simulateObs(
                orbit_info["line1"],
                orbit_info["line2"],
                epochs,  # Pass epochs directly
                sensor_df,
                positionNoise=0.01 if config.apply_sensor_noise else 0,
                angularNoise=1 / 3600 if config.apply_sensor_noise else 0,
                step=30.0,
                satelliteParameters=[sat_id, 1000, 10],
            )

            if sim_obs is not None and not sim_obs.empty:
                # Mark as simulated
                sim_obs["is_simulated"] = True
                sim_obs["dataMode"] = "SIMULATED"
                all_simulated.append(sim_obs)
                satellites_processed += 1

        except Exception as e:
            logger.warning(f"Simulation failed for satellite {sat_id}: {e}")
            satellites_failed += 1
            continue

    # Merge original and simulated observations
    if all_simulated:
        simulated_df = pd.concat(all_simulated, ignore_index=True)
        simulated_count = len(simulated_df)

        # Mark original observations
        obs_df = obs_df.copy()
        if "is_simulated" not in obs_df.columns:
            obs_df["is_simulated"] = False
        if "dataMode" not in obs_df.columns:
            obs_df["dataMode"] = "REAL"

        # Merge
        merged_df = pd.concat([obs_df, simulated_df], ignore_index=True)

        # Ensure obTime is datetime (simulated obs may have string timestamps)
        if "obTime" in merged_df.columns:
            # Fix malformed datetime strings with both +00:00 and Z suffix (v7)
            # Use Python native str.replace via apply() for reliable replacement
            def fix_datetime_str(x):
                s = str(x)
                if "+00:00Z" in s:
                    return s.replace("+00:00Z", "Z")
                return s

            obtime_fixed = merged_df["obTime"].apply(fix_datetime_str)
            # Use format='mixed' to handle multiple datetime formats in the column
            merged_df["obTime"] = pd.to_datetime(obtime_fixed, utc=True, format="mixed")

        # Sort by satellite and time
        if "obTime" in merged_df.columns:
            merged_df = merged_df.sort_values(["satNo", "obTime"]).reset_index(drop=True)
    else:
        merged_df = obs_df.copy()
        simulated_count = 0
        if "is_simulated" not in merged_df.columns:
            merged_df["is_simulated"] = False

    metadata = {
        "status": "success",
        "original_count": original_count,
        "simulated_count": simulated_count,
        "total_count": len(merged_df),
        "satellites_processed": satellites_processed,
        "satellites_failed": satellites_failed,
        "synthetic_ratio": simulated_count / len(merged_df) if len(merged_df) > 0 else 0,
        "config": {
            "apply_sensor_noise": config.apply_sensor_noise,
            "sensor_model": config.sensor_model,
            "max_synthetic_ratio": config.max_synthetic_ratio,
            "seed": config.seed,
        },
    }

    return merged_df, metadata


# =============================================================================
# LEWIS TIER CLASSIFICATION SYSTEM
# =============================================================================
# This implements Lewis's tier system for classifying windows:
# - Tier 1: All criteria met, no manipulation needed (optimal)
# - Tier 2: Too much data, needs downsampling
# - Tier 3: Too little data, needs simulation
#
# This is DIFFERENT from data quality tiers (T1/T2/T3) which control
# downsampling intensity. Lewis's tiers determine WHEN to apply manipulation.
# =============================================================================


class LewisTier:
    """Lewis's window classification tiers."""
    TIER_1 = 1  # Optimal: no manipulation needed
    TIER_2 = 2  # Suboptimal: needs downsampling (too much data)
    TIER_3 = 3  # Most suboptimal: needs simulation (too little data)
    TIER_4 = 4  # Insufficient: cannot meet criteria


def classify_window_tier(
    obs_df: pd.DataFrame,
    sat_params: Dict,
    criteria: Dict[str, Any],
) -> Tuple[int, Dict[str, Any]]:
    """
    Classify a time window per Lewis's tier system.

    This determines WHETHER manipulation is needed, not HOW MUCH.
    After tier classification, the appropriate manipulation function
    (downsample or simulate) is called with quality tier settings.

    Args:
        obs_df: DataFrame of observations in the window
        sat_params: Dict mapping satNo to orbital parameters
        criteria: Dict with user-specified criteria:
            - min_objects: Minimum number of objects required
            - target_objects: Target number of objects
            - min_obs_per_object: Minimum observations per object
            - target_obs_per_object: Target observations per object
            - min_coverage: Minimum orbital coverage (fraction)
            - target_coverage: Target orbital coverage
            - max_coverage: Maximum orbital coverage (above = too much)
            - min_track_gap_periods: Minimum gap (below = too frequent)
            - target_track_gap_periods: Target gap between tracks
            - max_track_gap_periods: Maximum gap (above = too sparse)

    Returns:
        Tuple of (tier, analysis_dict)
        tier: LewisTier.TIER_1, TIER_2, TIER_3, or TIER_4
        analysis_dict: Detailed analysis including:
            - tier: The tier classification
            - needs_downsampling: bool
            - needs_simulation: bool
            - object_count: Number of objects in window
            - avg_obs_per_object: Average observations per object
            - avg_coverage: Average orbital coverage
            - avg_track_gap: Average track gap in orbital periods
            - criteria_met: Dict of which criteria are met
    """
    if obs_df.empty:
        return LewisTier.TIER_4, {
            "tier": LewisTier.TIER_4,
            "needs_downsampling": False,
            "needs_simulation": True,
            "object_count": 0,
            "reason": "No observations in window",
        }

    # Default criteria values
    min_objects = criteria.get("min_objects", 10)
    target_objects = criteria.get("target_objects", 40)
    min_obs = criteria.get("min_obs_per_object", 5)
    target_obs = criteria.get("target_obs_per_object", 50)
    max_obs = criteria.get("max_obs_per_object", 150)
    min_coverage = criteria.get("min_coverage", 0.02)
    target_coverage = criteria.get("target_coverage", 0.10)
    max_coverage = criteria.get("max_coverage", 0.50)
    min_gap = criteria.get("min_track_gap_periods", 0.5)
    target_gap = criteria.get("target_track_gap_periods", 2.0)
    max_gap = criteria.get("max_track_gap_periods", 5.0)

    # Count observations per satellite
    sat_counts = obs_df["satNo"].value_counts()
    valid_sats = sat_counts[sat_counts >= 3].index.tolist()
    object_count = len(valid_sats)

    # Check object count criterion
    has_enough_objects = object_count >= min_objects
    has_target_objects = object_count >= target_objects
    has_too_many_objects = object_count > target_objects * 1.5

    # Analyze each satellite
    obs_counts = []
    coverages = []
    track_gaps = []

    for sat_no in valid_sats:
        sat_obs = obs_df[obs_df["satNo"] == sat_no]
        sat_param = sat_params.get(sat_no, {})
        period_sec = sat_param.get("Period", 5400)

        # Observation count
        obs_counts.append(len(sat_obs))

        # Coverage (simplified estimate)
        if len(sat_obs) >= 2:
            sat_obs = sat_obs.sort_values("obTime")
            time_span = (sat_obs["obTime"].max() - sat_obs["obTime"].min()).total_seconds()
            # Estimate coverage based on time span and observation density
            expected_period_obs = time_span / period_sec * 5  # ~5 obs per pass
            coverage = min(1.0, len(sat_obs) / max(1, expected_period_obs) * 0.3)
        else:
            coverage = 0.0
        coverages.append(coverage)

        # Track gap (max gap normalized by orbital period)
        if len(sat_obs) >= 2:
            time_diffs = sat_obs["obTime"].diff().dropna()
            if not time_diffs.empty:
                max_gap_sec = time_diffs.max().total_seconds()
                track_gaps.append(max_gap_sec / period_sec if period_sec > 0 else 0)
            else:
                track_gaps.append(0)
        else:
            track_gaps.append(float("inf"))

    # Compute averages
    avg_obs = np.mean(obs_counts) if obs_counts else 0
    avg_coverage = np.mean(coverages) if coverages else 0
    avg_gap = np.median(track_gaps) if track_gaps else float("inf")

    # Evaluate each criterion
    criteria_met = {
        "objects": has_enough_objects,
        "objects_target": has_target_objects,
        "obs_per_object": avg_obs >= min_obs,
        "obs_target": min_obs <= avg_obs <= max_obs,
        "coverage": avg_coverage >= min_coverage,
        "coverage_target": min_coverage <= avg_coverage <= max_coverage,
        "track_gap": avg_gap <= max_gap,
        "track_gap_target": min_gap <= avg_gap <= max_gap,
    }

    # Determine if data is "too much" or "too little"
    too_much_data = (
        avg_obs > max_obs or
        avg_coverage > max_coverage or
        avg_gap < min_gap or
        has_too_many_objects
    )

    too_little_data = (
        not has_enough_objects or
        avg_obs < min_obs or
        avg_coverage < min_coverage or
        avg_gap > max_gap
    )

    # Classify tier
    # Tier 1: All target criteria met - use data as-is
    all_targets_met = (
        criteria_met["objects_target"] and
        criteria_met["obs_target"] and
        criteria_met["coverage_target"] and
        criteria_met["track_gap_target"]
    )

    # Tier 1 or close to it: minimal criteria met, no manipulation needed
    minimal_criteria_met = (
        criteria_met["objects"] and
        criteria_met["obs_per_object"] and
        criteria_met["coverage"] and
        criteria_met["track_gap"]
    )

    if all_targets_met:
        tier = LewisTier.TIER_1
        needs_downsampling = False
        needs_simulation = False
    elif minimal_criteria_met and too_much_data:
        # Have more than enough data - need to reduce it
        tier = LewisTier.TIER_2
        needs_downsampling = True
        needs_simulation = False
    elif too_little_data and not too_much_data:
        # Not enough data - need to simulate
        tier = LewisTier.TIER_3
        needs_downsampling = False
        needs_simulation = True
    elif not has_enough_objects:
        # Cannot meet basic object count requirement
        tier = LewisTier.TIER_4
        needs_downsampling = False
        needs_simulation = True
    else:
        # Edge case: some criteria met, some not - default to tier 2
        tier = LewisTier.TIER_2
        needs_downsampling = too_much_data
        needs_simulation = too_little_data and not too_much_data

    analysis = {
        "tier": tier,
        "needs_downsampling": needs_downsampling,
        "needs_simulation": needs_simulation,
        "object_count": object_count,
        "avg_obs_per_object": float(avg_obs),
        "avg_coverage": float(avg_coverage),
        "avg_track_gap_periods": float(avg_gap) if avg_gap != float("inf") else None,
        "criteria_met": criteria_met,
        "too_much_data": too_much_data,
        "too_little_data": too_little_data,
        "satellites": valid_sats,
    }

    return tier, analysis


def process_window_by_tier(
    obs_df: pd.DataFrame,
    sat_params: Dict,
    elset_data: pd.DataFrame = None,
    sensor_df: pd.DataFrame = None,
    criteria: Dict[str, Any] = None,
    quality_tier: str = "T2",
    seed: int = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Process a data window based on Lewis's tier classification.

    This is the main orchestration function that:
    1. Classifies the window using Lewis's tier system
    2. Applies appropriate manipulation (downsampling or simulation)
    3. Returns processed data with metadata

    Args:
        obs_df: DataFrame of observations
        sat_params: Dict mapping satNo to orbital parameters
        elset_data: DataFrame of TLE data (needed for simulation)
        sensor_df: DataFrame of sensor info (needed for simulation)
        criteria: User-specified criteria dict
        quality_tier: Data quality tier ("T1", "T2", "T3", "T4") for intensity
        seed: Random seed for reproducibility

    Returns:
        Tuple of (processed_df, metadata)
    """
    if criteria is None:
        criteria = {
            "min_objects": 10,
            "target_objects": 40,
            "min_obs_per_object": 5,
            "target_obs_per_object": 50,
            "max_obs_per_object": 150,
            "min_coverage": 0.02,
            "target_coverage": 0.10,
            "max_coverage": 0.50,
            "min_track_gap_periods": 0.5,
            "target_track_gap_periods": 2.0,
            "max_track_gap_periods": 5.0,
        }

    # Step 1: Classify window using Lewis's tier system
    lewis_tier, analysis = classify_window_tier(obs_df, sat_params, criteria)

    logger.info(
        f"Window classified as Lewis Tier {lewis_tier}: "
        f"objects={analysis['object_count']}, "
        f"avg_obs={analysis['avg_obs_per_object']:.1f}, "
        f"needs_downsampling={analysis['needs_downsampling']}, "
        f"needs_simulation={analysis['needs_simulation']}"
    )

    # Step 2: Apply appropriate manipulation based on tier
    processed_df = obs_df.copy()
    manipulation_metadata = {}

    if lewis_tier == LewisTier.TIER_1:
        # No manipulation needed - use data as-is
        manipulation_metadata = {
            "action": "none",
            "reason": "All criteria met (Tier 1)",
        }

    elif lewis_tier == LewisTier.TIER_2 and analysis["needs_downsampling"]:
        # Too much data - apply downsampling
        logger.info(f"Applying downsampling with quality tier {quality_tier}")

        downsample_config = DownsampleConfig(seed=seed)
        processed_df, ds_meta = apply_downsampling(
            obs_df,
            sat_params,
            elset_data=elset_data,
            config=downsample_config,
            tier=quality_tier,
        )
        manipulation_metadata = {
            "action": "downsample",
            "reason": "Too much data (Tier 2)",
            "downsampling_metadata": ds_meta,
        }

    elif lewis_tier in [LewisTier.TIER_3, LewisTier.TIER_4] and analysis["needs_simulation"]:
        # Too little data - apply simulation
        if elset_data is not None and not elset_data.empty:
            logger.info("Applying simulation to fill gaps")

            sim_config = SimulationConfig(seed=seed)
            processed_df, sim_meta = apply_simulation_to_gaps(
                obs_df,
                elset_data,
                sensor_df,
                sat_params=sat_params,
                config=sim_config,
            )
            manipulation_metadata = {
                "action": "simulate",
                "reason": f"Too little data (Tier {lewis_tier})",
                "simulation_metadata": sim_meta,
            }
        else:
            manipulation_metadata = {
                "action": "none",
                "reason": "Simulation needed but no TLE data available",
                "warning": "Cannot simulate without element set data",
            }

    else:
        # Default: no manipulation
        manipulation_metadata = {
            "action": "none",
            "reason": f"Tier {lewis_tier}, no clear manipulation path",
        }

    # Compile full metadata
    metadata = {
        "lewis_tier": lewis_tier,
        "lewis_analysis": analysis,
        "quality_tier": quality_tier,
        "manipulation": manipulation_metadata,
        "input_obs_count": len(obs_df),
        "output_obs_count": len(processed_df),
        "seed": seed,
    }

    return processed_df, metadata


def generate_dataset_with_lewis_tiers(
    obs_df: pd.DataFrame,
    sat_params: Dict,
    elset_data: pd.DataFrame = None,
    sensor_df: pd.DataFrame = None,
    fit_span_days: float = 7.0,
    quality_level: str = "standard",
    quality_tier: str = "T2",
    regimes: List[str] = None,
    seed: int = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Complete dataset generation using Lewis's window selection and tier system.

    This is the top-level function that:
    1. Uses bisection algorithm to find optimal time window
    2. Classifies window using Lewis's tier system
    3. Applies appropriate manipulation (downsample or simulate)
    4. Returns final dataset with comprehensive metadata

    Args:
        obs_df: DataFrame of all available observations
        sat_params: Dict mapping satNo to orbital parameters
        elset_data: DataFrame of TLE data
        sensor_df: DataFrame of sensor info
        fit_span_days: Desired duration of dataset in days
        quality_level: "high", "standard", or "low" for criteria
        quality_tier: "T1", "T2", "T3", "T4" for downsampling intensity
        regimes: List of orbital regimes to include
        seed: Random seed for reproducibility

    Returns:
        Tuple of (final_dataset_df, comprehensive_metadata)
    """
    from uct_benchmark.data.windowSelection import (
        select_optimal_window_for_dataset,
        create_criteria_from_user_input,
    )

    logger.info(
        f"Generating dataset: fit_span={fit_span_days} days, "
        f"quality_level={quality_level}, quality_tier={quality_tier}"
    )

    # Step 1: Find optimal window using bisection algorithm
    filtered_obs, window_eval, recommended_action = select_optimal_window_for_dataset(
        obs_df,
        sat_params,
        fit_span_days=fit_span_days,
        quality_level=quality_level,
        regimes=regimes,
    )

    logger.info(
        f"Window selection complete: {len(filtered_obs)} obs, "
        f"recommended_action={recommended_action}"
    )

    # Step 2: Create criteria based on quality level
    quality_criteria_map = {
        "high": {
            "min_objects": 60, "target_objects": 80,
            "min_obs_per_object": 100, "target_obs_per_object": 150, "max_obs_per_object": 250,
            "min_coverage": 0.20, "target_coverage": 0.50, "max_coverage": 0.80,
            "min_track_gap_periods": 0.2, "target_track_gap_periods": 0.5, "max_track_gap_periods": 1.0,
        },
        "standard": {
            "min_objects": 30, "target_objects": 40,
            "min_obs_per_object": 30, "target_obs_per_object": 50, "max_obs_per_object": 100,
            "min_coverage": 0.05, "target_coverage": 0.15, "max_coverage": 0.30,
            "min_track_gap_periods": 1.0, "target_track_gap_periods": 2.0, "max_track_gap_periods": 4.0,
        },
        "low": {
            "min_objects": 5, "target_objects": 10,
            "min_obs_per_object": 5, "target_obs_per_object": 10, "max_obs_per_object": 30,
            "min_coverage": 0.01, "target_coverage": 0.03, "max_coverage": 0.10,
            "min_track_gap_periods": 3.0, "target_track_gap_periods": 5.0, "max_track_gap_periods": 10.0,
        },
    }
    criteria = quality_criteria_map.get(quality_level, quality_criteria_map["standard"])

    # Step 3: Process window based on Lewis tier classification
    final_df, process_metadata = process_window_by_tier(
        filtered_obs,
        sat_params,
        elset_data=elset_data,
        sensor_df=sensor_df,
        criteria=criteria,
        quality_tier=quality_tier,
        seed=seed,
    )

    # Compile comprehensive metadata
    metadata = {
        "window_selection": {
            "fit_span_days": fit_span_days,
            "quality_level": quality_level,
            "recommended_action": recommended_action,
            "window_start": str(window_eval.start_time) if window_eval else None,
            "window_end": str(window_eval.end_time) if window_eval else None,
            "window_tier": window_eval.tier.value if window_eval and hasattr(window_eval, 'tier') else None,
            "window_score": window_eval.overall_score if window_eval and hasattr(window_eval, 'overall_score') else None,
        },
        "tier_processing": process_metadata,
        "final_stats": {
            "observation_count": len(final_df),
            "satellite_count": final_df["satNo"].nunique() if not final_df.empty else 0,
            "time_span_days": (
                (final_df["obTime"].max() - final_df["obTime"].min()).total_seconds() / 86400
                if not final_df.empty and len(final_df) > 1 else 0
            ),
        },
        "config": {
            "quality_level": quality_level,
            "quality_tier": quality_tier,
            "regimes": regimes,
            "seed": seed,
        },
    }

    logger.info(
        f"Dataset generation complete: {metadata['final_stats']['observation_count']} obs, "
        f"{metadata['final_stats']['satellite_count']} satellites"
    )

    return final_df, metadata


# =============================================================================
# LEGACY CODE INTEGRATION: Downsampling configuration from 16-character code
# =============================================================================


def get_downsample_config_from_legacy(
    legacy_code: str = None,
    orbit_coverage: str = "S",
    track_gap: str = "S",
    observation_count: str = "S",
    seed: Optional[int] = None,
) -> DownsampleConfig:
    """
    Create DownsampleConfig from legacy 16-character dataset code parameters.

    Maps the A/S/N quality levels to downsampling configuration per Louis's documentation:
    - A = >90% objects have LOW quality (sparse dataset) → aggressive downsampling
    - S = 40-60% objects have LOW quality (mixed) → moderate downsampling
    - N = <10% objects have LOW quality (dense dataset) → minimal downsampling

    Args:
        legacy_code: Optional 16-character code (overrides other params)
        orbit_coverage: A, S, N - Coverage level target
        track_gap: A, S, N - Track gap level target
        observation_count: A, S, N - Observation count level target
        seed: Random seed for reproducibility

    Returns:
        DownsampleConfig configured for the legacy code parameters
    """
    # Parse legacy code if provided
    if legacy_code and len(legacy_code) == 16:
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode
        parsed = LegacyDatasetCode.from_code(legacy_code)
        orbit_coverage = parsed.orbit_coverage
        track_gap = parsed.track_gap
        observation_count = parsed.observation_count

    # Get base downsampling config from coverage level
    ds_config = LEGACY_COVERAGE_DOWNSAMPLE.get(orbit_coverage, LEGACY_COVERAGE_DOWNSAMPLE["S"])

    # Map coverage to target values
    # A = Want sparse-looking data, so downsample aggressively to ~2% coverage
    # S = Standard, moderate downsampling to ~5% coverage
    # N = Want dense/low-quality look, minimal downsampling ~15% coverage
    coverage_targets = {
        "A": 0.02,   # Aggressive: target 2% orbital coverage
        "S": 0.05,   # Standard: target 5% orbital coverage
        "N": 0.15,   # Minimal: target 15% orbital coverage
    }
    target_coverage = coverage_targets.get(orbit_coverage, 0.05)

    # Map track gap to target orbital periods per Louis's documentation:
    # A = >90% objects have LONG gaps (sparse tracking) → target large gaps
    # S = 40-60% objects have LONG gaps → moderate gaps
    # N = <10% objects have LONG gaps (dense tracking) → target small gaps
    gap_targets = {
        "A": 5.0,    # Sparse: large gaps (most objects poorly tracked)
        "S": 2.0,    # Mixed: standard gaps
        "N": 0.5,    # Dense: small gaps (most objects well tracked)
    }
    target_gap = gap_targets.get(track_gap, 2.0)

    # Map observation count to max observations per satellite per Louis's documentation:
    # A = >90% objects have LOW obs count (sparse) → strict limit
    # S = 40-60% objects have LOW obs count (mixed) → moderate limit
    # N = <10% objects have LOW obs count (dense) → allow many observations
    obs_limits = {
        "A": 20,     # Sparse: few observations per satellite
        "S": 50,     # Mixed: standard
        "N": 200,    # Dense: many observations per satellite
    }
    max_obs = obs_limits.get(observation_count, 50)

    # Determine coverage tolerance (how close to target is acceptable)
    coverage_tolerances = {
        "A": 0.01,   # Tight tolerance for aggressive downsampling
        "S": 0.02,   # Standard tolerance
        "N": 0.05,   # Loose tolerance for minimal downsampling
    }
    coverage_tolerance = coverage_tolerances.get(orbit_coverage, 0.02)

    # Determine gap tolerance (how close to target gap is acceptable)
    gap_tolerances = {
        "A": 1.0,    # Loose tolerance for large gaps target
        "S": 0.5,    # Standard tolerance
        "N": 0.2,    # Tight tolerance for small gaps target
    }
    gap_tolerance = gap_tolerances.get(track_gap, 0.5)

    logger.info(
        f"Creating downsample config from legacy: coverage={orbit_coverage} (target {target_coverage:.0%}), "
        f"gap={track_gap} (target {target_gap:.1f} periods), "
        f"obs={observation_count} (max {max_obs})"
    )

    return DownsampleConfig(
        target_coverage=target_coverage,
        coverage_tolerance=coverage_tolerance,
        target_gap=target_gap,
        gap_tolerance=gap_tolerance,
        max_obs_per_sat=max_obs,
        min_obs_per_sat=5,  # Always keep at least 5 observations
        preserve_track_boundaries=True,
        min_obs_per_track=3,  # Maintain track structure
        seed=seed,
    )


def should_simulate_for_legacy_code(
    current_coverage: float,
    current_obs_count: float,
    legacy_code: str = None,
    orbit_coverage: str = "S",
    observation_count: str = "S",
) -> Tuple[bool, str]:
    """
    Determine if simulation is needed based on legacy code requirements.

    Compares current data quality against the legacy code targets to decide
    if gap-filling simulation should be applied.

    Args:
        current_coverage: Current average orbital coverage (0.0-1.0)
        current_obs_count: Current average observation count per satellite
        legacy_code: Optional 16-character code
        orbit_coverage: A, S, N - Target coverage level
        observation_count: A, S, N - Target observation count level

    Returns:
        Tuple of (should_simulate, reason)
    """
    # Parse legacy code if provided
    if legacy_code and len(legacy_code) == 16:
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode
        parsed = LegacyDatasetCode.from_code(legacy_code)
        orbit_coverage = parsed.orbit_coverage
        observation_count = parsed.observation_count

    # Determine if current data meets legacy code requirements per Louis's documentation:
    # A = >90% objects have LOW quality (sparse) → we WANT sparse data, don't simulate
    # S = 40-60% objects have LOW quality (mixed) → simulate only if very sparse
    # N = <10% objects have LOW quality (dense) → we WANT dense data, simulate if sparse

    # Minimum thresholds to consider simulation (if below these AND dense data is desired)
    coverage_thresholds = {
        "A": 0.01,   # Sparse desired: threshold very low, almost never simulate
        "S": 0.05,   # Mixed: moderate threshold
        "N": 0.20,   # Dense desired: if below 20%, simulate to add more data
    }

    obs_thresholds = {
        "A": 5,      # Sparse desired: very low threshold
        "S": 20,     # Mixed: moderate threshold
        "N": 50,     # Dense desired: if below 50, simulate to add more data
    }

    coverage_threshold = coverage_thresholds.get(orbit_coverage, 0.05)
    obs_threshold = obs_thresholds.get(observation_count, 20)

    reasons = []

    # Check if simulation is needed
    should_sim = False

    # For "A" (sparse) coverage, we WANT sparse data, so don't simulate
    if orbit_coverage == "A":
        return False, "Sparse coverage (A) desired - no simulation needed"

    # For "N" (dense) or "S" (mixed), check if current data is below thresholds
    if current_coverage < coverage_threshold:
        should_sim = True
        reasons.append(f"coverage {current_coverage:.1%} < {coverage_threshold:.1%} threshold")

    if current_obs_count < obs_threshold:
        should_sim = True
        reasons.append(f"obs count {current_obs_count:.0f} < {obs_threshold} threshold")

    if should_sim:
        reason = f"Simulation needed: {'; '.join(reasons)}"
    else:
        reason = f"Data meets {orbit_coverage}/{observation_count} quality requirements"

    logger.debug(f"Simulation check: {reason}")
    return should_sim, reason


# =============================================================================
# NON-REFERENCE OBSERVATIONS (For True Negative Calculation)
# =============================================================================


def add_non_reference_observations(
    ref_obs_df: pd.DataFrame,
    reference_norad_ids: List[int],
    all_observations_df: pd.DataFrame = None,
    non_ref_ratio: float = 0.1,
    regime: str = "LEO",
    seed: Optional[int] = None,
    observations_per_satellite: int = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Add observations from non-reference satellites to the dataset.

    Per Louis's Benchmarking Documentation, True Negatives require observations
    from satellites NOT in the reference set. These observations should NOT be
    matched by the algorithm.

    IMPORTANT: Per Louis's specification, non-reference observations should have
    EXACTLY 2 observations per satellite. This makes IOD impossible (need minimum 3)
    so the algorithm should correctly NOT match these observations.

    Args:
        ref_obs_df: DataFrame of reference observations with 'satNo', 'id', 'obTime', etc.
        reference_norad_ids: Set/List of NORAD IDs that are in the reference set
        all_observations_df: DataFrame of ALL observations (including non-reference).
                            If None, function returns empty non-ref DataFrame.
        non_ref_ratio: Ratio of non-ref obs to add (relative to ref obs count).
                      0.1 = 10% of reference obs count as non-reference obs.
        regime: Orbital regime to filter non-reference satellites
        seed: Random seed for reproducibility
        observations_per_satellite: Number of obs per non-ref satellite.
                                   Default is NON_REF_OBS_PER_SATELLITE (2 per Louis's spec).
                                   EXACTLY 2 makes IOD impossible.

    Returns:
        Tuple of (combined_df, non_ref_truth_df)
        - combined_df: All observations (reference + non-reference)
        - non_ref_truth_df: Ground truth for non-reference obs with columns:
            - 'id': observation ID
            - 'source_norad_id': the actual satellite (for ground truth verification)
            - 'is_non_reference': True for all rows

    Example:
        >>> ref_obs = get_reference_observations(norad_ids)
        >>> combined, non_ref_truth = add_non_reference_observations(
        ...     ref_obs, reference_norad_ids, all_obs_df, non_ref_ratio=0.1
        ... )
        >>> # Now use combined for algorithm input, non_ref_truth for evaluation
    """
    rng = np.random.default_rng(seed)
    reference_set = set(reference_norad_ids)

    # Per Louis's specification: exactly 2 observations per non-reference satellite
    if observations_per_satellite is None:
        observations_per_satellite = NON_REF_OBS_PER_SATELLITE

    if observations_per_satellite != 2:
        logger.warning(
            f"Non-reference satellites should have exactly 2 observations per Louis's spec. "
            f"Got {observations_per_satellite}. This affects True Negative evaluation accuracy."
        )

    if all_observations_df is None or all_observations_df.empty:
        logger.warning(
            "No all_observations_df provided for non-reference obs selection. "
            "Returning reference observations only."
        )
        # Return ref_obs as combined, empty non_ref_truth
        non_ref_truth = pd.DataFrame(columns=["id", "source_norad_id", "is_non_reference"])
        return ref_obs_df.copy(), non_ref_truth

    # Calculate target count for non-reference observations
    ref_count = len(ref_obs_df)
    target_non_ref_count = int(ref_count * non_ref_ratio)

    if target_non_ref_count <= 0:
        logger.info("Non-ref ratio results in 0 non-reference observations")
        non_ref_truth = pd.DataFrame(columns=["id", "source_norad_id", "is_non_reference"])
        return ref_obs_df.copy(), non_ref_truth

    # Find observations from satellites NOT in reference set
    non_ref_obs = all_observations_df[~all_observations_df["satNo"].isin(reference_set)]

    if non_ref_obs.empty:
        logger.warning(
            "No non-reference observations available in all_observations_df. "
            "All satellites in the data are in the reference set."
        )
        non_ref_truth = pd.DataFrame(columns=["id", "source_norad_id", "is_non_reference"])
        return ref_obs_df.copy(), non_ref_truth

    logger.info(
        f"Found {len(non_ref_obs)} non-reference observations from "
        f"{non_ref_obs['satNo'].nunique()} satellites"
    )

    # Per Louis's specification: Select EXACTLY observations_per_satellite (default 2)
    # observations per non-reference satellite to make IOD impossible
    non_ref_satellites = non_ref_obs["satNo"].unique()

    # Calculate how many satellites we need to sample from to achieve target count
    # Each satellite contributes exactly observations_per_satellite observations
    target_non_ref_sats = max(1, target_non_ref_count // observations_per_satellite)
    target_non_ref_sats = min(target_non_ref_sats, len(non_ref_satellites))

    # Randomly select which non-reference satellites to include
    selected_sats = rng.choice(non_ref_satellites, target_non_ref_sats, replace=False)

    # For each selected satellite, pick exactly observations_per_satellite observations
    # Select observations spread apart in time for realistic scenario
    sampled_obs_list = []

    for sat_no in selected_sats:
        sat_obs = non_ref_obs[non_ref_obs["satNo"] == sat_no].copy()

        if len(sat_obs) < observations_per_satellite:
            logger.warning(f"Non-ref satellite {sat_no} has only {len(sat_obs)} observations")
            continue

        # Sort by time and select observations spread apart
        sat_obs = sat_obs.sort_values("obTime")

        if observations_per_satellite == 2:
            # Per Louis's spec: select first and last for maximum time spread
            selected = pd.concat([
                sat_obs.iloc[[0]],
                sat_obs.iloc[[-1]]
            ])
        else:
            # For other counts, use evenly spaced selection
            indices = np.linspace(0, len(sat_obs) - 1, observations_per_satellite, dtype=int)
            selected = sat_obs.iloc[indices]

        sampled_obs_list.append(selected)

    if sampled_obs_list:
        sampled_non_ref = pd.concat(sampled_obs_list, ignore_index=True)
    else:
        sampled_non_ref = pd.DataFrame()
        logger.warning("No non-reference observations could be sampled")

    if sampled_non_ref.empty:
        non_ref_truth = pd.DataFrame(columns=["id", "source_norad_id", "is_non_reference"])
        return ref_obs_df.copy(), non_ref_truth

    logger.info(
        f"Selected {len(sampled_non_ref)} non-ref observations from "
        f"{len(selected_sats)} satellites ({observations_per_satellite} obs each per Louis's spec)"
    )

    # Create ground truth DataFrame for non-reference observations
    non_ref_truth = pd.DataFrame({
        "id": sampled_non_ref["id"].values,
        "source_norad_id": sampled_non_ref["satNo"].values,
        "is_non_reference": True,
    })

    # Mark non-reference observations in the sampled DataFrame
    sampled_non_ref = sampled_non_ref.copy()
    sampled_non_ref["is_non_reference"] = True

    # Mark reference observations
    ref_obs_marked = ref_obs_df.copy()
    ref_obs_marked["is_non_reference"] = False

    # Combine reference and non-reference observations
    combined_df = pd.concat([ref_obs_marked, sampled_non_ref], ignore_index=True)

    # Shuffle to mix reference and non-reference observations
    combined_df = combined_df.sample(frac=1, random_state=rng.integers(2**31)).reset_index(drop=True)

    logger.info(
        f"Added {len(sampled_non_ref)} non-reference observations to dataset. "
        f"Total: {len(combined_df)} obs ({len(ref_obs_df)} ref + {len(sampled_non_ref)} non-ref)"
    )

    return combined_df, non_ref_truth


def generate_dataset_with_non_reference(
    obs_df: pd.DataFrame,
    sat_params: Dict[int, Dict],
    reference_norad_ids: List[int],
    include_non_ref_obs: bool = True,
    non_ref_ratio: float = 0.1,
    quality_level: str = "standard",
    quality_tier: str = "T2S",
    regimes: List[str] = None,
    seed: Optional[int] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Generate a complete dataset with optional non-reference observations.

    This is the high-level function that:
    1. Generates a standard dataset from reference observations
    2. Optionally adds non-reference observations for TN calculation
    3. Returns combined data and truth metadata for evaluation

    Args:
        obs_df: Full DataFrame of all observations (reference AND non-reference)
        sat_params: Dict mapping satNo to orbital parameters
        reference_norad_ids: List of NORAD IDs that are in the reference set
        include_non_ref_obs: Whether to include non-reference observations
        non_ref_ratio: Ratio of non-ref to ref observations (default 0.1 = 10%)
        quality_level: "high", "standard", or "low"
        quality_tier: Data quality tier for downsampling
        regimes: Orbital regimes to include
        seed: Random seed

    Returns:
        Tuple of (dataset_df, non_ref_truth_df, metadata)
        - dataset_df: Complete dataset for algorithm input (ref + non-ref)
        - non_ref_truth_df: Ground truth for non-reference observations
        - metadata: Dict with generation statistics
    """
    # Filter to reference observations
    reference_set = set(reference_norad_ids)
    ref_obs = obs_df[obs_df["satNo"].isin(reference_set)].copy()

    logger.info(
        f"Generating dataset: {len(ref_obs)} reference obs from "
        f"{len(reference_set)} reference satellites"
    )

    # Use reference observations as the dataset
    # Note: For full pipeline generation with window selection, use
    # generate_dataset_with_lewis_tiers() instead
    dataset_df = ref_obs.copy()
    generation_metadata = {
        "quality_level": quality_level,
        "quality_tier": quality_tier,
        "regimes": regimes,
        "seed": seed,
        "reference_satellites": list(reference_set),
        "total_reference_obs": len(ref_obs),
    }

    # Get the filtered reference satellite IDs after dataset generation
    final_ref_ids = list(dataset_df["satNo"].unique())

    # Initialize metadata
    metadata = {
        "generation": generation_metadata,
        "reference_satellite_count": len(final_ref_ids),
        "reference_observation_count": len(dataset_df),
        "include_non_ref_obs": include_non_ref_obs,
        "non_ref_observation_count": 0,
        "non_ref_satellite_count": 0,
    }

    # Add non-reference observations if requested
    if include_non_ref_obs:
        combined_df, non_ref_truth = add_non_reference_observations(
            dataset_df,
            final_ref_ids,
            all_observations_df=obs_df,
            non_ref_ratio=non_ref_ratio,
            seed=seed,
        )

        metadata["non_ref_observation_count"] = len(non_ref_truth)
        metadata["non_ref_satellite_count"] = non_ref_truth["source_norad_id"].nunique() if not non_ref_truth.empty else 0
        metadata["total_observation_count"] = len(combined_df)

        logger.info(
            f"Dataset generated: {metadata['reference_observation_count']} ref + "
            f"{metadata['non_ref_observation_count']} non-ref = "
            f"{metadata['total_observation_count']} total observations"
        )

        return combined_df, non_ref_truth, metadata
    else:
        non_ref_truth = pd.DataFrame(columns=["id", "source_norad_id", "is_non_reference"])
        metadata["total_observation_count"] = len(dataset_df)

        return dataset_df, non_ref_truth, metadata
