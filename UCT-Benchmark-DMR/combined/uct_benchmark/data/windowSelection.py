# -*- coding: utf-8 -*-
"""
Window Selection Module - Bisection Algorithm for Optimal Time Window

This module implements the binary search (bisection) algorithm described by Lewis
for finding the optimal time window within a larger data batch. The algorithm
recursively bisects the data to find windows that meet user-specified criteria.

Lewis's Algorithm (from transcript):
1. Pull large batch (e.g., 10 days for 2-day fit span)
2. Check if criteria A,B,C,D are met in entire batch
3. Bisect: check first half for criteria
   - If first half meets criteria, bisect first half again
   - If not, check second half
4. Continue until window approaches fit span size
5. When too small to bisect, use sliding window
6. Return optimal window with tier classification

Tier Classification (Lewis's definition):
- Tier 1: All criteria met, no data manipulation needed (optimal)
- Tier 2: Most criteria met, needs downsampling (too much data)
- Tier 3: Few criteria met, needs simulation (too little data)

Author: UCT Benchmark Team
Date: 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


# ---------------------------------------------------------------------------
# Reference-alignment configuration dataclass
# ---------------------------------------------------------------------------

@dataclass
class ReferenceAlignmentConfig:
    """
    Configuration for reference-algorithm alignment options.

    When ``reference_mode`` is True, all flags are set to match the original
    windowCheck.py behaviour authored by Miles Puchner. When False (default),
    the production-improved behaviour is retained.

    Attributes:
        normalize_backward: When True, normalize time backward so that
            0 corresponds to the *newest* observation (reference behaviour).
            When False, keep the current forward-time convention.
        overlap_bisection: When True, bisection halves overlap by
            0.5 x window_size on each side of the midpoint (reference
            behaviour).  When False, use a clean midpoint split.
        short_circuit_first_half: When True, during bisection check the
            first half only; if it passes, skip the second half entirely
            (reference behaviour).  When False, evaluate both halves and
            pick the better one.
        hard_stop_on_t1: When True, immediately return when a TIER_1
            window is found, stopping all sliding and bisecting (reference
            behaviour).  When False, keep the current conditional T1
            return that continues narrowing when the batch is large.
        min_batch_threshold_multiplier: Minimum batch-to-window ratio
            below which the decay loop stops.  Reference uses 2.01;
            current production default is 1.1.
    """

    normalize_backward: bool = False
    overlap_bisection: bool = False
    short_circuit_first_half: bool = False
    hard_stop_on_t1: bool = False
    min_batch_threshold_multiplier: float = 1.1

    @classmethod
    def from_reference_mode(cls, reference_mode: bool) -> "ReferenceAlignmentConfig":
        """Create a config with all flags set for reference alignment."""
        if reference_mode:
            return cls(
                normalize_backward=True,
                overlap_bisection=True,
                short_circuit_first_half=True,
                hard_stop_on_t1=True,
                min_batch_threshold_multiplier=2.01,
            )
        return cls()  # all defaults = current production behaviour

from uct_benchmark.settings import (
    highObjectCount,
    highObsCount,
    lowObjectCount,
    lowObsCount,
    lowPercentage,
    highPercentage,
    standardPercentage,
    longTrackGap,
    slide_resolution,
    batchSizeMultiplier,
    batchSizeDecayRate,
    QUALITY_LEVEL_THRESHOLDS,
    OBJECT_COUNT_MAP,
    COVERAGE_THRESHOLDS,
    QUALITY_RANGES,
    TRACK_GAP_LONG_MULTIPLIER,
)


class WindowTier(Enum):
    """
    Window quality tier classification per Lewis's definition.

    This is DIFFERENT from data quality tiers (T1/T2/T3) which control
    downsampling intensity. This tier classifies WHEN manipulation is needed.
    """
    TIER_1 = 1  # Optimal: all criteria met, no manipulation needed
    TIER_2 = 2  # Suboptimal: too much data, needs downsampling
    TIER_3 = 3  # Most suboptimal: too little data, needs simulation
    TIER_4 = 4  # Insufficient: cannot meet criteria even with simulation
    TIER_5 = 5  # Impossible: criteria cannot be met (per Louis's spec)


@dataclass
class WindowCriteria:
    """
    Criteria that a time window must meet.

    These are the user-specified requirements (Lewis's criteria A, B, C, D).
    """
    # Object count criteria
    min_objects: int = 10
    target_objects: int = 40
    max_objects: int = 80

    # Observation count per object
    min_obs_per_object: int = 5
    target_obs_per_object: int = 50
    max_obs_per_object: int = 150

    # Orbital coverage (fraction of orbit)
    min_coverage: float = 0.02
    target_coverage: float = 0.10
    max_coverage: float = 0.50

    # Track gap (in orbital periods)
    min_track_gap_periods: float = 0.5
    target_track_gap_periods: float = 2.0
    max_track_gap_periods: float = 5.0

    # Fit span (duration of data in days)
    fit_span_days: float = 7.0

    # Orbital regimes to include
    regimes: List[str] = field(default_factory=lambda: ["LEO", "MEO", "GEO"])

    # Object types to include
    object_types: List[str] = field(default_factory=lambda: ["NORM"])

    # Minimum criteria to meet for each tier
    tier_1_threshold: float = 1.0   # All criteria met
    tier_2_threshold: float = 0.7   # 70% criteria met (needs downsampling)
    tier_3_threshold: float = 0.4   # 40% criteria met (needs simulation)


@dataclass
class WindowEvaluation:
    """Results of evaluating a time window against criteria."""

    # Time window boundaries
    start_time: datetime = None
    end_time: datetime = None
    duration_days: float = 0.0

    # Tier classification
    tier: WindowTier = WindowTier.TIER_4

    # Criteria scores (0.0 to 1.0)
    object_count_score: float = 0.0
    obs_per_object_score: float = 0.0
    coverage_score: float = 0.0
    track_gap_score: float = 0.0
    overall_score: float = 0.0

    # Actual values
    object_count: int = 0
    avg_obs_per_object: float = 0.0
    avg_coverage: float = 0.0
    avg_track_gap_periods: float = 0.0

    # Data availability flags
    has_enough_objects: bool = False
    has_enough_observations: bool = False
    needs_downsampling: bool = False
    needs_simulation: bool = False

    # Maximum available objects in entire search space (for TIER_5 detection)
    max_available_objects: int = 0

    # Satellites in window
    satellite_ids: List[int] = field(default_factory=list)

    # Detailed per-satellite metrics
    satellite_metrics: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    # Recommended action for TIER_5
    recommended_action: str = ""


@dataclass
class BisectionResult:
    """Result of the bisection window search."""

    # Best window found
    best_window: WindowEvaluation = None

    # All evaluated windows (for debugging)
    evaluated_windows: List[WindowEvaluation] = field(default_factory=list)

    # Search statistics
    bisection_depth: int = 0
    windows_evaluated: int = 0
    search_duration_seconds: float = 0.0

    # Recommendation
    recommended_action: str = ""  # "use_as_is", "downsample", "simulate"


def evaluate_window(
    obs_df: pd.DataFrame,
    sat_params: Dict[int, Dict],
    start_time: datetime,
    end_time: datetime,
    criteria: WindowCriteria,
) -> WindowEvaluation:
    """
    Evaluate a time window against the specified criteria.

    This function checks if a given time window meets Lewis's criteria A, B, C, D
    and classifies it into Tier 1, 2, 3, or 4.

    Args:
        obs_df: DataFrame of observations with 'obTime', 'satNo' columns
        sat_params: Dict mapping satNo to orbital parameters
        start_time: Start of time window
        end_time: End of time window
        criteria: WindowCriteria instance with target values

    Returns:
        WindowEvaluation with scores and tier classification
    """
    result = WindowEvaluation(
        start_time=start_time,
        end_time=end_time,
        duration_days=(end_time - start_time).total_seconds() / 86400,
    )

    # Filter observations to time window
    if obs_df.empty:
        logger.warning("Empty observation DataFrame passed to window evaluation; returning TIER_4")
        result.tier = WindowTier.TIER_4
        return result

    # Ensure obTime is datetime
    obs_df = obs_df.copy()
    if obs_df["obTime"].dtype == "object":
        obs_df["obTime"] = pd.to_datetime(obs_df["obTime"])

    # Handle timezone-aware datetimes: ensure start/end match the column tz
    if obs_df["obTime"].dt.tz is not None:
        col_tz = obs_df["obTime"].dt.tz
        ts_start = pd.Timestamp(start_time)
        ts_end = pd.Timestamp(end_time)
        start_time = ts_start.tz_convert(col_tz) if ts_start.tzinfo is not None else ts_start.tz_localize(col_tz)
        end_time = ts_end.tz_convert(col_tz) if ts_end.tzinfo is not None else ts_end.tz_localize(col_tz)

    window_mask = (obs_df["obTime"] >= start_time) & (obs_df["obTime"] <= end_time)
    window_obs = obs_df[window_mask]

    if window_obs.empty:
        result.tier = WindowTier.TIER_4
        return result

    # Count unique satellites with observations
    sat_counts = window_obs["satNo"].value_counts()
    valid_sats = sat_counts[sat_counts >= 3].index.tolist()  # Min 3 obs for IOD

    result.object_count = len(valid_sats)
    result.satellite_ids = valid_sats
    result.has_enough_objects = result.object_count >= criteria.min_objects

    # Track max available objects for TIER_5 detection
    # This is all unique satellites in the window, regardless of observation count
    result.max_available_objects = len(sat_counts)

    # Evaluate each satellite
    sat_metrics = {}
    obs_counts = []
    coverages = []
    track_gaps = []

    for sat_no in valid_sats:
        sat_obs = window_obs[window_obs["satNo"] == sat_no].copy()
        sat_param = sat_params.get(sat_no, {})
        period_sec = sat_param.get("Period", 5400)  # Default 90 min

        # Observation count
        obs_count = len(sat_obs)
        obs_counts.append(obs_count)

        # Compute coverage using convex polygon on circumscribed circle method
        # per Louis's Benchmarking Documentation
        if len(sat_obs) >= 2:
            sat_obs = sat_obs.sort_values("obTime")
            coverage = calculate_orbital_coverage_polygon(
                sat_obs,
                orbital_period=period_sec,
                epoch_column="obTime"
            )
        else:
            coverage = 0.0
        coverages.append(coverage)

        # Track gap (max gap between observations, normalized by orbital period)
        if len(sat_obs) >= 2:
            time_diffs = sat_obs["obTime"].diff().dropna()
            max_gap_sec = time_diffs.max().total_seconds()
            track_gap_periods = max_gap_sec / period_sec if period_sec > 0 else 0
        else:
            track_gap_periods = float("inf")
        track_gaps.append(track_gap_periods)

        sat_metrics[sat_no] = {
            "obs_count": obs_count,
            "coverage": coverage,
            "track_gap_periods": track_gap_periods,
            "period_sec": period_sec,
        }

    result.satellite_metrics = sat_metrics

    # Compute average metrics
    if valid_sats:
        result.avg_obs_per_object = np.mean(obs_counts)
        result.avg_coverage = np.mean(coverages)
        # Use median for track gap to reduce outlier impact
        result.avg_track_gap_periods = np.median(track_gaps) if track_gaps else float("inf")

    # Check if has enough observations
    result.has_enough_observations = result.avg_obs_per_object >= criteria.min_obs_per_object

    # Score each criterion (0.0 to 1.0)
    # Object count score
    if result.object_count >= criteria.target_objects:
        result.object_count_score = 1.0
    elif result.object_count >= criteria.min_objects:
        result.object_count_score = 0.5 + 0.5 * (
            (result.object_count - criteria.min_objects) /
            max(1, criteria.target_objects - criteria.min_objects)
        )
    else:
        result.object_count_score = 0.5 * result.object_count / max(1, criteria.min_objects)

    # Observation count score
    if result.avg_obs_per_object >= criteria.target_obs_per_object:
        result.obs_per_object_score = 1.0
    elif result.avg_obs_per_object >= criteria.min_obs_per_object:
        result.obs_per_object_score = 0.5 + 0.5 * (
            (result.avg_obs_per_object - criteria.min_obs_per_object) /
            max(1, criteria.target_obs_per_object - criteria.min_obs_per_object)
        )
    else:
        result.obs_per_object_score = 0.5 * result.avg_obs_per_object / max(1, criteria.min_obs_per_object)

    # Coverage score (higher is better within range)
    # Use regime-specific scoring if regime is specified
    regime = criteria.regimes[0] if criteria.regimes else None
    if regime:
        result.coverage_score = get_coverage_score_with_regime(
            result.avg_coverage, regime, criteria
        )
    else:
        # Fallback to original scoring if no regime specified
        if criteria.min_coverage <= result.avg_coverage <= criteria.max_coverage:
            result.coverage_score = 1.0
        elif result.avg_coverage > criteria.max_coverage:
            # Too much coverage - needs downsampling but still usable
            result.coverage_score = 0.8
        elif result.avg_coverage >= criteria.min_coverage * 0.5:
            result.coverage_score = 0.5 + 0.5 * (
                result.avg_coverage / criteria.min_coverage
            )
        else:
            result.coverage_score = 0.5 * result.avg_coverage / max(0.001, criteria.min_coverage)

    # Track gap score (target gap is desired, not too small or too large)
    if criteria.min_track_gap_periods <= result.avg_track_gap_periods <= criteria.max_track_gap_periods:
        result.track_gap_score = 1.0
    elif result.avg_track_gap_periods < criteria.min_track_gap_periods:
        # Gaps too small - needs downsampling to increase gaps
        result.track_gap_score = 0.8
    elif result.avg_track_gap_periods <= criteria.max_track_gap_periods * 2:
        result.track_gap_score = 0.5
    else:
        result.track_gap_score = 0.2

    # Overall score (weighted average)
    result.overall_score = (
        0.30 * result.object_count_score +
        0.30 * result.obs_per_object_score +
        0.20 * result.coverage_score +
        0.20 * result.track_gap_score
    )

    # Determine tier
    if result.overall_score >= criteria.tier_1_threshold:
        result.tier = WindowTier.TIER_1
        result.needs_downsampling = False
        result.needs_simulation = False
    elif result.overall_score >= criteria.tier_2_threshold:
        result.tier = WindowTier.TIER_2
        # Too much data (high coverage, small gaps) -> needs downsampling
        result.needs_downsampling = (
            result.avg_coverage > criteria.max_coverage or
            result.avg_track_gap_periods < criteria.min_track_gap_periods or
            result.avg_obs_per_object > criteria.max_obs_per_object
        )
        result.needs_simulation = False
    elif result.overall_score >= criteria.tier_3_threshold:
        result.tier = WindowTier.TIER_3
        result.needs_downsampling = False
        # Too little data -> needs simulation
        result.needs_simulation = (
            result.avg_coverage < criteria.min_coverage or
            result.object_count < criteria.min_objects or
            result.avg_obs_per_object < criteria.min_obs_per_object
        )
    else:
        # Check if criteria are fundamentally impossible (TIER_5)
        # Per Lewis's specification: "Tier-5 occurs when the selected criteria cannot possibly be met"
        # Determine regime from criteria if available
        regime = criteria.regimes[0] if criteria.regimes else None
        if _is_criteria_impossible(result, criteria, regime=regime):
            result.tier = WindowTier.TIER_5
            result.needs_downsampling = False
            result.needs_simulation = False  # Can't simulate impossible criteria
            result.recommended_action = "criteria_impossible"
        else:
            result.tier = WindowTier.TIER_4
            result.needs_simulation = True

    return result


def _is_criteria_impossible(
    result: WindowEvaluation,
    criteria: WindowCriteria,
    regime: str = None
) -> bool:
    """
    Check if criteria can never be met per Lewis's specification.

    Tier-5 occurs when:
    1. No objects exist in the entire search space
    2. Requested more objects than exist in the catalog
    3. Required observation counts exceed what's physically possible
    4. Coverage requirements exceed orbital geometry limits
    5. Regime-specific physical limits are exceeded

    Args:
        result: Current window evaluation with actual data metrics
        criteria: User-specified criteria requirements
        regime: Optional orbital regime for regime-specific checks (LEO, MEO, GEO)

    Returns:
        True if criteria are fundamentally impossible to satisfy
    """
    # Case 1: No objects at all in the search space
    if result.object_count == 0 and result.max_available_objects == 0:
        logger.warning("TIER_5: No objects found in entire search space")
        return True

    # Case 2: Requested more minimum objects than exist
    if criteria.min_objects > result.max_available_objects and result.max_available_objects > 0:
        logger.warning(
            f"TIER_5: Requested min {criteria.min_objects} objects but only "
            f"{result.max_available_objects} exist in catalog"
        )
        return True

    # Case 3: No satellites have any observations (IOD impossible)
    if result.object_count == 0:
        logger.warning("TIER_5: No satellites have minimum required observations for IOD")
        return True

    # Case 4: Required fit span exceeds available data window
    if result.duration_days < criteria.fit_span_days * 0.1:
        # Less than 10% of required fit span available
        logger.warning(
            f"TIER_5: Data window {result.duration_days:.1f} days is far below "
            f"required {criteria.fit_span_days:.1f} day fit span"
        )
        return True

    # Case 5: All satellites have zero coverage (no valid observations)
    if result.avg_coverage == 0.0 and result.object_count > 0:
        all_zero_coverage = all(
            metrics.get("coverage", 0) == 0
            for metrics in result.satellite_metrics.values()
        )
        if all_zero_coverage:
            logger.warning("TIER_5: All satellites have zero orbital coverage")
            return True

    # Case 6: Regime-specific coverage limits (per Lewis's specification)
    # These represent physically realistic maximum observable coverage
    # for ground-based sensors in each orbital regime
    if regime and criteria.min_coverage:
        max_possible_coverage = _get_max_possible_coverage(regime)
        if criteria.min_coverage > max_possible_coverage:
            logger.warning(
                f"TIER_5: Requested {criteria.min_coverage:.1%} coverage is impossible for "
                f"{regime} (max realistic: {max_possible_coverage:.1%})"
            )
            return True

    # Case 7: Track gap exceeds fit span (per Louis's SDATap transcript example)
    # Quote: "Two periods between observations for a geostationary object which has
    # a period of one day. Now they're saying they want two days between observations,
    # but they only want a two day window - that's not possible."
    if regime and criteria.target_track_gap_periods and criteria.fit_span_days:
        # Typical orbital periods in seconds for each regime
        typical_periods_sec = {
            "LEO": 5400,    # ~90 minutes
            "MEO": 43200,   # ~12 hours
            "GEO": 86400,   # ~24 hours (1 day)
            "HEO": 43200,   # ~12 hours (highly variable)
        }
        period_sec = typical_periods_sec.get(regime.upper(), 5400)

        # Convert track gap from periods to days
        track_gap_days = (criteria.target_track_gap_periods * period_sec) / 86400

        # If requested track gap >= fit span, it's physically impossible
        # You can't have gaps longer than the entire data window
        if track_gap_days >= criteria.fit_span_days:
            logger.warning(
                f"TIER_5: Requested {criteria.target_track_gap_periods:.1f} period track gap "
                f"for {regime} = {track_gap_days:.1f} days, but fit span is only "
                f"{criteria.fit_span_days:.1f} days. Impossible per Louis's spec."
            )
            return True

    return False


def _get_max_possible_coverage(regime: str) -> float:
    """
    Get the maximum physically possible coverage for an orbital regime.

    These limits are based on ground-based sensor visibility constraints:
    - LEO: Objects pass overhead quickly, limited observation windows
    - MEO: Longer visibility but still limited by Earth rotation
    - GEO: Continuously visible from fixed location but orbital arc limited

    Per Lewis's documentation, these represent realistic upper bounds
    for what ground-based optical sensors can achieve.

    Args:
        regime: Orbital regime (LEO, MEO, GEO, HEO)

    Returns:
        Maximum coverage fraction [0.0, 1.0]
    """
    max_coverage_limits = {
        "LEO": 0.15,   # ~15% max realistic coverage (short passes)
        "MEO": 0.30,   # ~30% max realistic coverage
        "GEO": 0.60,   # ~60% max (always visible from site but orbital arc limited)
        "HEO": 0.20,   # ~20% max (highly variable)
    }
    return max_coverage_limits.get(regime.upper(), 1.0)


def _normalize_time_backward(obs_df: pd.DataFrame, epoch_column: str = "obTime") -> pd.Series:
    """
    Normalize observation epochs backward so that 0 = newest observation.

    This replicates the ``normalizeTime()`` helper in the reference
    windowCheck.py.  Each epoch is mapped to
    ``(max_epoch - epoch).total_seconds() / 86400`` so that the most
    recent observation has a normalized value of 0 and older observations
    have positive values (measured in days into the past).

    Args:
        obs_df: DataFrame containing the epoch column.
        epoch_column: Name of the datetime column (default ``"obTime"``).

    Returns:
        pandas Series of backward-normalized times (float, in days).
    """
    tf = obs_df[epoch_column].max()
    return obs_df[epoch_column].apply(lambda t: (tf - t).total_seconds() / 86400.0)


def _calculate_next_batch_size(
    iteration: int,
    initial_batch_days: float,
    fit_span_days: float,
) -> float:
    """
    Apply exponential decay to batch size per Lewis's specification.

    Per Lewis's reference code:
    - Initial batch = fitspan × batchSizeMultiplier (5x)
    - Each iteration: batch_size = fit_span + (initial - fit_span) * exp(-decay_rate * iteration)

    This gradually reduces the batch size from the initial large batch
    down toward the fit span as iterations progress.

    Args:
        iteration: Current iteration number (0-indexed)
        initial_batch_days: Initial batch size in days
        fit_span_days: Target fit span in days (minimum batch size)

    Returns:
        Next batch size in days
    """
    # The batch size asymptotically approaches fit_span_days
    # Starting from initial_batch_days and decaying exponentially
    decayed_batch = fit_span_days + (initial_batch_days - fit_span_days) * np.exp(
        -batchSizeDecayRate * iteration
    )

    # Ensure we never go below fit span
    return max(decayed_batch, fit_span_days)


def calculate_initial_batch_size(fit_span_days: float) -> float:
    """
    Calculate the initial batch size for window selection.

    Per Lewis's specification: Initial batch = fitspan × batchSizeMultiplier (5x)

    Args:
        fit_span_days: Target fit span in days

    Returns:
        Initial batch size in days
    """
    return fit_span_days * batchSizeMultiplier


def get_coverage_score_with_regime(
    coverage: float,
    regime: str,
    criteria: WindowCriteria
) -> float:
    """
    Score coverage using regime-specific thresholds per Lewis's specification.

    Uses the COVERAGE_THRESHOLDS from settings to determine what is
    considered "low" coverage for each orbital regime, then scores
    accordingly.

    Args:
        coverage: Observed coverage fraction [0.0, 1.0]
        regime: Orbital regime (LEO, MEO, GEO, HEO)
        criteria: WindowCriteria with target coverage values

    Returns:
        Coverage score [0.0, 1.0]
    """
    # Get regime-specific "low" threshold
    low_threshold = COVERAGE_THRESHOLDS.get(regime.upper(), COVERAGE_THRESHOLDS.get("LEO", 0.000213))

    # Check if coverage is considered "low" for this regime
    is_low = coverage < low_threshold

    # Score based on whether coverage meets criteria
    if criteria.min_coverage <= coverage <= criteria.max_coverage:
        return 1.0
    elif coverage > criteria.max_coverage:
        # Too much coverage - needs downsampling but still usable
        return 0.8
    elif coverage >= criteria.min_coverage * 0.5:
        # Partial credit for approaching minimum
        base_score = 0.5 + 0.5 * (coverage / criteria.min_coverage)
        # Penalize slightly if below regime threshold
        if is_low:
            base_score *= 0.9
        return min(base_score, 1.0)
    else:
        # Very low coverage
        base_score = 0.5 * coverage / max(0.001, criteria.min_coverage)
        if is_low:
            base_score *= 0.8
        return max(0.0, base_score)


def _bisect_search(
    obs_df: pd.DataFrame,
    sat_params: Dict[int, Dict],
    batch_start: datetime,
    batch_end: datetime,
    criteria: WindowCriteria,
    depth: int = 0,
    max_depth: int = 10,
    evaluated_windows: List[WindowEvaluation] = None,
    *,
    overlap_bisection: bool = False,
    short_circuit_first_half: bool = False,
    hard_stop_on_t1: bool = False,
    min_batch_threshold_multiplier: float = 1.1,
) -> Tuple[WindowEvaluation, List[WindowEvaluation]]:
    """
    Recursive bisection search for optimal window.

    This implements Lewis's algorithm:
    1. Evaluate current batch
    2. If batch is close to fit span, stop bisecting
    3. Otherwise, split in half and check each half
    4. Continue with the half that has better criteria match

    Reference-alignment parameters (all keyword-only, default to current
    production behaviour):

    Args:
        obs_df: DataFrame of observations
        sat_params: Dict mapping satNo to orbital parameters
        batch_start: Start of current batch to search
        batch_end: End of current batch to search
        criteria: WindowCriteria instance
        depth: Current recursion depth
        max_depth: Maximum recursion depth
        evaluated_windows: List to collect all evaluated windows
        overlap_bisection: When True, each bisection half overlaps by
            0.5 x fit_span_days around the midpoint (reference behaviour).
            When False, a clean midpoint split is used.
        short_circuit_first_half: When True, if the first half meets the
            threshold the second half is never evaluated (reference
            behaviour).  When False, both halves are evaluated and the
            better one is chosen.
        hard_stop_on_t1: When True, immediately return upon finding a
            TIER_1 window regardless of batch size (reference behaviour).
            When False, continue narrowing if the batch is still large.
        min_batch_threshold_multiplier: Minimum ratio of batch duration to
            fit_span_days below which bisection stops.  Reference uses
            2.01; current production default is 1.1.

    Returns:
        Tuple of (best_window, evaluated_windows)
    """
    if evaluated_windows is None:
        evaluated_windows = []

    batch_duration_days = (batch_end - batch_start).total_seconds() / 86400

    # Evaluate current batch
    current_eval = evaluate_window(obs_df, sat_params, batch_start, batch_end, criteria)
    evaluated_windows.append(current_eval)

    logger.debug(
        f"Bisection depth {depth}: {batch_start} to {batch_end} "
        f"({batch_duration_days:.1f} days) -> Tier {current_eval.tier.value}, "
        f"score {current_eval.overall_score:.2f}"
    )

    # Stop conditions:
    # 1. Reached max depth
    # 2. Batch is close to fit span (can't bisect further without going below)
    # 3. Found Tier 1 window
    #
    # The minimum bisectable duration uses min_batch_threshold_multiplier so
    # that reference mode can enforce the 2.01x threshold from windowCheck.py
    # while production keeps the tighter 1.1x (mapped to 1.5x via the
    # original constant below when the multiplier is at default).
    if min_batch_threshold_multiplier >= 2.0:
        # Reference-style: batch must be >= multiplier * fit_span to bisect
        min_bisect_duration = criteria.fit_span_days * min_batch_threshold_multiplier
    else:
        # Production-style: 1.5x was the original hardcoded constant
        min_bisect_duration = criteria.fit_span_days * 1.5

    if depth >= max_depth:
        logger.debug(f"Max depth {max_depth} reached")
        return current_eval, evaluated_windows

    if batch_duration_days <= min_bisect_duration:
        logger.debug(f"Batch duration {batch_duration_days:.1f} days <= min {min_bisect_duration:.1f}")
        return current_eval, evaluated_windows

    if current_eval.tier == WindowTier.TIER_1:
        if hard_stop_on_t1:
            # Reference behaviour: stop immediately on T1
            logger.debug("hard_stop_on_t1: TIER_1 found, returning immediately")
            return current_eval, evaluated_windows
        else:
            # Production behaviour: try to narrow it down unless batch is small
            if batch_duration_days <= criteria.fit_span_days * 2:
                return current_eval, evaluated_windows

    # Bisect: split into two halves
    midpoint = batch_start + (batch_end - batch_start) / 2

    if overlap_bisection:
        # Reference behaviour: overlapping regions around the midpoint.
        # Each half extends 0.5 x fit_span_days past the midpoint so the
        # two halves share a window_size-wide overlap region.
        overlap_delta = timedelta(days=0.5 * criteria.fit_span_days)
        first_half_end = midpoint + overlap_delta
        second_half_start = midpoint - overlap_delta

        # Clamp to batch boundaries
        first_half_end = min(first_half_end, batch_end)
        second_half_start = max(second_half_start, batch_start)
    else:
        # Production behaviour: clean midpoint split
        first_half_end = midpoint
        second_half_start = midpoint

    # --- short_circuit_first_half path (reference behaviour) ---
    if short_circuit_first_half:
        # Evaluate first half
        first_half_eval = evaluate_window(
            obs_df, sat_params, batch_start, first_half_end, criteria
        )
        evaluated_windows.append(first_half_eval)

        logger.debug(
            f"  [short-circuit] First half score: {first_half_eval.overall_score:.2f}"
        )

        # If the first half meets the current threshold, recurse into it
        # and never evaluate the second half.
        if first_half_eval.tier.value <= current_eval.tier.value:
            best_eval, evaluated_windows = _bisect_search(
                obs_df, sat_params, batch_start, first_half_end, criteria,
                depth + 1, max_depth, evaluated_windows,
                overlap_bisection=overlap_bisection,
                short_circuit_first_half=short_circuit_first_half,
                hard_stop_on_t1=hard_stop_on_t1,
                min_batch_threshold_multiplier=min_batch_threshold_multiplier,
            )
            if current_eval.overall_score > best_eval.overall_score:
                return current_eval, evaluated_windows
            return best_eval, evaluated_windows

        # First half did not pass -- fall through to second half
        second_half_eval = evaluate_window(
            obs_df, sat_params, second_half_start, batch_end, criteria
        )
        evaluated_windows.append(second_half_eval)

        logger.debug(
            f"  [short-circuit] Second half score: {second_half_eval.overall_score:.2f}"
        )

        best_eval, evaluated_windows = _bisect_search(
            obs_df, sat_params, second_half_start, batch_end, criteria,
            depth + 1, max_depth, evaluated_windows,
            overlap_bisection=overlap_bisection,
            short_circuit_first_half=short_circuit_first_half,
            hard_stop_on_t1=hard_stop_on_t1,
            min_batch_threshold_multiplier=min_batch_threshold_multiplier,
        )
        if current_eval.overall_score > best_eval.overall_score:
            return current_eval, evaluated_windows
        return best_eval, evaluated_windows

    # --- Production path: evaluate both halves, pick the better one ---
    # Evaluate first half
    first_half_eval = evaluate_window(
        obs_df, sat_params, batch_start, first_half_end, criteria
    )
    evaluated_windows.append(first_half_eval)

    # Evaluate second half
    second_half_eval = evaluate_window(
        obs_df, sat_params, second_half_start, batch_end, criteria
    )
    evaluated_windows.append(second_half_eval)

    logger.debug(
        f"  First half score: {first_half_eval.overall_score:.2f}, "
        f"Second half score: {second_half_eval.overall_score:.2f}"
    )

    # Choose the better half to continue searching
    # Prefer the half with:
    # 1. Better tier
    # 2. If same tier, better overall score
    # 3. If similar scores, prefer first half (earlier data)

    first_is_better = False
    if first_half_eval.tier.value < second_half_eval.tier.value:
        first_is_better = True
    elif first_half_eval.tier.value == second_half_eval.tier.value:
        if first_half_eval.overall_score >= second_half_eval.overall_score - 0.05:
            first_is_better = True

    if first_is_better:
        # Continue searching in first half
        best_eval, evaluated_windows = _bisect_search(
            obs_df, sat_params, batch_start, first_half_end, criteria,
            depth + 1, max_depth, evaluated_windows,
            overlap_bisection=overlap_bisection,
            short_circuit_first_half=short_circuit_first_half,
            hard_stop_on_t1=hard_stop_on_t1,
            min_batch_threshold_multiplier=min_batch_threshold_multiplier,
        )
    else:
        # Continue searching in second half
        best_eval, evaluated_windows = _bisect_search(
            obs_df, sat_params, second_half_start, batch_end, criteria,
            depth + 1, max_depth, evaluated_windows,
            overlap_bisection=overlap_bisection,
            short_circuit_first_half=short_circuit_first_half,
            hard_stop_on_t1=hard_stop_on_t1,
            min_batch_threshold_multiplier=min_batch_threshold_multiplier,
        )

    # Compare with current and return the best
    if current_eval.overall_score > best_eval.overall_score:
        return current_eval, evaluated_windows
    return best_eval, evaluated_windows


def _sliding_window_search(
    obs_df: pd.DataFrame,
    sat_params: Dict[int, Dict],
    batch_start: datetime,
    batch_end: datetime,
    criteria: WindowCriteria,
    step_fraction: float = 0.1,
    *,
    hard_stop_on_t1: bool = False,
) -> Tuple[WindowEvaluation, List[WindowEvaluation]]:
    """
    Sliding window search within a batch.

    Used when the batch is too small to bisect further. Slides a window
    of fit_span_days through the batch to find the optimal position.

    Args:
        obs_df: DataFrame of observations
        sat_params: Dict mapping satNo to orbital parameters
        batch_start: Start of batch
        batch_end: End of batch
        criteria: WindowCriteria instance
        step_fraction: Fraction of fit span to step (e.g., 0.1 = 10% steps)
        hard_stop_on_t1: When True, immediately return the first TIER_1
            window found without continuing to slide (reference behaviour).
            When False (default), the current behaviour of breaking the
            loop on TIER_1 is preserved (identical effect but documented
            explicitly for clarity).

    Returns:
        Tuple of (best_window, all_evaluated_windows)
    """
    evaluated_windows = []
    fit_span = timedelta(days=criteria.fit_span_days)
    step = timedelta(days=criteria.fit_span_days * step_fraction)

    batch_duration = batch_end - batch_start
    if batch_duration < fit_span:
        # Batch is smaller than fit span, evaluate entire batch
        window_eval = evaluate_window(obs_df, sat_params, batch_start, batch_end, criteria)
        return window_eval, [window_eval]

    best_eval = None
    current_start = batch_start

    while current_start + fit_span <= batch_end:
        current_end = current_start + fit_span

        window_eval = evaluate_window(obs_df, sat_params, current_start, current_end, criteria)
        evaluated_windows.append(window_eval)

        if best_eval is None or window_eval.overall_score > best_eval.overall_score:
            best_eval = window_eval

        # If we found Tier 1, we can stop
        if window_eval.tier == WindowTier.TIER_1:
            logger.debug(f"Found Tier 1 window at {current_start}")
            if hard_stop_on_t1:
                # Reference behaviour: return immediately, don't even
                # check the forced final bin.
                return best_eval, evaluated_windows
            break

        current_start += step

    return best_eval, evaluated_windows


def find_optimal_window(
    obs_df: pd.DataFrame,
    sat_params: Dict[int, Dict],
    batch_start: datetime,
    batch_end: datetime,
    criteria: WindowCriteria = None,
    use_sliding_after_bisect: bool = True,
    *,
    reference_mode: bool = False,
    normalize_backward: bool = False,
    overlap_bisection: bool = False,
    short_circuit_first_half: bool = False,
    hard_stop_on_t1: bool = False,
    min_batch_threshold_multiplier: float = 1.1,
    alignment_config: "ReferenceAlignmentConfig | None" = None,
) -> BisectionResult:
    """
    Find the optimal time window using Lewis's bisection algorithm.

    This is the main entry point for window selection. It:
    1. Performs binary search (bisection) to narrow down to a promising region
    2. Uses sliding window within that region to find the exact optimal window
    3. Returns the best window with tier classification

    Args:
        obs_df: DataFrame of observations with 'obTime', 'satNo' columns
        sat_params: Dict mapping satNo to orbital parameters
        batch_start: Start of the data batch to search
        batch_end: End of the data batch to search
        criteria: WindowCriteria instance (uses defaults if None)
        use_sliding_after_bisect: Whether to use sliding window refinement
        reference_mode: Convenience flag.  When True, sets
            normalize_backward, overlap_bisection,
            short_circuit_first_half, hard_stop_on_t1 all to True, and
            min_batch_threshold_multiplier to 2.01.  Provides a single
            switch to get reference-compatible (windowCheck.py) behaviour.
        normalize_backward: When True, add an ``epochNormalized`` column
            where 0 = newest observation (reference convention).  Does not
            change search logic directly but is available on the returned
            DataFrame for downstream consumers.
        overlap_bisection: Passed through to ``_bisect_search``.
        short_circuit_first_half: Passed through to ``_bisect_search``.
        hard_stop_on_t1: Passed through to ``_bisect_search`` and
            ``_sliding_window_search``.
        min_batch_threshold_multiplier: Passed through to
            ``_bisect_search``.
        alignment_config: Optional ``ReferenceAlignmentConfig`` instance.
            If provided, overrides individual alignment keyword arguments.

    Returns:
        BisectionResult with best window and search statistics
    """
    import time as _time
    start_time = _time.time()

    if criteria is None:
        criteria = WindowCriteria()

    # ---- Resolve alignment configuration ----
    if alignment_config is not None:
        cfg = alignment_config
    elif reference_mode:
        cfg = ReferenceAlignmentConfig.from_reference_mode(True)
    else:
        cfg = ReferenceAlignmentConfig(
            normalize_backward=normalize_backward,
            overlap_bisection=overlap_bisection,
            short_circuit_first_half=short_circuit_first_half,
            hard_stop_on_t1=hard_stop_on_t1,
            min_batch_threshold_multiplier=min_batch_threshold_multiplier,
        )

    # ---- Optional backward time normalization (reference behaviour) ----
    if cfg.normalize_backward and not obs_df.empty:
        obs_df = obs_df.copy()
        if obs_df["obTime"].dtype == "object":
            obs_df["obTime"] = pd.to_datetime(obs_df["obTime"])
        obs_df["epochNormalized"] = _normalize_time_backward(obs_df, "obTime")
        logger.debug(
            "normalize_backward: added epochNormalized column "
            f"(range {obs_df['epochNormalized'].min():.4f} -- "
            f"{obs_df['epochNormalized'].max():.4f} days)"
        )

    result = BisectionResult()

    logger.info(
        f"Starting window search: {batch_start} to {batch_end} "
        f"(fit span: {criteria.fit_span_days} days, "
        f"reference_mode={reference_mode or (alignment_config is not None and cfg.overlap_bisection)})"
    )

    # Phase 1: Bisection search to find promising region
    best_bisect, bisect_windows = _bisect_search(
        obs_df, sat_params, batch_start, batch_end, criteria,
        depth=0, max_depth=10,
        overlap_bisection=cfg.overlap_bisection,
        short_circuit_first_half=cfg.short_circuit_first_half,
        hard_stop_on_t1=cfg.hard_stop_on_t1,
        min_batch_threshold_multiplier=cfg.min_batch_threshold_multiplier,
    )
    result.evaluated_windows.extend(bisect_windows)
    result.bisection_depth = len(bisect_windows)

    logger.info(
        f"Bisection found window: Tier {best_bisect.tier.value}, "
        f"score {best_bisect.overall_score:.2f}"
    )

    # Phase 2: Sliding window refinement
    # In hard_stop_on_t1 mode, skip sliding when bisection already found T1.
    skip_sliding = cfg.hard_stop_on_t1 and best_bisect.tier == WindowTier.TIER_1

    if use_sliding_after_bisect and not skip_sliding and best_bisect.tier != WindowTier.TIER_1:
        # Expand the best window region slightly for sliding search
        region_start = best_bisect.start_time - timedelta(days=criteria.fit_span_days * 0.5)
        region_end = best_bisect.end_time + timedelta(days=criteria.fit_span_days * 0.5)

        # Clamp to original batch bounds
        region_start = max(region_start, batch_start)
        region_end = min(region_end, batch_end)

        best_slide, slide_windows = _sliding_window_search(
            obs_df, sat_params, region_start, region_end, criteria,
            step_fraction=slide_resolution if slide_resolution > 0 else 0.1,
            hard_stop_on_t1=cfg.hard_stop_on_t1,
        )
        result.evaluated_windows.extend(slide_windows)

        if best_slide.overall_score > best_bisect.overall_score:
            best_bisect = best_slide
            logger.info(
                f"Sliding window improved: Tier {best_slide.tier.value}, "
                f"score {best_slide.overall_score:.2f}"
            )

    result.best_window = best_bisect
    result.windows_evaluated = len(result.evaluated_windows)
    result.search_duration_seconds = _time.time() - start_time

    # Determine recommended action
    if best_bisect.tier == WindowTier.TIER_1:
        result.recommended_action = "use_as_is"
    elif best_bisect.tier == WindowTier.TIER_2:
        result.recommended_action = "downsample"
    elif best_bisect.tier == WindowTier.TIER_3:
        result.recommended_action = "simulate"
    elif best_bisect.tier == WindowTier.TIER_5:
        result.recommended_action = "criteria_impossible"
    else:
        result.recommended_action = "insufficient_data"

    logger.info(
        f"Window search complete: {result.windows_evaluated} windows evaluated, "
        f"best Tier {result.best_window.tier.value}, "
        f"recommended action: {result.recommended_action}"
    )

    return result


def find_optimal_window_with_decay(
    obs_df: pd.DataFrame,
    sat_params: Dict[int, Dict],
    data_start: datetime,
    data_end: datetime,
    criteria: WindowCriteria = None,
    max_iterations: int = 20,
    *,
    reference_mode: bool = False,
    normalize_backward: bool = False,
    overlap_bisection: bool = False,
    short_circuit_first_half: bool = False,
    hard_stop_on_t1: bool = False,
    min_batch_threshold_multiplier: float = 1.1,
    alignment_config: "ReferenceAlignmentConfig | None" = None,
) -> BisectionResult:
    """
    Find optimal window using iterative batch pulling with exponential decay.

    This implements Lewis's complete batch decay algorithm:
    1. Start with large batch (fitspan x batchSizeMultiplier)
    2. Each iteration, reduce batch size using exponential decay
    3. Search within each batch for optimal window
    4. Stop when criteria met or batch approaches fit span

    Per Lewis's specification:
    - Initial batch = fitspan x batchSizeMultiplier (5x by default)
    - Each iteration: batch_size = fit_span + (initial - fit_span) * exp(-decay_rate * iteration)
    - Decay rate = batchSizeDecayRate (0.01 by default)

    Reference-alignment parameters (all keyword-only):

    Args:
        obs_df: DataFrame of observations with 'obTime', 'satNo' columns
        sat_params: Dict mapping satNo to orbital parameters
        data_start: Earliest available data time
        data_end: Latest available data time
        criteria: WindowCriteria instance (uses defaults if None)
        max_iterations: Maximum number of decay iterations
        reference_mode: When True, activates all reference-alignment
            flags via ``ReferenceAlignmentConfig.from_reference_mode(True)``.
        normalize_backward: See ``find_optimal_window``.
        overlap_bisection: See ``find_optimal_window``.
        short_circuit_first_half: See ``find_optimal_window``.
        hard_stop_on_t1: See ``find_optimal_window``.
        min_batch_threshold_multiplier: Controls the minimum batch-to-
            fit-span ratio for the decay loop stop condition.  Reference
            uses 2.01 (``max(decayed, 2.01 * window_size)``); production
            default is 1.1.
        alignment_config: Optional ``ReferenceAlignmentConfig`` instance.
            If provided, overrides individual alignment keyword arguments.

    Returns:
        BisectionResult with best window and search statistics
    """
    import time as _time
    start_time = _time.time()

    if criteria is None:
        criteria = WindowCriteria()

    # ---- Resolve alignment configuration ----
    if alignment_config is not None:
        cfg = alignment_config
    elif reference_mode:
        cfg = ReferenceAlignmentConfig.from_reference_mode(True)
    else:
        cfg = ReferenceAlignmentConfig(
            normalize_backward=normalize_backward,
            overlap_bisection=overlap_bisection,
            short_circuit_first_half=short_circuit_first_half,
            hard_stop_on_t1=hard_stop_on_t1,
            min_batch_threshold_multiplier=min_batch_threshold_multiplier,
        )

    # Calculate initial batch size per Lewis's spec
    initial_batch_days = calculate_initial_batch_size(criteria.fit_span_days)
    data_duration_days = (data_end - data_start).total_seconds() / 86400

    logger.info(
        f"Starting iterative window search with decay: "
        f"initial batch={initial_batch_days:.1f} days, "
        f"fit span={criteria.fit_span_days} days, "
        f"data duration={data_duration_days:.1f} days, "
        f"min_batch_multiplier={cfg.min_batch_threshold_multiplier}"
    )

    best_result = None
    all_evaluated_windows = []

    for iteration in range(max_iterations):
        # Calculate batch size for this iteration using exponential decay
        batch_days = _calculate_next_batch_size(
            iteration, initial_batch_days, criteria.fit_span_days
        )

        # Reference behaviour: ensure batch never drops below
        # min_batch_threshold_multiplier * fit_span (reference uses 2.01x)
        batch_days = max(
            batch_days,
            criteria.fit_span_days * cfg.min_batch_threshold_multiplier,
        )

        # Stop if batch is effectively at fit span (using the multiplier)
        if batch_days <= criteria.fit_span_days * cfg.min_batch_threshold_multiplier:
            logger.debug(f"Iteration {iteration}: batch size {batch_days:.2f} days at minimum")
            break

        # Calculate batch boundaries (centered on available data)
        batch_half = timedelta(days=batch_days / 2)
        data_center = data_start + (data_end - data_start) / 2

        batch_start = max(data_start, data_center - batch_half)
        batch_end = min(data_end, data_center + batch_half)

        logger.debug(
            f"Iteration {iteration}: batch size={batch_days:.2f} days, "
            f"searching {batch_start} to {batch_end}"
        )

        # Run bisection search on this batch, passing alignment config
        result = find_optimal_window(
            obs_df, sat_params, batch_start, batch_end, criteria,
            use_sliding_after_bisect=True,
            alignment_config=cfg,
        )

        all_evaluated_windows.extend(result.evaluated_windows)

        # Keep track of best result
        if best_result is None or (
            result.best_window and
            result.best_window.overall_score > best_result.best_window.overall_score
        ):
            best_result = result

        # Stop if we found a Tier 1 window
        if result.best_window and result.best_window.tier == WindowTier.TIER_1:
            logger.info(f"Found Tier 1 window at iteration {iteration}")
            break

        # Stop if we found a usable window (Tier 2) and batch is getting small
        if (result.best_window and
            result.best_window.tier == WindowTier.TIER_2 and
            batch_days < initial_batch_days * 0.3):
            logger.info(f"Found Tier 2 window at iteration {iteration}, stopping")
            break

    # Update result statistics
    if best_result:
        best_result.evaluated_windows = all_evaluated_windows
        best_result.windows_evaluated = len(all_evaluated_windows)
        best_result.search_duration_seconds = _time.time() - start_time

    logger.info(
        f"Iterative search complete: {len(all_evaluated_windows)} windows evaluated, "
        f"best Tier {best_result.best_window.tier.value if best_result and best_result.best_window else 'None'}"
    )

    return best_result if best_result else BisectionResult()


def create_criteria_from_user_input(
    object_count: str = "standard",  # "high", "standard", "low"
    observation_count: str = "standard",
    orbital_coverage: str = "standard",
    track_gap: str = "standard",
    fit_span_days: float = 7.0,
    regimes: List[str] = None,
    object_types: List[str] = None,
) -> WindowCriteria:
    """
    Create WindowCriteria from user-friendly input strings.

    Args:
        object_count: "high", "standard", or "low"
        observation_count: "high", "standard", or "low"
        orbital_coverage: "high", "standard", or "low"
        track_gap: "short", "standard", or "long"
        fit_span_days: Duration of data window in days
        regimes: List of orbital regimes to include
        object_types: List of object types to include

    Returns:
        WindowCriteria instance
    """
    # Object count mapping
    obj_count_map = {
        "high": (60, 80, 100),      # min, target, max
        "standard": (30, 40, 60),
        "low": (5, 10, 20),
    }

    # Observation count mapping
    obs_count_map = {
        "high": (100, 150, 250),
        "standard": (30, 50, 100),
        "low": (5, 10, 30),
    }

    # Coverage mapping (fraction of orbit)
    coverage_map = {
        "high": (0.20, 0.50, 0.80),
        "standard": (0.05, 0.15, 0.30),
        "low": (0.01, 0.03, 0.10),
    }

    # Track gap mapping (orbital periods)
    gap_map = {
        "short": (0.2, 0.5, 1.0),
        "standard": (1.0, 2.0, 4.0),
        "long": (3.0, 5.0, 10.0),
    }

    obj_min, obj_target, obj_max = obj_count_map.get(object_count, obj_count_map["standard"])
    obs_min, obs_target, obs_max = obs_count_map.get(observation_count, obs_count_map["standard"])
    cov_min, cov_target, cov_max = coverage_map.get(orbital_coverage, coverage_map["standard"])
    gap_min, gap_target, gap_max = gap_map.get(track_gap, gap_map["standard"])

    return WindowCriteria(
        min_objects=obj_min,
        target_objects=obj_target,
        max_objects=obj_max,
        min_obs_per_object=obs_min,
        target_obs_per_object=obs_target,
        max_obs_per_object=obs_max,
        min_coverage=cov_min,
        target_coverage=cov_target,
        max_coverage=cov_max,
        min_track_gap_periods=gap_min,
        target_track_gap_periods=gap_target,
        max_track_gap_periods=gap_max,
        fit_span_days=fit_span_days,
        regimes=regimes or ["LEO", "MEO", "GEO"],
        object_types=object_types or ["NORM"],
    )


# =============================================================================
# INTEGRATION HELPER: Connect window selection to pipeline
# =============================================================================


def select_optimal_window_for_dataset(
    obs_df: pd.DataFrame,
    sat_params: Dict[int, Dict],
    fit_span_days: float = 7.0,
    quality_level: str = "standard",
    regimes: List[str] = None,
    *,
    reference_mode: bool = False,
    alignment_config: "ReferenceAlignmentConfig | None" = None,
) -> Tuple[pd.DataFrame, WindowEvaluation, str]:
    """
    High-level function to select optimal window for dataset generation.

    This integrates with the main pipeline by:
    1. Creating criteria from quality level
    2. Running bisection search
    3. Returning filtered observations and recommended action

    Args:
        obs_df: DataFrame of all observations
        sat_params: Dict mapping satNo to orbital parameters
        fit_span_days: Desired duration of dataset
        quality_level: "high", "standard", or "low"
        regimes: Orbital regimes to include
        reference_mode: Convenience flag -- when True activates all
            reference-alignment behaviours.  See ``find_optimal_window``
            for details.
        alignment_config: Optional ``ReferenceAlignmentConfig`` instance.

    Returns:
        Tuple of:
        - Filtered observation DataFrame (within optimal window)
        - WindowEvaluation with metrics
        - Recommended action ("use_as_is", "downsample", "simulate")
    """
    if obs_df.empty:
        return obs_df, WindowEvaluation(), "insufficient_data"

    # Determine batch boundaries from observations
    obs_df = obs_df.copy()
    if obs_df["obTime"].dtype == "object":
        obs_df["obTime"] = pd.to_datetime(obs_df["obTime"])

    batch_start = obs_df["obTime"].min()
    batch_end = obs_df["obTime"].max()

    # Handle timezone
    if hasattr(batch_start, "tzinfo") and batch_start.tzinfo is not None:
        batch_start = batch_start.to_pydatetime()
        batch_end = batch_end.to_pydatetime()

    # Create criteria
    criteria = create_criteria_from_user_input(
        object_count=quality_level,
        observation_count=quality_level,
        orbital_coverage=quality_level,
        track_gap="standard",
        fit_span_days=fit_span_days,
        regimes=regimes,
    )

    # Resolve alignment config
    if alignment_config is None and reference_mode:
        alignment_config = ReferenceAlignmentConfig.from_reference_mode(True)

    # Run window search
    result = find_optimal_window(
        obs_df, sat_params, batch_start, batch_end, criteria,
        reference_mode=reference_mode,
        alignment_config=alignment_config,
    )

    # Filter observations to best window
    if result.best_window and result.best_window.start_time:
        window_start = result.best_window.start_time
        window_end = result.best_window.end_time

        # Handle timezone matching: use tz_convert if already aware, else tz_localize
        if obs_df["obTime"].dt.tz is not None:
            col_tz = obs_df["obTime"].dt.tz
            ts_ws = pd.Timestamp(window_start)
            ts_we = pd.Timestamp(window_end)
            window_start = ts_ws.tz_convert(col_tz) if ts_ws.tzinfo is not None else ts_ws.tz_localize(col_tz)
            window_end = ts_we.tz_convert(col_tz) if ts_we.tzinfo is not None else ts_we.tz_localize(col_tz)

        filtered_obs = obs_df[
            (obs_df["obTime"] >= window_start) &
            (obs_df["obTime"] <= window_end)
        ].copy()
    else:
        filtered_obs = obs_df

    return filtered_obs, result.best_window, result.recommended_action


# =============================================================================
# LEGACY CODE INTEGRATION: Create criteria from 16-character dataset code
# =============================================================================


def create_criteria_from_legacy_code(
    legacy_code: str = None,
    object_type: str = "U",
    target_percentage: str = "50",
    orbital_regime: str = "LEO",
    event: str = "NE",
    sensor_type: str = "OP",
    orbit_coverage: str = "S",
    track_gap: str = "S",
    observation_count: str = "S",
    object_count: str = "S",
    fitspan_days: int = 7,
) -> WindowCriteria:
    """
    Create WindowCriteria from a legacy 16-character dataset code.

    Maps the A/S/N quality levels to numeric thresholds for coverage,
    track gaps, and observation counts.

    Args:
        legacy_code: Optional 16-character code (if provided, overrides other params)
        object_type: H, C, A, U, N
        target_percentage: 50, 10, 01, UN
        orbital_regime: LEO, MEO, GEO, HEO, ALL
        event: MB, BU, LL, NE
        sensor_type: OP, RA, RF, FU, OR, RO, RR
        orbit_coverage: A, S, N (All/High, Standard, None/Low)
        track_gap: A, S, N
        observation_count: A, S, N
        object_count: H, S, L (High=80, Standard=40, Low=10)
        fitspan_days: 1-14 days

    Returns:
        WindowCriteria configured from the legacy code parameters
    """
    # Parse legacy code if provided
    if legacy_code and len(legacy_code) == 16:
        from uct_benchmark.config.dataset_schema import LegacyDatasetCode
        parsed = LegacyDatasetCode.from_code(legacy_code)
        object_type = parsed.object_type
        target_percentage = parsed.target_percentage
        orbital_regime = parsed.orbital_regime
        event = parsed.event
        sensor_type = parsed.sensor_type
        orbit_coverage = parsed.orbit_coverage
        track_gap = parsed.track_gap
        observation_count = parsed.observation_count
        object_count = parsed.object_count
        fitspan_days = parsed.fitspan_days

    # Map A/S/N quality levels to thresholds
    coverage_thresholds = QUALITY_LEVEL_THRESHOLDS["coverage"]
    gap_thresholds = QUALITY_LEVEL_THRESHOLDS["track_gap"]
    obs_thresholds = QUALITY_LEVEL_THRESHOLDS["observation_count"]

    # Get coverage bounds from quality level
    cov_min, cov_max = coverage_thresholds.get(orbit_coverage, (0.40, 0.60))

    # Map to actual coverage values per Louis's documentation:
    # A = >90% of objects have LOW orbital coverage (sparse dataset)
    # S = 40-60% of objects have LOW orbital coverage (mixed)
    # N = <10% of objects have LOW orbital coverage (most have good coverage)
    coverage_ranges = {
        "A": (0.01, 0.03, 0.10),   # Most objects have LOW coverage (sparse data)
        "S": (0.05, 0.15, 0.30),   # Mixed coverage
        "N": (0.30, 0.50, 0.80),   # Few objects have LOW coverage (most have high/dense)
    }
    cov_min_val, cov_target_val, cov_max_val = coverage_ranges.get(orbit_coverage, coverage_ranges["S"])

    # Map track gap A/S/N to actual orbital periods per Louis's documentation:
    # A = >90% of objects have LONG track gaps (sparse tracking)
    # S = 40-60% of objects have LONG track gaps (mixed)
    # N = <10% of objects have LONG track gaps (dense tracking)
    gap_ranges = {
        "A": (3.0, 5.0, 10.0),  # Most objects have LONG gaps (sparse tracking)
        "S": (1.0, 2.0, 4.0),   # Mixed gaps
        "N": (0.2, 0.5, 1.0),   # Few objects have LONG gaps (dense tracking)
    }
    gap_min_val, gap_target_val, gap_max_val = gap_ranges.get(track_gap, gap_ranges["S"])

    # Map observation count A/S/N to actual counts per satellite per Louis's documentation:
    # A = >90% of objects have LOW observation count (sparse)
    # S = 40-60% of objects have LOW observation count (mixed)
    # N = <10% of objects have LOW observation count (most have many observations)
    obs_ranges = {
        "A": (5, 10, 30),      # Most objects have LOW obs count (sparse)
        "S": (30, 50, 100),    # Mixed observation counts
        "N": (100, 150, 250),  # Few objects have LOW obs count (most have high density)
    }
    obs_min_val, obs_target_val, obs_max_val = obs_ranges.get(observation_count, obs_ranges["S"])

    # Map object count H/S/L to actual numbers
    obj_count_val = OBJECT_COUNT_MAP.get(object_count, 40)

    # Set object count ranges based on level
    obj_ranges = {
        "H": (60, 80, 100),    # High: 60-100 objects, target 80
        "S": (30, 40, 60),     # Standard: 30-60 objects, target 40
        "L": (5, 10, 20),      # Low: 5-20 objects, target 10
    }
    obj_min_val, obj_target_val, obj_max_val = obj_ranges.get(object_count, obj_ranges["S"])

    # Determine regimes to include
    regime_map = {
        "LEO": ["LEO"],
        "MEO": ["MEO"],
        "GEO": ["GEO"],
        "HEO": ["HEO"],
        "ALL": ["LEO", "MEO", "GEO", "HEO"],
        "LMO": ["LEO", "MEO"],
        "LMG": ["LEO", "MEO", "GEO"],
        "MGH": ["MEO", "GEO", "HEO"],
    }
    regimes = regime_map.get(orbital_regime, ["LEO"])

    # Determine object types based on object_type code
    obj_type_map = {
        "H": ["HAMR"],
        "C": ["PROX"],
        "A": ["APRX"],
        "U": ["NORM"],
        "N": ["CALIB"],
    }
    object_types = obj_type_map.get(object_type, ["NORM"])

    logger.info(
        f"Creating criteria from legacy code: coverage={orbit_coverage} ({cov_min_val:.2f}-{cov_max_val:.2f}), "
        f"gap={track_gap} ({gap_min_val:.1f}-{gap_max_val:.1f}), "
        f"obs={observation_count} ({obs_min_val}-{obs_max_val}), "
        f"objects={object_count} ({obj_min_val}-{obj_max_val})"
    )

    return WindowCriteria(
        min_objects=obj_min_val,
        target_objects=obj_target_val,
        max_objects=obj_max_val,
        min_obs_per_object=obs_min_val,
        target_obs_per_object=obs_target_val,
        max_obs_per_object=obs_max_val,
        min_coverage=cov_min_val,
        target_coverage=cov_target_val,
        max_coverage=cov_max_val,
        min_track_gap_periods=gap_min_val,
        target_track_gap_periods=gap_target_val,
        max_track_gap_periods=gap_max_val,
        fit_span_days=float(fitspan_days),
        regimes=regimes,
        object_types=object_types,
    )


# =============================================================================
# ORBITAL COVERAGE CALCULATION (per Louis's Benchmarking Documentation)
# =============================================================================


def calculate_orbital_coverage_polygon(
    observations: pd.DataFrame,
    orbital_period: float,
    epoch_column: str = "obTime",
) -> float:
    """
    Calculate orbital coverage using convex polygon on circumscribed circle.

    Per Louis's Benchmarking Documentation:
    - Project observation times onto unit circle (one revolution = 2π)
    - Compute convex hull of projected points
    - Coverage = 1 - (largest_gap / 2π)

    This method accounts for the circular nature of orbits, where observations
    at the beginning and end of a period should be considered "close" if they
    span across the period boundary.

    Args:
        observations: DataFrame with epoch column (datetime)
        orbital_period: Satellite orbital period in seconds
        epoch_column: Name of the datetime column (default 'obTime')

    Returns:
        Coverage fraction [0.0, 1.0]
    """
    if len(observations) < 2:
        return 0.0

    if orbital_period <= 0:
        logger.warning(f"Invalid orbital period: {orbital_period}")
        return 0.0

    # Convert epochs to phase angles on unit circle
    obs_df = observations.copy()
    if obs_df[epoch_column].dtype == "object":
        obs_df[epoch_column] = pd.to_datetime(obs_df[epoch_column])

    epochs = obs_df[epoch_column]
    t0 = epochs.min()
    phase_angles = []

    for epoch in epochs:
        elapsed_seconds = (epoch - t0).total_seconds()
        # Map to [0, 2π) based on orbital period
        phase = (2 * np.pi * elapsed_seconds / orbital_period) % (2 * np.pi)
        phase_angles.append(phase)

    phase_angles = np.array(phase_angles)

    # Remove duplicates and sort
    unique_phases = np.unique(phase_angles)
    if len(unique_phases) < 2:
        return 0.0

    unique_phases = np.sort(unique_phases)

    # Calculate gaps between consecutive phase angles
    # Include the wrap-around gap from last to first
    gaps = np.diff(unique_phases)
    wrap_gap = 2 * np.pi - unique_phases[-1] + unique_phases[0]
    all_gaps = np.append(gaps, wrap_gap)

    # Coverage = 1 - (largest_gap / 2π)
    # This represents the fraction of the orbit that is "covered" by observations
    # A large gap means poor coverage of that portion of the orbit
    largest_gap = np.max(all_gaps)
    coverage = 1.0 - (largest_gap / (2 * np.pi))

    return max(0.0, min(1.0, coverage))


def calculate_orbital_coverage_polygon_with_hull(
    observations: pd.DataFrame,
    orbital_period: float,
    epoch_column: str = "obTime",
) -> float:
    """
    Calculate orbital coverage using scipy ConvexHull on unit circle.

    Alternative implementation using actual convex hull computation.
    This is more computationally expensive but may be more accurate
    for irregularly distributed observations.

    Args:
        observations: DataFrame with epoch column (datetime)
        orbital_period: Satellite orbital period in seconds
        epoch_column: Name of the datetime column (default 'obTime')

    Returns:
        Coverage fraction [0.0, 1.0]
    """
    from scipy.spatial import ConvexHull

    if len(observations) < 3:  # Need at least 3 points for convex hull
        return calculate_orbital_coverage_polygon(observations, orbital_period, epoch_column)

    if orbital_period <= 0:
        return 0.0

    # Convert epochs to phase angles
    obs_df = observations.copy()
    if obs_df[epoch_column].dtype == "object":
        obs_df[epoch_column] = pd.to_datetime(obs_df[epoch_column])

    epochs = obs_df[epoch_column]
    t0 = epochs.min()

    # Convert to unit circle coordinates
    points = []
    for epoch in epochs:
        elapsed_seconds = (epoch - t0).total_seconds()
        phase = (2 * np.pi * elapsed_seconds / orbital_period) % (2 * np.pi)
        x = np.cos(phase)
        y = np.sin(phase)
        points.append([x, y])

    points = np.array(points)

    # Remove near-duplicate points (within numerical tolerance)
    unique_points = np.unique(np.round(points, decimals=10), axis=0)
    if len(unique_points) < 3:
        return calculate_orbital_coverage_polygon(observations, orbital_period, epoch_column)

    try:
        # Compute convex hull
        hull = ConvexHull(unique_points)

        # Get hull vertices in order
        hull_points = unique_points[hull.vertices]

        # Calculate angles of hull vertices
        hull_angles = np.arctan2(hull_points[:, 1], hull_points[:, 0])
        # Convert to [0, 2π) range
        hull_angles = (hull_angles + 2 * np.pi) % (2 * np.pi)
        hull_angles = np.sort(hull_angles)

        # Calculate gaps between hull vertices
        gaps = np.diff(hull_angles)
        wrap_gap = 2 * np.pi - hull_angles[-1] + hull_angles[0]
        all_gaps = np.append(gaps, wrap_gap)

        # Coverage = 1 - (largest_gap / 2π)
        coverage = 1.0 - (np.max(all_gaps) / (2 * np.pi))
        return max(0.0, min(1.0, coverage))

    except Exception as e:
        logger.warning(f"ConvexHull failed: {e}, falling back to simple method")
        return calculate_orbital_coverage_polygon(observations, orbital_period, epoch_column)


def is_low_coverage(coverage: float, regime: str) -> bool:
    """
    Check if coverage is considered LOW for a given orbital regime.

    Per Louis's Benchmarking Documentation thresholds:
    - LEO: < 0.0213% (0.000213)
    - MEO: < 0.0449% (0.000449)
    - GEO: < 41.656% (0.41656)

    Args:
        coverage: Coverage fraction [0.0, 1.0]
        regime: Orbital regime ("LEO", "MEO", "GEO")

    Returns:
        True if coverage is below the LOW threshold for the regime
    """
    threshold = COVERAGE_THRESHOLDS.get(regime.upper(), COVERAGE_THRESHOLDS.get("LEO", 0.000213))
    return coverage < threshold


# =============================================================================
# A/S/N QUALITY INTERPRETATION (per Louis's Specification)
# =============================================================================


def interpret_quality_code(quality_char: str) -> dict:
    """
    Interpret A/S/N quality character per Louis's specification.

    Per Benchmarking Documentation (% of objects with LOW quality):
    - A (All-sparse):   >90% of objects have LOW quality (sparse dataset)
    - S (Standard):     40-60% of objects have LOW quality (mixed dataset)
    - N (None-sparse):  <10% of objects have LOW quality (dense dataset)

    "LOW" is defined by coverage/track-gap/obs-count thresholds:
    - Coverage LOW: < regime threshold (LEO 0.0213%, MEO 0.0449%, GEO 41.656%)
    - Track Gap LOW: > 2 orbital periods between tracks
    - Obs Count LOW: < 50 observations per 3-day span

    Args:
        quality_char: Single character 'A', 'S', or 'N'

    Returns:
        Dict with 'min_pct' and 'max_pct' of objects that should have LOW quality
    """
    return QUALITY_RANGES.get(quality_char.upper(), QUALITY_RANGES['S'])


def generate_dataset_with_quality_distribution(
    objects: List[pd.DataFrame],
    quality_char: str,
    metric_type: str,
    regime: str = "LEO",
    orbital_periods: Optional[Dict[int, float]] = None,
) -> List[pd.DataFrame]:
    """
    Generate dataset where specified percentage of objects have LOW quality.

    Per Louis's specification, A/S/N codes determine what percentage of
    objects in the dataset should have LOW quality for a given metric.

    Args:
        objects: List of DataFrames, one per satellite (with 'satNo' column)
        quality_char: 'A', 'S', or 'N'
        metric_type: Which quality metric to evaluate ("coverage", "track_gap", or "obs_count")
        regime: Orbital regime for threshold lookup
        orbital_periods: Optional dict mapping satNo to period in seconds

    Returns:
        Modified list of DataFrames with correct quality distribution
    """
    if not objects:
        return objects

    quality_range = interpret_quality_code(quality_char)
    target_pct = (quality_range['min_pct'] + quality_range['max_pct']) / 2

    n_objects = len(objects)
    n_low_quality = int(n_objects * target_pct)

    # Randomly select which objects get LOW quality
    low_quality_indices = set(np.random.choice(n_objects, n_low_quality, replace=False))

    result = []
    for i, obj_df in enumerate(objects):
        if i in low_quality_indices:
            # This object should have LOW quality - may need downsampling
            # (actual downsampling happens in dataManipulation.py)
            obj_df = obj_df.copy()
            obj_df['_target_quality'] = 'LOW'
        else:
            obj_df = obj_df.copy()
            obj_df['_target_quality'] = 'HIGH'
        result.append(obj_df)

    logger.info(
        f"Quality distribution for {quality_char}: {n_low_quality}/{n_objects} "
        f"({n_low_quality/n_objects*100:.1f}%) objects targeted for LOW {metric_type}"
    )

    return result


# =============================================================================
# BISECTION WITH SHORT-CIRCUIT (per Louis's Specification)
# =============================================================================


def bisection_window_selection(
    observations: pd.DataFrame,
    quality_check_fn: Callable[[pd.DataFrame], bool],
    min_window_size: int = 10,
    epoch_column: str = "obTime",
) -> List[pd.DataFrame]:
    """
    Bisection window selection with short-circuit evaluation.

    Per Louis's specification:
    1. Check if full window passes quality check
    2. If passes, return full window
    3. If fails, split in half
    4. Check FIRST half only
    5. If first half passes, use it (short-circuit - don't check second)
    6. If first half fails, recursively bisect it
    7. Only check second half if first half exhausted

    This is more efficient than evaluating both halves and implements
    the specific algorithm described in Louis's documentation.

    Args:
        observations: DataFrame sorted by epoch
        quality_check_fn: Function returning True if window meets quality criteria
        min_window_size: Minimum observations in a window
        epoch_column: Name of the epoch/time column

    Returns:
        List of qualifying observation windows
    """
    def _bisect_recursive(obs_window: pd.DataFrame) -> List[pd.DataFrame]:
        # Base case: window too small
        if len(obs_window) < min_window_size:
            return []

        # Check if current window passes
        if quality_check_fn(obs_window):
            return [obs_window]

        # Split window in half (by observation count, not time)
        mid = len(obs_window) // 2
        first_half = obs_window.iloc[:mid].copy()
        second_half = obs_window.iloc[mid:].copy()

        # SHORT-CIRCUIT: Check first half first
        first_results = _bisect_recursive(first_half)
        if first_results:
            return first_results  # Don't check second half if first succeeds

        # Only check second half if first half failed
        return _bisect_recursive(second_half)

    # Ensure observations are sorted by time
    obs_sorted = observations.sort_values(epoch_column).copy()

    return _bisect_recursive(obs_sorted)


def bisection_window_selection_time_based(
    observations: pd.DataFrame,
    quality_check_fn: Callable[[pd.DataFrame], bool],
    min_duration_seconds: float = 3600,
    epoch_column: str = "obTime",
) -> List[pd.DataFrame]:
    """
    Bisection window selection based on time duration with short-circuit.

    Similar to bisection_window_selection but splits based on time
    rather than observation count.

    Args:
        observations: DataFrame with epoch column
        quality_check_fn: Function returning True if window meets quality criteria
        min_duration_seconds: Minimum window duration in seconds
        epoch_column: Name of the epoch/time column

    Returns:
        List of qualifying observation windows
    """
    def _get_duration(obs_window: pd.DataFrame) -> float:
        if len(obs_window) < 2:
            return 0.0
        return (obs_window[epoch_column].max() - obs_window[epoch_column].min()).total_seconds()

    def _bisect_recursive(obs_window: pd.DataFrame) -> List[pd.DataFrame]:
        # Base case: window duration too short
        if _get_duration(obs_window) < min_duration_seconds:
            return []

        if len(obs_window) < 3:
            return []

        # Check if current window passes
        if quality_check_fn(obs_window):
            return [obs_window]

        # Split window in half by time
        start_time = obs_window[epoch_column].min()
        end_time = obs_window[epoch_column].max()
        mid_time = start_time + (end_time - start_time) / 2

        first_half = obs_window[obs_window[epoch_column] <= mid_time].copy()
        second_half = obs_window[obs_window[epoch_column] > mid_time].copy()

        # SHORT-CIRCUIT: Check first half first
        if len(first_half) >= 3:
            first_results = _bisect_recursive(first_half)
            if first_results:
                return first_results  # Don't check second half if first succeeds

        # Only check second half if first half failed
        if len(second_half) >= 3:
            return _bisect_recursive(second_half)

        return []

    # Ensure observations are sorted by time
    obs_sorted = observations.sort_values(epoch_column).copy()
    if obs_sorted[epoch_column].dtype == "object":
        obs_sorted[epoch_column] = pd.to_datetime(obs_sorted[epoch_column])

    return _bisect_recursive(obs_sorted)
