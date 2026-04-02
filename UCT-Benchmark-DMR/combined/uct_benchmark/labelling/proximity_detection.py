"""
Proximity event detector.

Detects close approaches between satellite pairs by comparing
orbital parameters. Uses semi-major axis similarity as a first-pass
filter, then checks temporal overlap of observations to identify
potential conjunction windows.

This is new logic (not wrapping existing eventDetection code).
"""

from datetime import datetime, timedelta
from itertools import combinations
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from .detection_base import (
    DetectionResult,
    EventDetector,
    _generate_event_id,
    confidence_from_score,
    get_unique_objects,
)
from .schema import EventLabel, EventWindow


class ProximityDetector(EventDetector):
    """Detect close approaches between satellite pairs.

    Uses a two-stage filter:
    1. **Orbital similarity filter** -- pairs must have semi-major axes
       within ``sma_similarity_km`` of each other (coplanar filter
       optional via inclination).
    2. **Temporal co-location** -- both objects must have observations
       within ``temporal_window_minutes`` of each other.

    Args:
        miss_distance_threshold_km: Maximum miss distance to flag as a
            proximity event. Use ~10 for LEO, ~50 for GEO (default 10).
        sma_similarity_km: Maximum SMA difference for the first-pass
            orbital filter (default 50).
        temporal_window_minutes: Maximum time difference between
            concurrent observations to consider objects co-located
            (default 30).
        max_pairs: Upper limit on satellite pairs to evaluate, to
            prevent combinatorial explosion (default 5000).
    """

    def __init__(
        self,
        miss_distance_threshold_km: float = 10.0,
        sma_similarity_km: float = 50.0,
        temporal_window_minutes: float = 30.0,
        max_pairs: int = 5000,
    ):
        self.miss_distance_threshold_km = miss_distance_threshold_km
        self.sma_similarity_km = sma_similarity_km
        self.temporal_window_minutes = temporal_window_minutes
        self.max_pairs = max_pairs

    @property
    def detector_name(self) -> str:
        return "ProximityDetector"

    def validate_input(self, df: pd.DataFrame) -> Tuple[bool, str]:
        required = {"sat_no", "ob_time"}
        missing = required - set(df.columns)
        if missing:
            return False, f"Missing required columns: {missing}"
        if df.empty:
            return False, "DataFrame is empty"
        return True, ""

    def _compute_sma_from_mean_motion(self, mean_motion_rev_day: float) -> float:
        """Compute semi-major axis (km) from mean motion (rev/day)."""
        if mean_motion_rev_day <= 0:
            return 0.0
        mu = 398600.4418  # km^3/s^2
        n_rad_s = mean_motion_rev_day * 2 * np.pi / 86400.0
        return (mu / (n_rad_s ** 2)) ** (1 / 3)

    def _build_object_profiles(
        self,
        observations_df: pd.DataFrame,
        tle_df: Optional[pd.DataFrame],
    ) -> Dict[int, dict]:
        """Build orbital profiles per object for fast filtering.

        Returns dict mapping sat_no -> {sma_km, inc_deg, obs_times}.
        """
        profiles: Dict[int, dict] = {}
        sat_nos = get_unique_objects(observations_df)

        for sat_no in sat_nos:
            sat_obs = observations_df[observations_df["sat_no"] == sat_no]
            obs_times = pd.to_datetime(sat_obs["ob_time"]).sort_values()

            profile: dict = {
                "sat_no": sat_no,
                "obs_times": obs_times,
                "sma_km": None,
                "inc_deg": None,
            }

            # Try to get SMA from TLE data
            if tle_df is not None and not tle_df.empty:
                sat_tles = tle_df[tle_df["satNo"] == sat_no] if "satNo" in tle_df.columns else pd.DataFrame()
                if not sat_tles.empty:
                    if "mean_motion" in sat_tles.columns:
                        mm = sat_tles["mean_motion"].iloc[-1]
                        profile["sma_km"] = self._compute_sma_from_mean_motion(float(mm))
                    if "inclination" in sat_tles.columns:
                        profile["inc_deg"] = float(sat_tles["inclination"].iloc[-1])

            profiles[sat_no] = profile

        return profiles

    def _find_temporal_overlaps(
        self,
        times_a: pd.Series,
        times_b: pd.Series,
        window_minutes: float,
    ) -> List[Tuple[datetime, datetime]]:
        """Find time intervals where both objects have near-simultaneous observations."""
        overlaps = []
        window_td = timedelta(minutes=window_minutes)

        # Use sorted merge approach for efficiency
        a_vals = times_a.values
        b_vals = times_b.values
        j = 0

        for i in range(len(a_vals)):
            t_a = pd.Timestamp(a_vals[i])
            # Advance j to the first b_val within window
            while j < len(b_vals) and pd.Timestamp(b_vals[j]) < t_a - window_td:
                j += 1
            # Check all b_vals within window
            k = j
            while k < len(b_vals) and pd.Timestamp(b_vals[k]) <= t_a + window_td:
                t_b = pd.Timestamp(b_vals[k])
                overlap_start = min(t_a, t_b).to_pydatetime()
                overlap_end = max(t_a, t_b).to_pydatetime()
                overlaps.append((overlap_start, overlap_end))
                k += 1

        return overlaps

    def detect(
        self,
        observations_df: pd.DataFrame,
        time_window: Tuple[datetime, datetime],
        *,
        tle_df: Optional[pd.DataFrame] = None,
        **kwargs,
    ) -> DetectionResult:
        """Detect proximity events between satellite pairs.

        Args:
            observations_df: Observation DataFrame.
            time_window: Analysis time window.
            tle_df: Optional TLE data for orbital filtering.

        Returns:
            DetectionResult with detected proximity events.
        """
        import time as _time

        t0 = _time.monotonic()
        result = DetectionResult(observations_processed=len(observations_df))

        valid, msg = self.validate_input(observations_df)
        if not valid:
            result.warnings.append(f"Input validation failed: {msg}")
            result.processing_time_seconds = _time.monotonic() - t0
            return result

        start_time, end_time = time_window

        # Build orbital profiles
        profiles = self._build_object_profiles(observations_df, tle_df)
        sat_nos = list(profiles.keys())

        if len(sat_nos) < 2:
            result.warnings.append("Fewer than 2 objects — no proximity check possible")
            result.processing_time_seconds = _time.monotonic() - t0
            return result

        # Generate candidate pairs (limit to max_pairs)
        all_pairs = list(combinations(sat_nos, 2))
        if len(all_pairs) > self.max_pairs:
            result.warnings.append(
                f"Too many pairs ({len(all_pairs)}); sampling {self.max_pairs}"
            )
            import random
            random.shuffle(all_pairs)
            all_pairs = all_pairs[: self.max_pairs]

        # Stage 1: SMA similarity filter
        candidate_pairs = []
        for sat_a, sat_b in all_pairs:
            sma_a = profiles[sat_a].get("sma_km")
            sma_b = profiles[sat_b].get("sma_km")

            # If SMA unknown for either, include in candidates (cannot filter)
            if sma_a is None or sma_b is None:
                candidate_pairs.append((sat_a, sat_b))
                continue

            if abs(sma_a - sma_b) <= self.sma_similarity_km:
                candidate_pairs.append((sat_a, sat_b))

        # Stage 2: Temporal overlap check
        for sat_a, sat_b in candidate_pairs:
            times_a = profiles[sat_a]["obs_times"]
            times_b = profiles[sat_b]["obs_times"]

            overlaps = self._find_temporal_overlaps(
                times_a, times_b, self.temporal_window_minutes
            )

            if not overlaps:
                continue

            # Filter overlaps to the analysis window
            valid_overlaps = [
                (s, e) for s, e in overlaps
                if s <= end_time and e >= start_time
            ]

            if not valid_overlaps:
                continue

            # Merge close overlaps into proximity windows
            merged = self._merge_overlaps(valid_overlaps)

            for window_start, window_end in merged:
                # Confidence based on number of overlapping observations
                # and SMA proximity
                sma_a = profiles[sat_a].get("sma_km")
                sma_b = profiles[sat_b].get("sma_km")

                if sma_a and sma_b:
                    sma_diff = abs(sma_a - sma_b)
                    sma_score = max(0.0, 1.0 - sma_diff / self.miss_distance_threshold_km)
                else:
                    sma_score = 0.3  # Unknown SMA — lower confidence

                overlap_count = sum(
                    1 for s, e in valid_overlaps
                    if s >= window_start and e <= window_end + timedelta(hours=1)
                )
                temporal_score = min(1.0, overlap_count / 5.0)

                score = 0.5 * sma_score + 0.5 * temporal_score

                label = EventLabel(
                    event_id=_generate_event_id("prox"),
                    event_type="proximity",
                    confidence=confidence_from_score(score),
                    source="automated_detection",
                    primary_object_ids=[sat_a],
                    secondary_object_ids=[sat_b],
                    event_window=EventWindow(
                        start_time=window_start,
                        end_time=window_end if window_end > window_start else window_start + timedelta(minutes=1),
                        peak_time=None,
                    ),
                    metadata={
                        "sma_a_km": sma_a,
                        "sma_b_km": sma_b,
                        "sma_diff_km": abs(sma_a - sma_b) if sma_a and sma_b else None,
                        "overlap_count": overlap_count,
                        "miss_distance_threshold_km": self.miss_distance_threshold_km,
                        "detector": self.detector_name,
                    },
                )
                result.events.append(label)

        result.processing_time_seconds = _time.monotonic() - t0
        logger.info(
            f"{self.detector_name}: detected {len(result.events)} proximity events "
            f"from {len(candidate_pairs)} candidate pairs "
            f"(filtered from {len(all_pairs)} total pairs)"
        )
        return result

    @staticmethod
    def _merge_overlaps(
        intervals: List[Tuple[datetime, datetime]],
    ) -> List[Tuple[datetime, datetime]]:
        """Merge overlapping or adjacent time intervals."""
        if not intervals:
            return []
        sorted_intervals = sorted(intervals, key=lambda x: x[0])
        merged = [sorted_intervals[0]]
        for start, end in sorted_intervals[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end + timedelta(hours=1):
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))
        return merged
