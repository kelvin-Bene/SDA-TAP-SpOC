# -*- coding: utf-8 -*-
"""
Event Detection Module

This module provides infrastructure for detecting and filtering orbital events
as described by Lewis:
1. Maneuver events - object thrusts between observations
2. Breakup events - one object becomes many
3. Long-duration low-thrust maneuvers - subtle maneuvering over time

Lewis noted: "We need a database of when objects are maneuvering...
That's something we didn't have readily available."

This module implements:
- Event type definitions and data structures
- TLE discontinuity detection (proxy for maneuver detection)
- Infrastructure for integrating with event databases
- Event filtering for dataset generation

Author: UCT Benchmark Team
Date: 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


class EventType(Enum):
    """Types of orbital events."""
    MANEUVER = "maneuver"              # Impulsive maneuver
    LONG_THRUST = "long_thrust"        # Long-duration low-thrust
    BREAKUP = "breakup"                # Fragmentation/breakup
    COLLISION = "collision"            # Collision event
    LAUNCH = "launch"                  # Launch/deployment
    REENTRY = "reentry"                # Atmospheric reentry
    PROXIMITY = "proximity"            # Close approach
    UNKNOWN = "unknown"                # Detected anomaly, unknown type


@dataclass
class OrbitalEvent:
    """Represents a detected or known orbital event."""

    event_type: EventType
    satellite_id: int                  # Primary satellite NORAD ID
    event_time: datetime               # Time of event (or start time)
    end_time: Optional[datetime] = None  # End time for long-duration events

    # Event characteristics
    confidence: float = 0.0            # Detection confidence (0-1)
    delta_v_m_s: Optional[float] = None  # Estimated delta-V for maneuvers
    direction: Optional[str] = None    # Direction (in-track, cross-track, radial)

    # For breakup/collision events
    secondary_ids: List[int] = field(default_factory=list)  # Related objects
    fragment_count: Optional[int] = None

    # Source information
    source: str = "unknown"            # Where event info came from
    source_id: Optional[str] = None    # ID in source database

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventDetectionConfig:
    """Configuration for event detection."""

    # TLE discontinuity thresholds
    sma_threshold_km: float = 10.0           # Semi-major axis change threshold
    ecc_threshold: float = 0.001             # Eccentricity change threshold
    inc_threshold_deg: float = 0.1           # Inclination change threshold
    raan_threshold_deg: float = 1.0          # RAAN change threshold
    mean_motion_threshold: float = 0.001     # Mean motion change (rev/day)

    # Time windows
    min_gap_hours: float = 1.0               # Minimum gap between TLEs
    max_gap_days: float = 7.0                # Maximum gap to consider continuous

    # Confidence thresholds
    maneuver_confidence_threshold: float = 0.7
    breakup_confidence_threshold: float = 0.8

    # Long-thrust detection
    long_thrust_duration_days: float = 7.0   # Min duration for long-thrust
    long_thrust_rate_threshold: float = 0.5  # m/s per day max rate

    # ML Model availability (per Louis's note about ML Labelling Team)
    ml_model_available: bool = False         # Set True when ML model is operational
    use_tle_fallback: bool = True            # Use TLE-based detection when ML unavailable
    warn_on_ml_unavailable: bool = True      # Log warning when ML model not available


# =============================================================================
# ML MODEL AVAILABILITY CHECK
# =============================================================================


def check_ml_model_availability() -> Tuple[bool, str]:
    """
    Check if the ML event labelling model is available.

    Per Louis's specification in the transcript:
    "Since the UDL does not contain these events directly, we are relying on
    the ML Labelling Team to feed us the NORAD IDs and Observation times
    corresponding to these events. As of the writing of this report, the
    ML Model is not operating."

    Returns:
        Tuple of (is_available, status_message)
    """
    import os

    # Check for ML model endpoint or configuration
    ml_endpoint = os.environ.get("UCT_ML_EVENT_ENDPOINT")
    ml_api_key = os.environ.get("UCT_ML_EVENT_API_KEY")

    if ml_endpoint and ml_api_key:
        # Try to ping the endpoint
        try:
            import requests
            response = requests.get(
                f"{ml_endpoint}/health",
                headers={"Authorization": f"Bearer {ml_api_key}"},
                timeout=5
            )
            if response.status_code == 200:
                return True, "ML event labelling model is operational"
        except Exception as e:
            logger.debug(f"ML model health check failed: {e}")

    return False, (
        "ML event labelling model is NOT available. "
        "Event detection (MB/BU/LL) will use TLE-based heuristics as fallback. "
        "For accurate event detection, configure UCT_ML_EVENT_ENDPOINT and "
        "UCT_ML_EVENT_API_KEY environment variables. "
        "Only 'NE' (No Events) filtering is fully reliable without ML model."
    )


def get_event_code_reliability(event_code: str, ml_available: bool = None) -> Dict[str, Any]:
    """
    Get reliability information for a given event code.

    Per Louis's specification, event detection reliability depends on
    data sources available.

    Args:
        event_code: Two-character event code (MB, BU, LL, NE)
        ml_available: Override for ML availability check

    Returns:
        Dict with reliability info including 'reliable', 'fallback_method', 'warning'
    """
    if ml_available is None:
        ml_available, _ = check_ml_model_availability()

    reliability_info = {
        "event_code": event_code,
        "ml_model_available": ml_available,
        "reliable": False,
        "fallback_method": None,
        "warning": None,
        "recommendation": None,
    }

    if event_code == "NE":
        # No Events is always reliable - we're selecting satellites WITHOUT events
        reliability_info["reliable"] = True
        reliability_info["fallback_method"] = "tle_discontinuity_absence"
        reliability_info["recommendation"] = "Fully supported - use as needed"

    elif event_code == "MB":
        # Maneuver Between - requires either ML or TLE discontinuity detection
        if ml_available:
            reliability_info["reliable"] = True
            reliability_info["fallback_method"] = "ml_model"
        else:
            reliability_info["reliable"] = False
            reliability_info["fallback_method"] = "tle_discontinuity_detection"
            reliability_info["warning"] = (
                "MB detection using TLE discontinuity heuristics. "
                "May miss subtle maneuvers or produce false positives."
            )
            reliability_info["recommendation"] = (
                "Consider using 'NE' instead for reliable datasets, "
                "or validate detected maneuvers manually."
            )

    elif event_code == "BU":
        # Breakup - requires Space-Track/CelesTrak integration
        reliability_info["reliable"] = True  # Database-driven, not ML-dependent
        reliability_info["fallback_method"] = "spacetrack_celestrak_database"
        reliability_info["recommendation"] = (
            "Reliability depends on Space-Track API access. "
            "Set SPACETRACK_TOKEN environment variable."
        )

    elif event_code == "LL":
        # Long-duration Low-thrust - challenging to detect without ML
        if ml_available:
            reliability_info["reliable"] = True
            reliability_info["fallback_method"] = "ml_model"
        else:
            reliability_info["reliable"] = False
            reliability_info["fallback_method"] = "tle_trend_analysis"
            reliability_info["warning"] = (
                "LL detection using TLE trend analysis. "
                "Low-thrust maneuvers are difficult to distinguish from natural perturbations. "
                "Results may have significant uncertainty."
            )
            reliability_info["recommendation"] = (
                "Consider using 'NE' for reliable datasets, "
                "or treat LL-filtered datasets as approximate."
            )

    return reliability_info


# =============================================================================
# TLE DISCONTINUITY DETECTION
# =============================================================================


def compute_orbital_elements_from_tle(tle_line2: str) -> Dict[str, float]:
    """
    Extract orbital elements from TLE line 2.

    Args:
        tle_line2: TLE line 2 string

    Returns:
        Dict with orbital elements
    """
    try:
        # Parse TLE line 2
        # Format: 2 NNNNN III.IIII RRR.RRRR EEEEEEE AAA.AAAA MMM.MMMM NN.NNNNNNNN RRRRR
        inclination = float(tle_line2[8:16])
        raan = float(tle_line2[17:25])
        eccentricity = float("0." + tle_line2[26:33])
        arg_perigee = float(tle_line2[34:42])
        mean_anomaly = float(tle_line2[43:51])
        mean_motion = float(tle_line2[52:63])

        # Compute semi-major axis from mean motion
        # n = sqrt(mu/a^3) => a = (mu/n^2)^(1/3)
        # mean_motion is in rev/day, convert to rad/s
        n_rad_s = mean_motion * 2 * np.pi / 86400
        mu = 398600.4418  # km^3/s^2
        if n_rad_s > 0:
            sma = (mu / (n_rad_s ** 2)) ** (1/3)
        else:
            sma = 0

        return {
            "inclination_deg": inclination,
            "raan_deg": raan,
            "eccentricity": eccentricity,
            "arg_perigee_deg": arg_perigee,
            "mean_anomaly_deg": mean_anomaly,
            "mean_motion_rev_day": mean_motion,
            "semi_major_axis_km": sma,
        }
    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to parse TLE line 2: {e}")
        return {}


def detect_tle_discontinuity(
    tle_before: Dict[str, float],
    tle_after: Dict[str, float],
    config: EventDetectionConfig = None,
) -> Tuple[bool, float, Dict[str, Any]]:
    """
    Detect orbital discontinuity between two TLEs.

    A significant change in orbital elements between consecutive TLEs
    indicates a possible maneuver or other event.

    Args:
        tle_before: Orbital elements from earlier TLE
        tle_after: Orbital elements from later TLE
        config: Detection configuration

    Returns:
        Tuple of (is_discontinuity, confidence, details)
    """
    if config is None:
        config = EventDetectionConfig()

    if not tle_before or not tle_after:
        return False, 0.0, {"error": "Missing TLE data"}

    details = {}
    discontinuity_scores = []

    # Check semi-major axis change
    sma_before = tle_before.get("semi_major_axis_km", 0)
    sma_after = tle_after.get("semi_major_axis_km", 0)
    if sma_before > 0 and sma_after > 0:
        sma_change = abs(sma_after - sma_before)
        details["sma_change_km"] = sma_change
        if sma_change > config.sma_threshold_km:
            discontinuity_scores.append(min(1.0, sma_change / (config.sma_threshold_km * 5)))

    # Check eccentricity change
    ecc_before = tle_before.get("eccentricity", 0)
    ecc_after = tle_after.get("eccentricity", 0)
    ecc_change = abs(ecc_after - ecc_before)
    details["ecc_change"] = ecc_change
    if ecc_change > config.ecc_threshold:
        discontinuity_scores.append(min(1.0, ecc_change / (config.ecc_threshold * 5)))

    # Check inclination change
    inc_before = tle_before.get("inclination_deg", 0)
    inc_after = tle_after.get("inclination_deg", 0)
    inc_change = abs(inc_after - inc_before)
    details["inc_change_deg"] = inc_change
    if inc_change > config.inc_threshold_deg:
        discontinuity_scores.append(min(1.0, inc_change / (config.inc_threshold_deg * 5)))

    # Check RAAN change (accounting for natural drift)
    raan_before = tle_before.get("raan_deg", 0)
    raan_after = tle_after.get("raan_deg", 0)
    raan_change = abs(raan_after - raan_before)
    if raan_change > 180:
        raan_change = 360 - raan_change
    details["raan_change_deg"] = raan_change
    # RAAN naturally drifts, so use higher threshold
    if raan_change > config.raan_threshold_deg * 2:
        discontinuity_scores.append(min(1.0, raan_change / (config.raan_threshold_deg * 10)))

    # Check mean motion change
    mm_before = tle_before.get("mean_motion_rev_day", 0)
    mm_after = tle_after.get("mean_motion_rev_day", 0)
    if mm_before > 0:
        mm_change = abs(mm_after - mm_before) / mm_before  # Relative change
        details["mean_motion_rel_change"] = mm_change
        if mm_change > config.mean_motion_threshold:
            discontinuity_scores.append(min(1.0, mm_change / (config.mean_motion_threshold * 5)))

    # Compute overall confidence
    if discontinuity_scores:
        confidence = np.mean(discontinuity_scores)
    else:
        confidence = 0.0

    is_discontinuity = confidence >= config.maneuver_confidence_threshold
    details["confidence"] = confidence
    details["scores"] = discontinuity_scores

    return is_discontinuity, confidence, details


def detect_maneuvers_from_tle_history(
    tle_df: pd.DataFrame,
    satellite_id: int,
    config: EventDetectionConfig = None,
) -> List[OrbitalEvent]:
    """
    Detect maneuvers from TLE history using discontinuity analysis.

    Args:
        tle_df: DataFrame with TLE data (must have 'epoch', 'line1', 'line2', 'satNo')
        satellite_id: NORAD catalog number
        config: Detection configuration

    Returns:
        List of detected OrbitalEvent objects
    """
    if config is None:
        config = EventDetectionConfig()

    events = []

    # Filter to satellite and sort by epoch
    sat_tles = tle_df[tle_df["satNo"] == satellite_id].copy()
    if sat_tles.empty or len(sat_tles) < 2:
        return events

    if "epoch" in sat_tles.columns:
        sat_tles = sat_tles.sort_values("epoch")
    elif "epochTime" in sat_tles.columns:
        sat_tles = sat_tles.sort_values("epochTime")
    else:
        return events

    # Compare consecutive TLEs
    prev_tle = None
    prev_epoch = None
    prev_elements = None

    for _, row in sat_tles.iterrows():
        # Get epoch
        epoch = row.get("epoch") or row.get("epochTime")
        if isinstance(epoch, str):
            epoch = pd.to_datetime(epoch)

        # Parse TLE elements
        line2 = row.get("line2", row.get("tle2", ""))
        if not line2:
            continue

        elements = compute_orbital_elements_from_tle(line2)
        if not elements:
            continue

        # Compare with previous TLE
        if prev_elements is not None and prev_epoch is not None:
            # Check time gap
            time_gap = (epoch - prev_epoch).total_seconds() / 3600  # hours

            if config.min_gap_hours <= time_gap <= config.max_gap_days * 24:
                is_disc, confidence, details = detect_tle_discontinuity(
                    prev_elements, elements, config
                )

                if is_disc:
                    # Estimate delta-V from SMA change
                    sma_change = details.get("sma_change_km", 0)
                    # Very rough estimate: delta_v ~ sqrt(mu) * delta_a / (2 * a^1.5)
                    if sma_change > 0 and elements["semi_major_axis_km"] > 0:
                        mu = 398600.4418
                        a = elements["semi_major_axis_km"]
                        delta_v = np.sqrt(mu) * sma_change / (2 * a ** 1.5)  # km/s
                        delta_v_m_s = delta_v * 1000
                    else:
                        delta_v_m_s = None

                    # Determine maneuver direction
                    if details.get("sma_change_km", 0) > config.sma_threshold_km:
                        direction = "in-track"
                    elif details.get("inc_change_deg", 0) > config.inc_threshold_deg:
                        direction = "cross-track"
                    else:
                        direction = "unknown"

                    event = OrbitalEvent(
                        event_type=EventType.MANEUVER,
                        satellite_id=satellite_id,
                        event_time=prev_epoch + (epoch - prev_epoch) / 2,  # Midpoint
                        confidence=confidence,
                        delta_v_m_s=delta_v_m_s,
                        direction=direction,
                        source="tle_discontinuity",
                        metadata=details,
                    )
                    events.append(event)

        prev_elements = elements
        prev_epoch = epoch

    logger.info(f"Detected {len(events)} potential maneuvers for satellite {satellite_id}")
    return events


# =============================================================================
# LONG-DURATION LOW-THRUST MANEUVER DETECTION
# =============================================================================


def detect_long_duration_maneuvers(
    tle_df: pd.DataFrame,
    satellite_id: int,
    config: EventDetectionConfig = None,
) -> List[OrbitalEvent]:
    """
    Detect long-duration low-thrust (LL) maneuvers from TLE history.

    Long-duration maneuvers are characterized by:
    - Sustained orbital element changes over days/weeks
    - Gradual SMA drift that exceeds natural perturbations
    - Consistent directional changes (not random noise)

    This is different from impulsive maneuvers which cause sudden discontinuities.
    LL maneuvers show a steady trend in orbital elements over the maneuver duration.

    Args:
        tle_df: DataFrame with TLE data (must have 'epoch', 'line1', 'line2', 'satNo')
        satellite_id: NORAD catalog number
        config: Detection configuration with long_thrust parameters

    Returns:
        List of detected OrbitalEvent objects with event_type=LONG_THRUST
    """
    if config is None:
        config = EventDetectionConfig()

    events = []

    # Filter to satellite and sort by epoch
    sat_tles = tle_df[tle_df["satNo"] == satellite_id].copy()
    if sat_tles.empty or len(sat_tles) < 5:  # Need enough data points for trend
        return events

    # Sort by epoch
    epoch_col = "epoch" if "epoch" in sat_tles.columns else "epochTime"
    if epoch_col not in sat_tles.columns:
        return events
    sat_tles = sat_tles.sort_values(epoch_col)

    # Parse all TLEs to get orbital elements time series
    elements_history = []
    for _, row in sat_tles.iterrows():
        epoch = row.get("epoch") or row.get("epochTime")
        if isinstance(epoch, str):
            epoch = pd.to_datetime(epoch)

        line2 = row.get("line2", row.get("tle2", ""))
        if not line2:
            continue

        elements = compute_orbital_elements_from_tle(line2)
        if elements:
            elements["epoch"] = epoch
            elements_history.append(elements)

    if len(elements_history) < 5:
        return events

    # Convert to DataFrame for analysis
    elem_df = pd.DataFrame(elements_history)
    elem_df = elem_df.sort_values("epoch")

    # Compute time in days from first epoch
    first_epoch = elem_df["epoch"].iloc[0]
    elem_df["days_from_start"] = (elem_df["epoch"] - first_epoch).dt.total_seconds() / 86400

    # Analyze SMA trend using rolling window
    window_days = config.long_thrust_duration_days
    min_points = 3

    # Identify segments with sustained SMA drift
    maneuver_segments = []
    current_segment_start = None
    current_direction = None

    sma_values = elem_df["semi_major_axis_km"].values
    time_values = elem_df["days_from_start"].values
    epochs = elem_df["epoch"].values

    # Use sliding window to detect sustained drift
    for i in range(len(elem_df) - min_points + 1):
        window_end = i + min_points
        while window_end < len(elem_df):
            window_time_span = time_values[window_end - 1] - time_values[i]
            if window_time_span >= window_days:
                break
            window_end += 1

        if window_end > len(elem_df):
            break

        window_time_span = time_values[window_end - 1] - time_values[i]
        if window_time_span < window_days:
            continue

        # Calculate linear trend in this window
        window_times = time_values[i:window_end]
        window_smas = sma_values[i:window_end]

        # Linear regression: SMA = slope * time + intercept
        n = len(window_times)
        sum_t = np.sum(window_times)
        sum_sma = np.sum(window_smas)
        sum_t2 = np.sum(window_times ** 2)
        sum_t_sma = np.sum(window_times * window_smas)

        denominator = n * sum_t2 - sum_t ** 2
        if abs(denominator) < 1e-10:
            continue

        slope_km_per_day = (n * sum_t_sma - sum_t * sum_sma) / denominator

        # Convert slope to equivalent delta-V rate
        # Very rough: orbit raising/lowering delta-V proportional to SMA change
        # For circular orbit: delta_v ~ sqrt(mu/a) * delta_a / (2*a)
        # This gives delta_v_rate in km/s per day
        mu = 398600.4418  # km^3/s^2
        a = np.mean(window_smas)
        if a > 0:
            delta_v_rate_km_s_per_day = abs(
                np.sqrt(mu / a) * slope_km_per_day / (2 * a)
            )
            delta_v_rate_m_s_per_day = delta_v_rate_km_s_per_day * 1000
        else:
            delta_v_rate_m_s_per_day = 0

        # Check if rate exceeds threshold (indicating active thrust)
        # Natural perturbations cause ~0.01-0.1 m/s per day drift
        # Low-thrust typically < 0.5 m/s per day but sustained
        if delta_v_rate_m_s_per_day > 0.05 and delta_v_rate_m_s_per_day < config.long_thrust_rate_threshold:
            # This looks like a sustained low-thrust maneuver
            new_direction = "raising" if slope_km_per_day > 0 else "lowering"

            if current_segment_start is None:
                current_segment_start = i
                current_direction = new_direction
            elif new_direction != current_direction:
                # Direction changed - end current segment and start new one
                maneuver_segments.append({
                    "start_idx": current_segment_start,
                    "end_idx": i,
                    "direction": current_direction,
                    "slope_km_per_day": slope_km_per_day,
                    "delta_v_rate_m_s_per_day": delta_v_rate_m_s_per_day,
                })
                current_segment_start = i
                current_direction = new_direction
        else:
            # No longer maneuvering
            if current_segment_start is not None:
                maneuver_segments.append({
                    "start_idx": current_segment_start,
                    "end_idx": i,
                    "direction": current_direction,
                    "slope_km_per_day": slope_km_per_day,
                    "delta_v_rate_m_s_per_day": delta_v_rate_m_s_per_day,
                })
                current_segment_start = None
                current_direction = None

    # Close any open segment
    if current_segment_start is not None:
        maneuver_segments.append({
            "start_idx": current_segment_start,
            "end_idx": len(elem_df) - 1,
            "direction": current_direction,
            "slope_km_per_day": 0,  # Unknown for last segment
            "delta_v_rate_m_s_per_day": 0,
        })

    # Create OrbitalEvent objects for detected long-thrust maneuvers
    for segment in maneuver_segments:
        start_idx = segment["start_idx"]
        end_idx = segment["end_idx"]

        # Ensure sufficient duration
        duration_days = time_values[end_idx] - time_values[start_idx]
        if duration_days < config.long_thrust_duration_days:
            continue

        # Calculate total delta-V
        total_sma_change = abs(sma_values[end_idx] - sma_values[start_idx])
        a_avg = (sma_values[start_idx] + sma_values[end_idx]) / 2
        if a_avg > 0:
            total_delta_v_km_s = np.sqrt(mu / a_avg) * total_sma_change / (2 * a_avg)
            total_delta_v_m_s = total_delta_v_km_s * 1000
        else:
            total_delta_v_m_s = None

        # Compute confidence based on consistency of trend
        segment_smas = sma_values[start_idx:end_idx + 1]
        segment_times = time_values[start_idx:end_idx + 1]
        if len(segment_smas) > 2:
            # Correlation coefficient as confidence measure
            correlation = np.corrcoef(segment_times, segment_smas)[0, 1]
            confidence = abs(correlation) if not np.isnan(correlation) else 0.5
        else:
            confidence = 0.5

        event = OrbitalEvent(
            event_type=EventType.LONG_THRUST,
            satellite_id=satellite_id,
            event_time=pd.Timestamp(epochs[start_idx]).to_pydatetime(),
            end_time=pd.Timestamp(epochs[end_idx]).to_pydatetime(),
            confidence=confidence,
            delta_v_m_s=total_delta_v_m_s,
            direction=f"orbit_{segment['direction']}",
            source="tle_trend_analysis",
            metadata={
                "duration_days": duration_days,
                "sma_change_km": total_sma_change,
                "slope_km_per_day": segment.get("slope_km_per_day", 0),
                "delta_v_rate_m_s_per_day": segment.get("delta_v_rate_m_s_per_day", 0),
                "data_points": end_idx - start_idx + 1,
            },
        )
        events.append(event)

    logger.info(
        f"Detected {len(events)} long-duration low-thrust maneuvers for satellite {satellite_id}"
    )
    return events


def filter_satellites_by_event_code(
    tle_df: pd.DataFrame,
    satellite_ids: List[int],
    event_code: str,
    config: EventDetectionConfig = None,
) -> Tuple[List[int], List[OrbitalEvent]]:
    """
    Filter satellites based on legacy 16-character event code.

    Event codes from Louis's documentation:
        MB: Maneuver Between observations - impulsive maneuvers detected
        BU: Breakup event - fragmentation/debris generation
        LL: Long-duration Low-thrust - sustained low-thrust maneuvering
        NE: No Events - satellites with no detected events

    IMPORTANT: Per Louis's specification, event detection (MB/BU/LL) originally
    relies on ML Labelling Team output which may not be operational. This
    implementation uses TLE-based heuristics as a fallback when ML is unavailable.
    Only 'NE' (No Events) is fully reliable without the ML model.

    Args:
        tle_df: DataFrame with TLE data
        satellite_ids: List of satellites to check
        event_code: Two-character event code: MB, BU, LL, or NE
        config: Detection configuration

    Returns:
        Tuple of (matching_satellites, detected_events)

    Raises:
        ValueError: If event_code is not valid
    """
    valid_codes = ["MB", "BU", "LL", "NE"]
    if event_code not in valid_codes:
        raise ValueError(
            f"Invalid event code '{event_code}'. Valid codes are: {valid_codes}"
        )

    if config is None:
        config = EventDetectionConfig()

    # Check ML model availability and log appropriate warnings
    reliability_info = get_event_code_reliability(event_code, config.ml_model_available)

    if config.warn_on_ml_unavailable and not reliability_info["reliable"]:
        logger.warning(
            f"Event code '{event_code}' detection: {reliability_info.get('warning', 'Limited reliability')}"
        )
        if reliability_info.get("recommendation"):
            logger.info(f"Recommendation: {reliability_info['recommendation']}")

    logger.info(
        f"Event filtering (code={event_code}): using {reliability_info['fallback_method']} method"
    )

    all_events = []
    satellites_with_events = set()
    satellites_without_events = set()

    for sat_id in satellite_ids:
        sat_events = []

        if event_code in ["MB", "LL", "NE"]:
            # Detect impulsive maneuvers
            if event_code != "LL":
                maneuver_events = detect_maneuvers_from_tle_history(
                    tle_df, sat_id, config
                )
                if maneuver_events:
                    sat_events.extend(maneuver_events)

            # Detect long-thrust maneuvers
            if event_code in ["LL", "NE"]:
                long_thrust_events = detect_long_duration_maneuvers(
                    tle_df, sat_id, config
                )
                if long_thrust_events:
                    sat_events.extend(long_thrust_events)

        # Classify satellite
        has_maneuver = any(e.event_type == EventType.MANEUVER for e in sat_events)
        has_long_thrust = any(e.event_type == EventType.LONG_THRUST for e in sat_events)

        if event_code == "MB" and has_maneuver:
            satellites_with_events.add(sat_id)
            all_events.extend([e for e in sat_events if e.event_type == EventType.MANEUVER])
        elif event_code == "LL" and has_long_thrust:
            satellites_with_events.add(sat_id)
            all_events.extend([e for e in sat_events if e.event_type == EventType.LONG_THRUST])
        elif event_code == "NE" and not has_maneuver and not has_long_thrust:
            satellites_without_events.add(sat_id)
        elif event_code == "BU":
            # Breakup detection handled separately below
            pass

    # Return appropriate list based on event code
    if event_code == "NE":
        matching_satellites = list(satellites_without_events)
    elif event_code == "BU":
        # Breakup requires Space-Track/CelesTrak integration
        # Get date range from TLE data
        if not tle_df.empty:
            epoch_col = "epoch" if "epoch" in tle_df.columns else "epochTime"
            if epoch_col in tle_df.columns:
                tle_df[epoch_col] = pd.to_datetime(tle_df[epoch_col], errors="coerce")
                start_date = tle_df[epoch_col].min()
                end_date = tle_df[epoch_col].max()

                if pd.notna(start_date) and pd.notna(end_date):
                    # Fetch breakup events from Space-Track/CelesTrak
                    breakup_events = fetch_breakup_events_combined(
                        start_date.to_pydatetime() if hasattr(start_date, "to_pydatetime") else start_date,
                        end_date.to_pydatetime() if hasattr(end_date, "to_pydatetime") else end_date,
                    )

                    if breakup_events:
                        # Collect affected satellites
                        affected_ids = set()
                        for event in breakup_events:
                            affected_ids.add(event.parent_norad_id)
                            affected_ids.update(event.debris_norad_ids)

                        # Filter to only satellites in our input list
                        matching_satellites = [
                            sat_id for sat_id in satellite_ids
                            if sat_id in affected_ids
                        ]

                        # Add breakup events to all_events
                        for event in breakup_events:
                            orbital_event = OrbitalEvent(
                                event_type=EventType.BREAKUP,
                                satellite_id=event.parent_norad_id,
                                event_time=event.event_date,
                                confidence=0.9,
                                secondary_ids=event.debris_norad_ids,
                                fragment_count=event.debris_count,
                                source=event.source,
                                metadata={"event_type": event.event_type}
                            )
                            all_events.append(orbital_event)

                        logger.info(
                            f"BU filter: {len(breakup_events)} breakup events, "
                            f"{len(matching_satellites)} matching satellites"
                        )
                    else:
                        matching_satellites = []
                        logger.warning("No breakup events found in date range")
                else:
                    matching_satellites = []
                    logger.warning("Could not determine date range from TLE data")
            else:
                matching_satellites = []
                logger.warning("TLE data missing epoch column")
        else:
            matching_satellites = []
            logger.warning("Empty TLE data for breakup detection")
    else:
        matching_satellites = list(satellites_with_events)

    logger.info(
        f"Event filtering (code={event_code}): "
        f"{len(matching_satellites)} satellites match, "
        f"{len(all_events)} events detected"
    )

    return matching_satellites, all_events


# =============================================================================
# BREAKUP DETECTION
# =============================================================================


def detect_breakup_candidates(
    catalog_df: pd.DataFrame,
    time_window_days: float = 30.0,
    min_fragments: int = 5,
) -> List[OrbitalEvent]:
    """
    Detect potential breakup events from catalog data.

    Breakups are characterized by sudden appearance of multiple objects
    with similar orbital elements.

    Args:
        catalog_df: DataFrame with catalog data (satNo, epoch, orbital elements)
        time_window_days: Time window to look for related objects
        min_fragments: Minimum number of fragments to consider a breakup

    Returns:
        List of potential breakup events
    """
    events = []

    # Group objects by epoch of first detection
    if "first_epoch" not in catalog_df.columns and "epoch" in catalog_df.columns:
        # Use earliest epoch per object
        first_epochs = catalog_df.groupby("satNo")["epoch"].min().reset_index()
        first_epochs.columns = ["satNo", "first_epoch"]
        catalog_df = catalog_df.merge(first_epochs, on="satNo", how="left")

    if "first_epoch" not in catalog_df.columns:
        return events

    # Find clusters of objects appearing at similar times
    catalog_df["first_epoch"] = pd.to_datetime(catalog_df["first_epoch"])

    # Group by time bins
    time_bin = pd.Timedelta(days=time_window_days)
    catalog_df["time_bin"] = catalog_df["first_epoch"].dt.floor(time_bin)

    for time_bin_val, group in catalog_df.groupby("time_bin"):
        if len(group) >= min_fragments:
            # Check if objects have similar orbital elements (potential common origin)
            sma_std = group["semi_major_axis_km"].std() if "semi_major_axis_km" in group else float("inf")
            inc_std = group["inclination_deg"].std() if "inclination_deg" in group else float("inf")

            # Similar orbits suggest common origin
            if sma_std < 100 and inc_std < 5:  # Within 100 km SMA and 5 deg inclination
                primary_id = group["satNo"].iloc[0]  # Largest/first fragment
                fragment_ids = group["satNo"].tolist()

                event = OrbitalEvent(
                    event_type=EventType.BREAKUP,
                    satellite_id=primary_id,
                    event_time=time_bin_val,
                    confidence=min(1.0, len(group) / 20),  # More fragments = higher confidence
                    secondary_ids=fragment_ids[1:],
                    fragment_count=len(fragment_ids),
                    source="catalog_analysis",
                    metadata={
                        "sma_std_km": sma_std,
                        "inc_std_deg": inc_std,
                    },
                )
                events.append(event)

    logger.info(f"Detected {len(events)} potential breakup events")
    return events


# =============================================================================
# EVENT DATABASE INTEGRATION
# =============================================================================


def fetch_events_from_database(
    satellite_ids: List[int],
    start_time: datetime,
    end_time: datetime,
    event_types: List[EventType] = None,
) -> List[OrbitalEvent]:
    """
    Fetch known events from external event databases.

    Per Louis's specification, integrates with:
    - Space-Track maneuver data (boxscore endpoint)
    - 18 SDS conjunction data messages (CDMs via Space-Track)
    - Space-Track/CelesTrak breakup notifications

    Args:
        satellite_ids: List of satellite NORAD IDs to check
        start_time: Start of time window
        end_time: End of time window
        event_types: Types of events to fetch (None = all)

    Returns:
        List of OrbitalEvent objects sorted by event time
    """
    if event_types is None:
        event_types = [EventType.MANEUVER, EventType.BREAKUP, EventType.PROXIMITY]

    events = []
    satellite_set = set(satellite_ids) if satellite_ids else set()

    # 1. Fetch maneuvers from Space-Track boxscore
    if EventType.MANEUVER in event_types:
        try:
            maneuver_events = _fetch_spacetrack_maneuvers(
                satellite_ids, start_time, end_time
            )
            events.extend(maneuver_events)
            logger.info(f"Fetched {len(maneuver_events)} maneuver events from Space-Track")
        except Exception as e:
            logger.warning(f"Failed to fetch maneuvers from Space-Track: {e}")

    # 2. Fetch breakup events from Space-Track and CelesTrak
    if EventType.BREAKUP in event_types:
        try:
            breakup_events_raw = fetch_breakup_events_combined(
                start_time, end_time, use_cache=True
            )
            # Convert BreakupEvent to OrbitalEvent and filter by satellite_ids
            for bu in breakup_events_raw:
                # Include if parent or any debris is in our satellite list
                relevant = (
                    not satellite_set or
                    bu.parent_norad_id in satellite_set or
                    any(d in satellite_set for d in bu.debris_norad_ids)
                )
                if relevant:
                    event = OrbitalEvent(
                        event_type=EventType.BREAKUP,
                        satellite_id=bu.parent_norad_id,
                        event_time=bu.event_date,
                        confidence=0.9,  # High confidence from database
                        secondary_ids=bu.debris_norad_ids,
                        fragment_count=bu.debris_count,
                        source=bu.source,
                        metadata={
                            "parent_name": bu.parent_name,
                            "event_subtype": bu.event_type,
                        }
                    )
                    events.append(event)
            logger.info(f"Fetched {len([e for e in events if e.event_type == EventType.BREAKUP])} breakup events")
        except Exception as e:
            logger.warning(f"Failed to fetch breakup events: {e}")

    # 3. Fetch conjunction data messages (CDMs) from Space-Track
    if EventType.PROXIMITY in event_types:
        try:
            conjunction_events = _fetch_spacetrack_cdm(
                satellite_ids, start_time, end_time
            )
            events.extend(conjunction_events)
            logger.info(f"Fetched {len(conjunction_events)} conjunction events from Space-Track")
        except Exception as e:
            logger.warning(f"Failed to fetch CDMs from Space-Track: {e}")

    # Sort by event time
    events.sort(key=lambda x: x.event_time)

    logger.info(f"Total events fetched from databases: {len(events)}")
    return events


def _fetch_spacetrack_maneuvers(
    satellite_ids: List[int],
    start_time: datetime,
    end_time: datetime,
) -> List[OrbitalEvent]:
    """
    Fetch maneuver records from Space-Track boxscore endpoint.

    The boxscore endpoint tracks satellite position changes that may
    indicate maneuvers.

    Args:
        satellite_ids: NORAD IDs to query
        start_time: Start of time window
        end_time: End of time window

    Returns:
        List of OrbitalEvent objects for detected maneuvers
    """
    import os
    events = []

    try:
        from uct_benchmark.api.apiIntegration import spacetrackQuery

        spacetrack_token = os.environ.get("SPACETRACK_TOKEN")
        if not spacetrack_token:
            logger.warning("SPACETRACK_TOKEN not set, skipping maneuver fetch")
            return events

        # Query boxscore for each satellite
        for norad_id in satellite_ids:
            try:
                params = {
                    "NORAD_CAT_ID": norad_id,
                    "EPOCH": f">{start_time.strftime('%Y-%m-%d')}",
                    "EPOCH": f"<{end_time.strftime('%Y-%m-%d')}",
                    "orderby": "EPOCH asc",
                }

                result = spacetrackQuery(spacetrack_token, params, request="boxscore")

                if result is None or (isinstance(result, pd.DataFrame) and result.empty) or (isinstance(result, list) and len(result) == 0):
                    continue

                if isinstance(result, list):
                    result = pd.DataFrame(result)

                # Look for significant position changes (potential maneuvers)
                # Boxscore contains RMS of position changes
                for _, row in result.iterrows():
                    rms_value = row.get("RMS", 0)
                    if rms_value and float(rms_value) > 10.0:  # Threshold for significant change
                        epoch_str = row.get("EPOCH")
                        if epoch_str:
                            try:
                                event_time = pd.to_datetime(epoch_str)
                                if hasattr(event_time, "to_pydatetime"):
                                    event_time = event_time.to_pydatetime()

                                event = OrbitalEvent(
                                    event_type=EventType.MANEUVER,
                                    satellite_id=norad_id,
                                    event_time=event_time,
                                    confidence=min(0.5 + float(rms_value) / 100.0, 0.95),
                                    source="SPACETRACK_BOXSCORE",
                                    metadata={
                                        "rms": float(rms_value),
                                        "detection_method": "boxscore_rms",
                                    }
                                )
                                events.append(event)
                            except Exception:
                                continue

            except Exception as e:
                logger.debug(f"Error querying boxscore for {norad_id}: {e}")
                continue

    except ImportError as e:
        logger.warning(f"Could not import apiIntegration: {e}")

    return events


def _fetch_spacetrack_cdm(
    satellite_ids: List[int],
    start_time: datetime,
    end_time: datetime,
) -> List[OrbitalEvent]:
    """
    Fetch Conjunction Data Messages (CDMs) from Space-Track.

    CDMs are provided by 18 SDS (18th Space Defense Squadron) and contain
    close approach predictions between tracked objects.

    Args:
        satellite_ids: NORAD IDs to query
        start_time: Start of time window
        end_time: End of time window

    Returns:
        List of OrbitalEvent objects for conjunctions
    """
    import os
    events = []

    try:
        from uct_benchmark.api.apiIntegration import spacetrackQuery

        spacetrack_token = os.environ.get("SPACETRACK_TOKEN")
        if not spacetrack_token:
            logger.warning("SPACETRACK_TOKEN not set, skipping CDM fetch")
            return events

        # Query CDM endpoint for each satellite
        for norad_id in satellite_ids:
            try:
                params = {
                    "SAT1_NORAD_CAT_ID": norad_id,
                    "TCA": f">{start_time.strftime('%Y-%m-%d')}",
                    "TCA": f"<{end_time.strftime('%Y-%m-%d')}",
                    "orderby": "TCA asc",
                    "limit": 100,  # Limit per satellite
                }

                result = spacetrackQuery(spacetrack_token, params, request="cdm_public")

                if result is None or (isinstance(result, pd.DataFrame) and result.empty) or (isinstance(result, list) and len(result) == 0):
                    continue

                if isinstance(result, list):
                    result = pd.DataFrame(result)

                for _, row in result.iterrows():
                    tca_str = row.get("TCA")
                    if tca_str:
                        try:
                            event_time = pd.to_datetime(tca_str)
                            if hasattr(event_time, "to_pydatetime"):
                                event_time = event_time.to_pydatetime()

                            miss_distance = row.get("MISS_DISTANCE")
                            collision_prob = row.get("COLLISION_PROBABILITY")
                            secondary_id = row.get("SAT2_NORAD_CAT_ID")

                            # Calculate confidence based on collision probability
                            if collision_prob:
                                try:
                                    confidence = min(float(collision_prob) * 1000, 0.99)
                                except (ValueError, TypeError):
                                    confidence = 0.5
                            else:
                                confidence = 0.5

                            event = OrbitalEvent(
                                event_type=EventType.PROXIMITY,
                                satellite_id=norad_id,
                                event_time=event_time,
                                confidence=confidence,
                                secondary_ids=[int(secondary_id)] if secondary_id else [],
                                source="SPACETRACK_CDM",
                                metadata={
                                    "miss_distance_m": float(miss_distance) if miss_distance else None,
                                    "collision_probability": float(collision_prob) if collision_prob else None,
                                    "cdm_id": row.get("CDM_ID"),
                                }
                            )
                            events.append(event)
                        except Exception:
                            continue

            except Exception as e:
                logger.debug(f"Error querying CDM for {norad_id}: {e}")
                continue

    except ImportError as e:
        logger.warning(f"Could not import apiIntegration: {e}")

    return events


# =============================================================================
# EVENT FILTERING FOR DATASETS
# =============================================================================


def filter_observations_by_events(
    obs_df: pd.DataFrame,
    events: List[OrbitalEvent],
    mode: str = "include",
    time_buffer_hours: float = 24.0,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Filter observations based on event proximity.

    Args:
        obs_df: DataFrame of observations
        events: List of detected/known events
        mode: "include" to keep only obs near events, "exclude" to remove them
        time_buffer_hours: Time window around events

    Returns:
        Tuple of (filtered_df, metadata)
    """
    if obs_df.empty or not events:
        return obs_df, {"events_used": 0, "mode": mode}

    buffer = timedelta(hours=time_buffer_hours)
    event_masks = []

    for event in events:
        sat_mask = obs_df["satNo"] == event.satellite_id
        time_mask = (
            (obs_df["obTime"] >= event.event_time - buffer) &
            (obs_df["obTime"] <= event.event_time + buffer)
        )
        event_masks.append(sat_mask & time_mask)

    if event_masks:
        combined_mask = event_masks[0]
        for mask in event_masks[1:]:
            combined_mask = combined_mask | mask
    else:
        combined_mask = pd.Series([False] * len(obs_df))

    if mode == "include":
        filtered_df = obs_df[combined_mask].copy()
    else:  # exclude
        filtered_df = obs_df[~combined_mask].copy()

    metadata = {
        "events_used": len(events),
        "mode": mode,
        "time_buffer_hours": time_buffer_hours,
        "observations_before": len(obs_df),
        "observations_after": len(filtered_df),
    }

    return filtered_df, metadata


def get_satellites_with_events(
    tle_df: pd.DataFrame,
    satellite_ids: List[int],
    event_types: List[EventType] = None,
    config: EventDetectionConfig = None,
) -> Tuple[List[int], List[OrbitalEvent]]:
    """
    Find satellites that have events within the TLE history.

    Args:
        tle_df: DataFrame with TLE data
        satellite_ids: List of satellites to check
        event_types: Types of events to look for
        config: Detection configuration

    Returns:
        Tuple of (satellites_with_events, all_events)
    """
    if event_types is None:
        event_types = [EventType.MANEUVER]

    all_events = []
    satellites_with_events = set()

    for sat_id in satellite_ids:
        if EventType.MANEUVER in event_types:
            maneuver_events = detect_maneuvers_from_tle_history(
                tle_df, sat_id, config
            )
            if maneuver_events:
                satellites_with_events.add(sat_id)
                all_events.extend(maneuver_events)

    logger.info(
        f"Found {len(satellites_with_events)} satellites with events "
        f"({len(all_events)} total events)"
    )

    return list(satellites_with_events), all_events


# =============================================================================
# SPACE-TRACK / CELESTRAK BREAKUP EVENT INTEGRATION
# =============================================================================


@dataclass
class BreakupEvent:
    """
    Represents a breakup/fragmentation event from Space-Track or CelesTrak.

    Per Louis's documentation, breakup (BU) event detection requires
    external database integration to identify actual fragmentation events.
    """
    parent_norad_id: int
    parent_name: str
    event_date: datetime
    debris_count: int
    debris_norad_ids: List[int]
    event_type: str  # 'FRAGMENTATION', 'COLLISION', 'ANOMALY'
    source: str      # 'SPACETRACK' or 'CELESTRAK'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "parent_norad_id": self.parent_norad_id,
            "parent_name": self.parent_name,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "debris_count": self.debris_count,
            "debris_norad_ids": self.debris_norad_ids,
            "event_type": self.event_type,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BreakupEvent":
        """Create from dictionary."""
        event_date = data.get("event_date")
        if event_date and isinstance(event_date, str):
            event_date = datetime.fromisoformat(event_date)

        return cls(
            parent_norad_id=data.get("parent_norad_id", 0),
            parent_name=data.get("parent_name", ""),
            event_date=event_date,
            debris_count=data.get("debris_count", 0),
            debris_norad_ids=data.get("debris_norad_ids", []),
            event_type=data.get("event_type", "UNKNOWN"),
            source=data.get("source", "UNKNOWN"),
        )


def fetch_breakup_events_from_spacetrack(
    start_date: datetime,
    end_date: datetime,
    regime: Optional[str] = None,
    spacetrack_token: str = None,
) -> List[BreakupEvent]:
    """
    Query Space-Track DECAY and SATCAT tables for fragmentation events.

    Uses the existing spacetrackQuery() function from apiIntegration.py.

    Args:
        start_date: Start of date range to search
        end_date: End of date range to search
        regime: Optional orbital regime filter (LEO, MEO, GEO)
        spacetrack_token: Space-Track API token (uses env var if not provided)

    Returns:
        List of BreakupEvent objects from Space-Track
    """
    events = []

    try:
        from uct_benchmark.api.apiIntegration import spacetrackQuery
        import os

        # Get token from environment if not provided
        if spacetrack_token is None:
            spacetrack_token = os.environ.get("SPACETRACK_TOKEN")

        if not spacetrack_token:
            logger.warning(
                "No Space-Track token available. "
                "Set SPACETRACK_TOKEN environment variable."
            )
            return events

        # Query SATCAT for debris objects created in the date range
        params = {
            "OBJECT_TYPE": "DEBRIS",
            "LAUNCH": f">{start_date.strftime('%Y-%m-%d')}",
            "LAUNCH": f"<{end_date.strftime('%Y-%m-%d')}",
            "orderby": "LAUNCH asc",
            "limit": 5000,
        }

        # Execute query
        result = spacetrackQuery(spacetrack_token, params, request="satcat")

        if result is None or (isinstance(result, pd.DataFrame) and result.empty):
            logger.info("No debris objects found in Space-Track SATCAT for date range")
            return events

        # Convert to DataFrame if needed
        if isinstance(result, list):
            result = pd.DataFrame(result)

        if result.empty:
            return events

        # Group debris by INTLDES prefix to identify parent objects
        # INTLDES format: YYYY-NNNAA where YYYY is year, NNN is launch number, AA is piece
        if "INTLDES" in result.columns:
            result["parent_intldes"] = result["INTLDES"].str[:8]  # YYYY-NNN prefix

            # Group fragments by parent
            for parent_id, fragments in result.groupby("parent_intldes"):
                if len(fragments) >= 5:  # Minimum fragments for a breakup
                    # Get parent object info
                    parent_row = fragments.iloc[0]

                    # Extract event date from launch date of first fragment
                    event_date = None
                    if "LAUNCH" in fragments.columns:
                        try:
                            event_date = pd.to_datetime(fragments["LAUNCH"].min())
                        except Exception:
                            pass

                    if event_date is None:
                        continue

                    debris_ids = fragments["NORAD_CAT_ID"].tolist() if "NORAD_CAT_ID" in fragments else []

                    event = BreakupEvent(
                        parent_norad_id=int(parent_row.get("NORAD_CAT_ID", 0)),
                        parent_name=str(parent_row.get("SATNAME", parent_id)),
                        event_date=event_date.to_pydatetime() if hasattr(event_date, "to_pydatetime") else event_date,
                        debris_count=len(fragments),
                        debris_norad_ids=[int(x) for x in debris_ids if pd.notna(x)],
                        event_type="FRAGMENTATION",
                        source="SPACETRACK",
                    )
                    events.append(event)

        logger.info(f"Found {len(events)} breakup events from Space-Track")

    except ImportError as e:
        logger.warning(f"Could not import apiIntegration: {e}")
    except Exception as e:
        logger.error(f"Error fetching breakup events from Space-Track: {e}")

    return events


def fetch_breakup_events_from_celestrak(
    start_date: datetime,
    end_date: datetime,
) -> List[BreakupEvent]:
    """
    Query CelesTrak SATCAT for fragmentation events.

    Uses the existing celestrakQuery() function from apiIntegration.py.

    Args:
        start_date: Start of date range to search
        end_date: End of date range to search

    Returns:
        List of BreakupEvent objects from CelesTrak
    """
    events = []

    try:
        from uct_benchmark.api.apiIntegration import celestrakQuery

        # Query CelesTrak for debris objects
        params = {
            "OBJECT_TYPE": "DEBRIS",
        }

        result = celestrakQuery(params, table="satcat")

        if result is None or (isinstance(result, pd.DataFrame) and result.empty):
            logger.info("No debris data available from CelesTrak")
            return events

        if isinstance(result, list):
            result = pd.DataFrame(result)

        if result.empty:
            return events

        # Filter by date range
        if "LAUNCH" in result.columns:
            result["LAUNCH"] = pd.to_datetime(result["LAUNCH"], errors="coerce")
            result = result[
                (result["LAUNCH"] >= start_date) &
                (result["LAUNCH"] <= end_date)
            ]

        # Group by international designator prefix
        if "INTLDES" in result.columns and not result.empty:
            result["parent_intldes"] = result["INTLDES"].str[:8]

            for parent_id, fragments in result.groupby("parent_intldes"):
                if len(fragments) >= 5:
                    parent_row = fragments.iloc[0]
                    event_date = fragments["LAUNCH"].min() if "LAUNCH" in fragments else None

                    if event_date is None or pd.isna(event_date):
                        continue

                    debris_ids = fragments["NORAD_CAT_ID"].tolist() if "NORAD_CAT_ID" in fragments else []

                    event = BreakupEvent(
                        parent_norad_id=int(parent_row.get("NORAD_CAT_ID", 0)),
                        parent_name=str(parent_row.get("SATNAME", parent_id)),
                        event_date=event_date.to_pydatetime() if hasattr(event_date, "to_pydatetime") else event_date,
                        debris_count=len(fragments),
                        debris_norad_ids=[int(x) for x in debris_ids if pd.notna(x)],
                        event_type="FRAGMENTATION",
                        source="CELESTRAK",
                    )
                    events.append(event)

        logger.info(f"Found {len(events)} breakup events from CelesTrak")

    except ImportError as e:
        logger.warning(f"Could not import apiIntegration: {e}")
    except Exception as e:
        logger.error(f"Error fetching breakup events from CelesTrak: {e}")

    return events


def fetch_breakup_events_combined(
    start_date: datetime,
    end_date: datetime,
    regime: Optional[str] = None,
    use_cache: bool = True,
    cache_hours: int = 24,
) -> List[BreakupEvent]:
    """
    Fetch breakup events from both Space-Track and CelesTrak.

    Combines results and removes duplicates based on parent NORAD ID.

    Args:
        start_date: Start of date range
        end_date: End of date range
        regime: Optional orbital regime filter
        use_cache: Whether to use cached results
        cache_hours: Cache expiration time in hours

    Returns:
        Combined list of BreakupEvent objects
    """
    import json
    import os
    from pathlib import Path

    # Check cache
    cache_dir = Path(__file__).parent.parent / "cache"
    cache_file = cache_dir / "breakup_events.json"

    if use_cache and cache_file.exists():
        try:
            cache_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - cache_mtime < timedelta(hours=cache_hours):
                with open(cache_file, "r") as f:
                    cached_data = json.load(f)
                    # Filter to requested date range
                    events = []
                    for event_data in cached_data.get("events", []):
                        event = BreakupEvent.from_dict(event_data)
                        if start_date <= event.event_date <= end_date:
                            events.append(event)
                    logger.info(f"Loaded {len(events)} breakup events from cache")
                    return events
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")

    # Fetch from both sources
    events = []

    # Try Space-Track first
    spacetrack_events = fetch_breakup_events_from_spacetrack(start_date, end_date, regime)
    events.extend(spacetrack_events)

    # Then CelesTrak
    celestrak_events = fetch_breakup_events_from_celestrak(start_date, end_date)
    events.extend(celestrak_events)

    # Remove duplicates (prefer Space-Track as primary source)
    seen_parents = set()
    unique_events = []
    for event in events:
        if event.parent_norad_id not in seen_parents:
            seen_parents.add(event.parent_norad_id)
            unique_events.append(event)

    # Save to cache
    if use_cache:
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump({
                    "cached_at": datetime.now().isoformat(),
                    "events": [e.to_dict() for e in unique_events],
                }, f, indent=2)
            logger.debug(f"Saved {len(unique_events)} breakup events to cache")
        except Exception as e:
            logger.warning(f"Could not save cache: {e}")

    logger.info(f"Total breakup events: {len(unique_events)} (Space-Track: {len(spacetrack_events)}, CelesTrak: {len(celestrak_events)})")
    return unique_events


def filter_by_breakup_event(
    obs_df: pd.DataFrame,
    start_date: datetime,
    end_date: datetime,
    regime: Optional[str] = None,
) -> Tuple[pd.DataFrame, List[BreakupEvent], Dict[str, Any]]:
    """
    Filter observations to only include satellites involved in breakup events.

    This implements the BU (Breakup) event code from Louis's 16-character format.

    Args:
        obs_df: DataFrame of observations with 'satNo' column
        start_date: Start of date range
        end_date: End of date range
        regime: Optional orbital regime filter

    Returns:
        Tuple of (filtered_obs, breakup_events, metadata)
    """
    metadata = {
        "event_code": "BU",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "regime": regime,
    }

    if obs_df.empty:
        return obs_df, [], metadata

    # Fetch breakup events
    breakup_events = fetch_breakup_events_combined(start_date, end_date, regime)

    if not breakup_events:
        logger.warning(
            "No breakup events found in date range. "
            "Returning empty result."
        )
        metadata["status"] = "no_breakup_events"
        metadata["satellites_matched"] = 0
        return obs_df.iloc[:0].copy(), [], metadata

    # Collect all affected NORAD IDs (parents + debris)
    affected_norad_ids = set()
    for event in breakup_events:
        affected_norad_ids.add(event.parent_norad_id)
        affected_norad_ids.update(event.debris_norad_ids)

    # Filter observations
    filtered_obs = obs_df[obs_df["satNo"].isin(affected_norad_ids)].copy()

    metadata["status"] = "success"
    metadata["breakup_events_count"] = len(breakup_events)
    metadata["affected_norad_ids"] = list(affected_norad_ids)
    metadata["satellites_matched"] = len(filtered_obs["satNo"].unique())
    metadata["observations_filtered"] = len(filtered_obs)

    logger.info(
        f"BU filter: {len(breakup_events)} breakup events, "
        f"{len(affected_norad_ids)} affected satellites, "
        f"{len(filtered_obs)} observations"
    )

    return filtered_obs, breakup_events, metadata
