"""
Maneuver event detector.

Wraps the existing detect_maneuvers_from_tle_history() and
detect_long_duration_maneuvers() functions from eventDetection.py,
converting their OrbitalEvent results into the EventLabel format.

Also detects maneuvers from observation gaps (extended absence
followed by position offset).
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
from loguru import logger

from .detection_base import (
    DetectionResult,
    EventDetector,
    _generate_event_id,
    confidence_from_score,
    find_observation_gaps,
    get_unique_objects,
)
from .schema import EventLabel, EventWindow


class ManeuverDetector(EventDetector):
    """Detect orbital maneuvers by wrapping existing TLE heuristics.

    This detector delegates to the proven functions in
    ``uct_benchmark.data.eventDetection`` and converts their
    ``OrbitalEvent`` outputs into ``EventLabel`` objects.

    It also supplements TLE-based detection with observation-gap
    analysis: if an object has a gap longer than ``gap_threshold_hours``
    it is flagged as a potential maneuver window.

    Args:
        sma_threshold_km: Semi-major axis change threshold (km).
        ecc_threshold: Eccentricity change threshold.
        inc_threshold_deg: Inclination change threshold (degrees).
        gap_threshold_hours: Observation gap threshold for gap-based
            detection (hours). Defaults to 24.
        include_long_thrust: Also detect long-duration low-thrust
            maneuvers via the existing LL heuristic.
    """

    def __init__(
        self,
        sma_threshold_km: float = 10.0,
        ecc_threshold: float = 0.001,
        inc_threshold_deg: float = 0.1,
        gap_threshold_hours: float = 24.0,
        include_long_thrust: bool = True,
    ):
        self.sma_threshold_km = sma_threshold_km
        self.ecc_threshold = ecc_threshold
        self.inc_threshold_deg = inc_threshold_deg
        self.gap_threshold_hours = gap_threshold_hours
        self.include_long_thrust = include_long_thrust

    @property
    def detector_name(self) -> str:
        return "ManeuverDetector"

    def validate_input(self, df: pd.DataFrame) -> Tuple[bool, str]:
        required = {"sat_no", "ob_time"}
        missing = required - set(df.columns)
        if missing:
            return False, f"Missing required columns: {missing}"
        if df.empty:
            return False, "DataFrame is empty"
        return True, ""

    # ------------------------------------------------------------------
    # Internal: wrap existing eventDetection functions
    # ------------------------------------------------------------------

    def _detect_from_tle(
        self,
        tle_df: pd.DataFrame,
        satellite_ids: List[int],
        time_window: Tuple[datetime, datetime],
    ) -> List[EventLabel]:
        """Run TLE-based maneuver detection via eventDetection module."""
        events: List[EventLabel] = []

        try:
            from uct_benchmark.data.eventDetection import (
                EventDetectionConfig,
                EventType,
                detect_long_duration_maneuvers,
                detect_maneuvers_from_tle_history,
            )
        except ImportError as exc:
            logger.warning(f"Could not import eventDetection module: {exc}")
            return events

        config = EventDetectionConfig(
            sma_threshold_km=self.sma_threshold_km,
            ecc_threshold=self.ecc_threshold,
            inc_threshold_deg=self.inc_threshold_deg,
        )

        start_time, end_time = time_window
        # Normalize to naive datetimes for comparison with OrbitalEvent times
        start_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
        end_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time

        for sat_id in satellite_ids:
            # Impulsive maneuver detection
            orbital_events = detect_maneuvers_from_tle_history(
                tle_df, sat_id, config
            )

            for oe in orbital_events:
                # Filter to events within the analysis time window
                oe_time = oe.event_time.replace(tzinfo=None) if oe.event_time.tzinfo else oe.event_time
                if oe_time < start_naive or oe_time > end_naive:
                    continue

                event_end = oe.end_time or (oe.event_time + timedelta(hours=1))
                confidence_level = confidence_from_score(oe.confidence)

                label = EventLabel(
                    event_id=_generate_event_id("mnvr"),
                    event_type="maneuver",
                    confidence=confidence_level,
                    source="automated_detection",
                    primary_object_ids=[sat_id],
                    event_window=EventWindow(
                        start_time=oe.event_time,
                        end_time=event_end,
                        peak_time=oe.event_time,
                    ),
                    metadata={
                        "delta_v_m_s": oe.delta_v_m_s,
                        "direction": oe.direction,
                        "detection_source": oe.source,
                        "maneuver_type": "impulsive",
                        "detector": self.detector_name,
                        **oe.metadata,
                    },
                )
                events.append(label)

            # Long-thrust maneuver detection
            if self.include_long_thrust:
                lt_events = detect_long_duration_maneuvers(
                    tle_df, sat_id, config
                )
                for oe in lt_events:
                    oe_time = oe.event_time.replace(tzinfo=None) if oe.event_time.tzinfo else oe.event_time
                    oe_end = oe.end_time.replace(tzinfo=None) if oe.end_time and oe.end_time.tzinfo else oe.end_time
                    if oe_time < start_naive:
                        continue
                    if oe_end and oe_end < start_naive:
                        continue

                    event_end = oe.end_time or (oe.event_time + timedelta(days=7))
                    confidence_level = confidence_from_score(oe.confidence)

                    label = EventLabel(
                        event_id=_generate_event_id("mnvr"),
                        event_type="maneuver",
                        confidence=confidence_level,
                        source="automated_detection",
                        primary_object_ids=[sat_id],
                        event_window=EventWindow(
                            start_time=oe.event_time,
                            end_time=event_end,
                            peak_time=None,
                        ),
                        metadata={
                            "delta_v_m_s": oe.delta_v_m_s,
                            "direction": oe.direction,
                            "detection_source": oe.source,
                            "maneuver_type": "long_thrust",
                            "detector": self.detector_name,
                            **oe.metadata,
                        },
                    )
                    events.append(label)

        return events

    def _detect_from_observation_gaps(
        self,
        observations_df: pd.DataFrame,
        satellite_ids: List[int],
        time_window: Tuple[datetime, datetime],
    ) -> List[EventLabel]:
        """Detect potential maneuvers from observation gaps.

        An observation gap longer than gap_threshold_hours may indicate
        the object maneuvered (changed orbit enough that the sensor
        lost track temporarily).
        """
        events: List[EventLabel] = []
        start_time, end_time = time_window

        # Normalize to naive datetimes for comparison (gaps are naive)
        start_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
        end_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time

        for sat_id in satellite_ids:
            sat_obs = observations_df[observations_df["sat_no"] == sat_id]
            if len(sat_obs) < 2:
                continue

            gaps = find_observation_gaps(
                sat_obs, self.gap_threshold_hours, time_column="ob_time"
            )

            for _, gap in gaps.iterrows():
                gap_start = gap["gap_start"]
                gap_end = gap["gap_end"]

                # Only include gaps within the time window
                if gap_end < start_naive or gap_start > end_naive:
                    continue

                gap_hours = gap["gap_hours"]
                # Longer gaps = lower confidence (could be sensor outage)
                # Sweet spot is 24-72 hours
                if gap_hours <= 72:
                    score = 0.4
                elif gap_hours <= 168:
                    score = 0.25
                else:
                    score = 0.15

                label = EventLabel(
                    event_id=_generate_event_id("mnvr"),
                    event_type="maneuver",
                    confidence=confidence_from_score(score),
                    source="automated_detection",
                    primary_object_ids=[sat_id],
                    event_window=EventWindow(
                        start_time=gap_start,
                        end_time=gap_end,
                        peak_time=None,
                    ),
                    metadata={
                        "gap_hours": gap_hours,
                        "detection_source": "observation_gap",
                        "maneuver_type": "gap_inferred",
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
        *,
        tle_df: Optional[pd.DataFrame] = None,
        **kwargs,
    ) -> DetectionResult:
        """Run maneuver detection.

        Args:
            observations_df: Observation DataFrame with 'sat_no' and
                'ob_time' columns.
            time_window: (start, end) datetime tuple.
            tle_df: Optional TLE DataFrame for TLE-based detection.
                If not provided, only observation-gap detection runs.

        Returns:
            DetectionResult with detected maneuver events.
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

        # TLE-based detection (primary method)
        if tle_df is not None and not tle_df.empty:
            tle_events = self._detect_from_tle(tle_df, satellite_ids, time_window)
            result.events.extend(tle_events)
        else:
            result.warnings.append(
                "No TLE data provided — TLE-based maneuver detection skipped. "
                "Only observation-gap heuristic will be used."
            )

        # Observation-gap detection (supplementary)
        gap_events = self._detect_from_observation_gaps(
            observations_df, satellite_ids, time_window
        )
        result.events.extend(gap_events)

        result.processing_time_seconds = _time.monotonic() - t0
        logger.info(
            f"{self.detector_name}: detected {len(result.events)} maneuver events "
            f"({len(result.events) - len(gap_events)} TLE-based, "
            f"{len(gap_events)} gap-based)"
        )
        return result
