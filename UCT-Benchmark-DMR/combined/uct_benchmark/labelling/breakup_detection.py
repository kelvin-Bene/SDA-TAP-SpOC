"""
Breakup event detector.

Wraps the existing fetch_breakup_events_combined() and related
functions from eventDetection.py, converting BreakupEvent results
into EventLabel format.

Includes a fallback: when no external API data is available, detects
sudden increases in object count from observation data alone.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

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


class BreakupDetector(EventDetector):
    """Detect breakup / fragmentation events.

    Primary detection delegates to the Space-Track and CelesTrak
    integration in ``uct_benchmark.data.eventDetection``. When external
    API access is unavailable, a fallback heuristic looks for sudden
    increases in the number of tracked objects from the observation data.

    Args:
        min_fragment_count: Minimum number of new objects to consider
            a breakup event (default 5).
        surge_window_hours: Time window in hours over which to measure
            object-count surges for the fallback heuristic (default 48).
        use_external_apis: Whether to attempt Space-Track / CelesTrak
            queries (default True). Set to False for offline mode.
    """

    def __init__(
        self,
        min_fragment_count: int = 5,
        surge_window_hours: float = 48.0,
        use_external_apis: bool = True,
    ):
        self.min_fragment_count = min_fragment_count
        self.surge_window_hours = surge_window_hours
        self.use_external_apis = use_external_apis

    @property
    def detector_name(self) -> str:
        return "BreakupDetector"

    def validate_input(self, df: pd.DataFrame) -> Tuple[bool, str]:
        required = {"sat_no", "ob_time"}
        missing = required - set(df.columns)
        if missing:
            return False, f"Missing required columns: {missing}"
        if df.empty:
            return False, "DataFrame is empty"
        return True, ""

    # ------------------------------------------------------------------
    # External API wrappers
    # ------------------------------------------------------------------

    def _detect_from_external(
        self,
        time_window: Tuple[datetime, datetime],
        satellite_ids: Optional[List[int]] = None,
    ) -> Tuple[List[EventLabel], List[str]]:
        """Fetch breakup events from Space-Track and CelesTrak.

        Returns (events, warnings).
        """
        events: List[EventLabel] = []
        warnings: List[str] = []
        start_time, end_time = time_window

        try:
            from uct_benchmark.data.eventDetection import fetch_breakup_events_combined
        except ImportError as exc:
            warnings.append(f"Could not import eventDetection: {exc}")
            return events, warnings

        try:
            breakup_events = fetch_breakup_events_combined(
                start_date=start_time,
                end_date=end_time,
                use_cache=True,
            )
        except Exception as exc:
            warnings.append(f"External breakup query failed: {exc}")
            return events, warnings

        if not breakup_events:
            return events, warnings

        for be in breakup_events:
            # If we have a satellite filter, check relevance
            if satellite_ids is not None:
                relevant_ids = {be.parent_norad_id} | set(be.debris_norad_ids)
                if not relevant_ids.intersection(satellite_ids):
                    continue

            # Build EventLabel
            primary_ids = [be.parent_norad_id]
            secondary_ids = [
                int(d) for d in be.debris_norad_ids
                if d != be.parent_norad_id
            ]

            # Higher fragment count = higher confidence
            if be.debris_count >= 50:
                score = 0.95
            elif be.debris_count >= 20:
                score = 0.85
            elif be.debris_count >= 10:
                score = 0.7
            else:
                score = 0.55

            event_start = be.event_date
            event_end = be.event_date + timedelta(hours=24)

            label = EventLabel(
                event_id=_generate_event_id("brkp"),
                event_type="breakup",
                confidence=confidence_from_score(score),
                source="external_database",
                primary_object_ids=primary_ids,
                secondary_object_ids=secondary_ids[:50],  # Cap at 50 fragment IDs
                event_window=EventWindow(
                    start_time=event_start,
                    end_time=event_end,
                    peak_time=event_start,
                ),
                metadata={
                    "parent_name": be.parent_name,
                    "debris_count": be.debris_count,
                    "external_event_type": be.event_type,
                    "external_source": be.source,
                    "detector": self.detector_name,
                },
            )
            events.append(label)

        return events, warnings

    # ------------------------------------------------------------------
    # Observation-based fallback
    # ------------------------------------------------------------------

    def _detect_from_object_surge(
        self,
        observations_df: pd.DataFrame,
        time_window: Tuple[datetime, datetime],
    ) -> List[EventLabel]:
        """Fallback: detect sudden increases in tracked object count.

        Bins observations into time buckets and looks for windows where
        the number of unique objects spikes significantly above the
        baseline.
        """
        events: List[EventLabel] = []
        start_time, end_time = time_window

        df = observations_df.copy()
        df["ob_time"] = pd.to_datetime(df["ob_time"])
        df = df[(df["ob_time"] >= start_time) & (df["ob_time"] <= end_time)]

        if df.empty:
            return events

        # Bin into time buckets
        bucket_size_hours = self.surge_window_hours
        bucket_td = timedelta(hours=bucket_size_hours)

        current = start_time
        bucket_counts = []

        while current < end_time:
            bucket_end = current + bucket_td
            bucket_obs = df[(df["ob_time"] >= current) & (df["ob_time"] < bucket_end)]
            unique_objects = bucket_obs["sat_no"].nunique()
            bucket_counts.append({
                "start": current,
                "end": bucket_end,
                "unique_objects": unique_objects,
            })
            current = bucket_end

        if len(bucket_counts) < 3:
            return events

        # Compute baseline (median unique objects per bucket)
        counts = [b["unique_objects"] for b in bucket_counts]
        import numpy as np
        baseline = float(np.median(counts))
        if baseline < 1:
            baseline = 1.0

        # Look for spikes above 2x baseline with minimum fragment count
        for bucket in bucket_counts:
            if (
                bucket["unique_objects"] > baseline * 2
                and bucket["unique_objects"] - baseline >= self.min_fragment_count
            ):
                # Identify the new objects in this bucket vs previous
                score = min(0.5, 0.2 + 0.05 * (bucket["unique_objects"] - baseline))

                label = EventLabel(
                    event_id=_generate_event_id("brkp"),
                    event_type="breakup",
                    confidence=confidence_from_score(score),
                    source="automated_detection",
                    primary_object_ids=[],  # Unknown parent
                    event_window=EventWindow(
                        start_time=bucket["start"],
                        end_time=bucket["end"],
                        peak_time=None,
                    ),
                    metadata={
                        "unique_objects_in_bucket": bucket["unique_objects"],
                        "baseline_objects": baseline,
                        "detection_source": "object_count_surge",
                        "detector": self.detector_name,
                    },
                )
                events.append(label)

        return events

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(
        self,
        observations_df: pd.DataFrame,
        time_window: Tuple[datetime, datetime],
        **kwargs,
    ) -> DetectionResult:
        """Run breakup detection.

        Args:
            observations_df: Observation DataFrame.
            time_window: Analysis time window.

        Returns:
            DetectionResult with detected breakup events.
        """
        import time as _time

        t0 = _time.monotonic()
        result = DetectionResult(observations_processed=len(observations_df))

        valid, msg = self.validate_input(observations_df)
        if not valid:
            result.warnings.append(f"Input validation failed: {msg}")
            result.processing_time_seconds = _time.monotonic() - t0
            return result

        satellite_ids = get_unique_objects(observations_df)

        # Primary: external API detection
        if self.use_external_apis:
            ext_events, ext_warnings = self._detect_from_external(
                time_window, satellite_ids
            )
            result.events.extend(ext_events)
            result.warnings.extend(ext_warnings)

        # Fallback: observation-based surge detection
        if not result.events:
            if not self.use_external_apis:
                result.warnings.append(
                    "External API detection disabled — using observation-based fallback"
                )
            else:
                result.warnings.append(
                    "No external breakup events found — running observation-based fallback"
                )

            surge_events = self._detect_from_object_surge(observations_df, time_window)
            result.events.extend(surge_events)

        result.processing_time_seconds = _time.monotonic() - t0
        logger.info(
            f"{self.detector_name}: detected {len(result.events)} breakup events"
        )
        return result
