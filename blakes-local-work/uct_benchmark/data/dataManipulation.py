# -*- coding: utf-8 -*-
"""
Created on Fri Jun 27 11:45:50 2025

@author: Gabriel Lundin
"""

import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from uct_benchmark.simulation.orbitCoverage import orbitCoverage
from uct_benchmark.config import (
    DOWNSAMPLING_PROFILES,
    DownsampleConfig,
    semiMajorAxis_LEO,
    semiMajorAxis_GEO,
)


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
    a = 1 / ((2 / r_norms) - (v_norms**2 / mu))

    # Orbital periods in seconds (NaN if hyperbolic/unbound)
    T = np.where(a > 0, 2 * np.pi * np.sqrt(a**3 / mu), np.nan)

    # Map satNo → period
    periods = dict(zip(first_sv["satNo"], T))

    # --------------------------------------------------------------------
    # Create efficient group keys for binning observations
    # --------------------------------------------------------------------
    # Instead of modifying the original DataFrame in-place, track temporary columns
    added_cols = ["grp_type", "grp_key", "grp_code"]
    ref_obs_wip = ref_obs  # Work directly to avoid full memory copy

    # Determine if observations have a sensor ID or just location
    sensor_mask = ref_obs_wip["idSensor"].notna()

    # Mark grouping type: 'id' for sensor-based, 'loc' for location-based
    ref_obs_wip["grp_type"] = np.where(sensor_mask, "id", "loc")

    # Build fast, hashable group key as a string
    ref_obs_wip["grp_key"] = np.where(
        sensor_mask,
        ref_obs_wip["idSensor"].astype(str) + "_" + ref_obs_wip["satNo"].astype(str),
        ref_obs_wip["senlat"].astype(str)
        + "_"
        + ref_obs_wip["senlon"].astype(str)
        + "_"
        + ref_obs_wip["senalt"].astype(str)
        + "_"
        + ref_obs_wip["satNo"].astype(str),
    )

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
    # Drop temporary columns to avoid modifying input
    # --------------------------------------------------------------------
    ref_obs.drop(
        columns=[col for col in added_cols if col in ref_obs.columns],
        inplace=True,
        errors="ignore",
    )

    return tracks, metrics


# =============================================================================
# ORBITAL REGIME DETECTION
# =============================================================================

def determine_orbital_regime(semi_major_axis_km: float, eccentricity: float = 0.0) -> str:
    """
    Determine the orbital regime based on semi-major axis and eccentricity.

    Args:
        semi_major_axis_km: Semi-major axis in kilometers
        eccentricity: Orbital eccentricity (default 0)

    Returns:
        str: One of 'LEO', 'MEO', 'GEO', 'HEO'
    """
    if eccentricity >= 0.7:
        return 'HEO'
    elif semi_major_axis_km < semiMajorAxis_LEO:
        return 'LEO'
    elif semi_major_axis_km >= semiMajorAxis_GEO:
        return 'GEO'
    else:
        return 'MEO'


def get_regime_profile(regime: str) -> Dict:
    """Get the downsampling profile for a given orbital regime."""
    return DOWNSAMPLING_PROFILES.get(regime, DOWNSAMPLING_PROFILES['LEO'])


# =============================================================================
# TRACK IDENTIFICATION AND PRESERVATION
# =============================================================================

def identify_tracks(
    obs_df: pd.DataFrame,
    gap_threshold_minutes: float = 90.0
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
    if obs_df['obTime'].dtype == 'object':
        obs_df['obTime'] = pd.to_datetime(obs_df['obTime'])

    # Sort by satellite and time
    obs_df = obs_df.sort_values(['satNo', 'obTime']).reset_index(drop=True)

    # Build grouping key (sensor or location)
    if 'idSensor' in obs_df.columns:
        sensor_mask = obs_df['idSensor'].notna()
        obs_df['grp_key'] = np.where(
            sensor_mask,
            obs_df['idSensor'].astype(str) + '_' + obs_df['satNo'].astype(str),
            obs_df['senlat'].astype(str) + '_' + obs_df['senlon'].astype(str) + '_' + obs_df['satNo'].astype(str)
        )
    else:
        obs_df['grp_key'] = obs_df['satNo'].astype(str)

    tracks = []
    threshold = pd.Timedelta(minutes=gap_threshold_minutes)

    for _, group in obs_df.groupby('grp_key', sort=False):
        if len(group) < 1:
            continue

        group = group.sort_values('obTime')
        time_diffs = group['obTime'].diff()
        track_boundaries = (time_diffs > threshold).cumsum()

        for _, track in group.groupby(track_boundaries, sort=False):
            if len(track) >= 1:
                tracks.append(track.reset_index(drop=True))

    return tracks


def select_tracks_for_coverage(
    tracks: List[pd.DataFrame],
    orbital_period_sec: float,
    target_coverage: float,
    rng: np.random.Generator = None
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
        center = track['obTime'].median()
        track_info.append({
            'index': i,
            'center': center,
            'duration': (track['obTime'].max() - track['obTime'].min()).total_seconds(),
            'count': len(track)
        })

    track_info = sorted(track_info, key=lambda x: x['center'])

    # Calculate how many tracks to select based on target coverage
    if len(track_info) <= 1:
        return tracks

    # Calculate temporal span
    total_span = (track_info[-1]['center'] - track_info[0]['center']).total_seconds()
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
            weights = np.array([t['count'] for t in bin_tracks], dtype=float)
            weights /= weights.sum()
            chosen_idx = rng.choice(len(bin_tracks), p=weights)
            selected_indices.add(bin_tracks[chosen_idx]['index'])

    return [tracks[i] for i in sorted(selected_indices)]


def thin_within_tracks(
    tracks: List[pd.DataFrame],
    obs_per_track: Tuple[int, int],
    preserve_boundaries: bool = True,
    rng: np.random.Generator = None
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
        track = track.sort_values('obTime').reset_index(drop=True)

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
                    sampled_indices = rng.choice(
                        len(middle_obs), size=sample_count, replace=False
                    )
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
    rng: np.random.Generator = None
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
    regime_sats: Dict[str, List[int]] = {'LEO': [], 'MEO': [], 'GEO': [], 'HEO': []}

    for sat_no, params in sat_params.items():
        sma = params.get('Semi-Major Axis', 7000)
        ecc = params.get('Eccentricity', 0.0)
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
        regime_obs = ref_obs[ref_obs['satNo'].isin(sat_list)].copy()
        if regime_obs.empty:
            continue

        # Apply regime-specific downsampling
        for sat_no in sat_list:
            sat_obs = regime_obs[regime_obs['satNo'] == sat_no].copy()
            if sat_obs.empty:
                continue

            sat_param = sat_params.get(sat_no, {})
            period = sat_param.get('Period', 5400)  # Default ~90 min

            # Identify tracks
            tracks = identify_tracks(sat_obs)

            # Select tracks based on coverage target
            target_coverage = rng.uniform(
                profile['min_coverage_pct'],
                profile['max_coverage_pct']
            )
            selected_tracks = select_tracks_for_coverage(
                tracks, period, target_coverage, rng
            )

            # Thin observations within tracks
            obs_range = profile['obs_per_track']
            thinned = thin_within_tracks(
                selected_tracks,
                obs_range,
                preserve_boundaries=config.preserve_track_boundaries,
                rng=rng
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
    seed: Optional[int] = None
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

    for sat_no in obs_df['satNo'].unique():
        sat_obs = obs_df[obs_df['satNo'] == sat_no].copy()
        sat_param = sat_params.get(sat_no, {})
        period = sat_param.get('Period', 5400)

        # Identify tracks
        tracks = identify_tracks(sat_obs)

        if not tracks:
            continue

        # Select tracks to achieve target coverage
        selected = select_tracks_for_coverage(
            tracks, period, target_coverage, rng
        )

        # Thin within tracks
        thinned = thin_within_tracks(
            selected, obs_per_track, preserve_boundaries, rng
        )

        if not thinned.empty:
            result_parts.append(thinned)

    if result_parts:
        return pd.concat(result_parts, ignore_index=True)
    return pd.DataFrame()


# =============================================================================
# 3D ORBITAL COVERAGE CALCULATION
# =============================================================================

def compute_mean_anomaly_from_obs(
    obs_df: pd.DataFrame,
    orbital_elements: Dict
) -> np.ndarray:
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
    a = orbital_elements.get('Semi-Major Axis', 7000)
    e = orbital_elements.get('Eccentricity', 0.0)
    i = np.radians(orbital_elements.get('Inclination', 0.0))
    raan = np.radians(orbital_elements.get('RAAN', 0.0))
    argp = np.radians(orbital_elements.get('Argument of Perigee', 0.0))

    # Convert RA/Dec to line-of-sight unit vectors
    ra = np.radians(obs_df['ra'].values)
    dec = np.radians(obs_df['declination'].values)

    los_x = np.cos(dec) * np.cos(ra)
    los_y = np.cos(dec) * np.sin(ra)
    los_z = np.sin(dec)

    # Rotation matrix from perifocal to ECI
    cos_raan, sin_raan = np.cos(raan), np.sin(raan)
    cos_argp, sin_argp = np.cos(argp), np.sin(argp)
    cos_i, sin_i = np.cos(i), np.sin(i)

    # Inverse rotation to get to orbital plane
    # Simplified: project onto orbital plane and find angle

    # For each observation, find the true anomaly
    true_anomalies = np.arctan2(los_y * cos_raan + los_x * sin_raan,
                                 los_x * cos_raan - los_y * sin_raan)

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


def compute_3d_coverage(
    obs_df: pd.DataFrame,
    orbital_elements: Dict
) -> Tuple[float, Dict]:
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
        return 0.0, {'status': 'insufficient_observations', 'count': len(obs_df)}

    # Compute mean anomalies
    try:
        mean_anomalies = compute_mean_anomaly_from_obs(obs_df, orbital_elements)
    except Exception as e:
        # Fall back to 2D coverage
        coverage, _ = orbitCoverage(obs_df, orbital_elements)
        return coverage, {'status': 'fallback_2d', 'error': str(e)}

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
        'status': 'success',
        'arc_coverage': arc_coverage,
        'poly_coverage': poly_coverage,
        'combined_coverage': combined_coverage,
        'n_observations': len(obs_df),
        'mean_anomaly_range': float(np.ptp(mean_anomalies)),
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

    # Perform bin-based sampling
    def safe_sample(group, k, period_sec, relax=False):
        if k >= len(group):
            return group
        if relax:
            return group.sample(n=k, random_state=rand)
        time_sorted = group.sort_values("obTime")
        thresh = pd.Timedelta(seconds=0.1 * period_sec)
        diffs = time_sorted["obTime"].diff().abs().fillna(pd.Timedelta(seconds=0))
        dense = 1 / diffs.clip(lower=thresh).dt.total_seconds()
        prob = dense / dense.sum()
        return time_sorted.sample(n=k, weights=prob, random_state=rand)

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

            # Compute observation density (vectorized)
            diffs = time_sorted["obTime"].diff().dt.total_seconds().fillna(period_sec)
            thresh = 0.1 * period_sec
            dense = 1.0 / diffs.clip(lower=thresh)

            # Normalize weights globally
            weights = dense / dense.sum()

            # Combine into one DataFrame
            time_sorted = time_sorted.assign(time_bin=time_bins, weight=weights)

            # Now sample per bin vectorized:
            sampled = time_sorted.groupby("time_bin", group_keys=False, observed=True).apply(
                lambda g: g.sample(
                    n=min(int(target_per_bin[g.name]), len(g)),
                    weights=g["weight"],
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

        max_area = np.pi * sat_params[sat]["Semi-Major Axis"] ** 2
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
