# -*- coding: utf-8 -*-
"""
Experimental / Research Downsampling Strategies

This module contains experimental and alternative downsampling approaches that
are NOT part of Louis's canonical 3-stage pipeline. These functions were
developed during research and prototyping and may be useful for future work
or comparison studies.

The canonical production pipeline lives in dataManipulation.py:
  apply_downsampling() -> downsampleData() ->
    Stage 1: _lowerOrbitCoverage
    Stage 2: _increaseTrackDistance
    Stage 3: _downsampleAbsolute

Functions in this module:
  - downsample_preserve_tracks: Track-aware downsampling (alternative approach)
  - downsample_observations_sequential: Per-satellite sequential downsampling
  - downsample_dataset_sequential: Dataset-level sequential downsampling
  - classify_window_tier: Lewis's window tier classification
  - process_window_by_tier: Window processing orchestration by Lewis tier
  - get_downsample_config_from_legacy: Legacy 16-char code to config mapping
  - should_simulate_for_legacy_code: Simulation decision for legacy codes
  - add_non_reference_observations: Non-reference obs for True Negative calc
"""

from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
import numpy as np
import pandas as pd

from uct_benchmark.settings import (
    DownsampleConfig,
    SimulationConfig,
    LEGACY_COVERAGE_DOWNSAMPLE,
    TRACK_GAP_LONG_MULTIPLIER,
    OBS_COUNT_LOW_THRESHOLD,
    NON_REF_OBS_PER_SATELLITE,
)
from uct_benchmark.utils.orbital import determine_orbital_regime


# =============================================================================
# TRACK-AWARE DOWNSAMPLING (Alternative Approach)
# =============================================================================


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
    from uct_benchmark.data.dataManipulation import (
        identify_tracks,
        select_tracks_for_coverage,
        thin_within_tracks,
    )

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
# SEQUENTIAL DOWNSAMPLING (per Louis's Specification)
# =============================================================================
# Order: Coverage -> Track Gap -> Obs Count
# This is the CORRECT order per Louis's Benchmarking Documentation


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

    Order: Coverage -> Track Gap -> Observation Count

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

    Applies Coverage -> Track Gap -> Obs Count downsampling in order,
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
    from uct_benchmark.data.dataManipulation import (
        apply_downsampling,
        apply_simulation_to_gaps,
    )

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
    - A = >90% objects have LOW quality (sparse dataset) -> aggressive downsampling
    - S = 40-60% objects have LOW quality (mixed) -> moderate downsampling
    - N = <10% objects have LOW quality (dense dataset) -> minimal downsampling

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
    # A = >90% objects have LONG gaps (sparse tracking) -> target large gaps
    # S = 40-60% objects have LONG gaps -> moderate gaps
    # N = <10% objects have LONG gaps (dense tracking) -> target small gaps
    gap_targets = {
        "A": 5.0,    # Sparse: large gaps (most objects poorly tracked)
        "S": 2.0,    # Mixed: standard gaps
        "N": 0.5,    # Dense: small gaps (most objects well tracked)
    }
    target_gap = gap_targets.get(track_gap, 2.0)

    # Map observation count to max observations per satellite per Louis's documentation:
    # A = >90% objects have LOW obs count (sparse) -> strict limit
    # S = 40-60% objects have LOW obs count (mixed) -> moderate limit
    # N = <10% objects have LOW obs count (dense) -> allow many observations
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
    # A = >90% objects have LOW quality (sparse) -> we WANT sparse data, don't simulate
    # S = 40-60% objects have LOW quality (mixed) -> simulate only if very sparse
    # N = <10% objects have LOW quality (dense) -> we WANT dense data, simulate if sparse

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

    # Per SSOT: "2 non-reference observations per satellite" -- the number of
    # non-reference satellites matches the number of reference satellites, and
    # each gets exactly NON_REF_OBS_PER_SATELLITE observations (default 2).
    ref_sat_count = ref_obs_df["satNo"].nunique()

    if ref_sat_count <= 0:
        logger.info("No reference satellites; skipping non-reference observation selection")
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

    # Per SSOT: one non-reference satellite per reference satellite,
    # each with exactly NON_REF_OBS_PER_SATELLITE (2) observations
    target_non_ref_sats = min(ref_sat_count, len(non_ref_satellites))
    logger.info(
        f"Targeting {target_non_ref_sats} non-ref satellites "
        f"({observations_per_satellite} obs each) to match {ref_sat_count} reference satellites"
    )

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
