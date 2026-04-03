"""
Launch event detector.

Detects new objects appearing in observations within a time window
by finding first-appearance times and clustering them to identify
launch events (multiple objects from the same launch appearing close
in time).
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Tuple

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


class LaunchDetector(EventDetector):
    """Detect launch events from new object appearances.

    Identifies objects whose first observation falls within the analysis
    time window, then clusters those first-appearances by temporal
    proximity to identify launch groups.

    Args:
        new_object_window_hours: Maximum hours between first appearances
            to consider them part of the same launch (default 48).
        min_observations: Minimum observations an object must have to
            be considered a real detection rather than noise (default 3).
        confidence_threshold: Minimum confidence score (0-1) to report
            an event (default 0.5).
    """

    def __init__(
        self,
        new_object_window_hours: float = 48.0,
        min_observations: int = 3,
        confidence_threshold: float = 0.5,
    ):
        self.new_object_window_hours = new_object_window_hours
        self.min_observations = min_observations
        self.confidence_threshold = confidence_threshold

    @property
    def detector_name(self) -> str:
        return "LaunchDetector"

    def validate_input(self, df: pd.DataFrame) -> Tuple[bool, str]:
        required = {"sat_no", "ob_time"}
        missing = required - set(df.columns)
        if missing:
            return False, f"Missing required columns: {missing}"
        if df.empty:
            return False, "DataFrame is empty"
        return True, ""

    def detect(
        self,
        observations_df: pd.DataFrame,
        time_window: Tuple[datetime, datetime],
        **kwargs,
    ) -> DetectionResult:
        """Detect launch events from observation data.

        Args:
            observations_df: DataFrame with 'sat_no' and 'ob_time' columns.
            time_window: (start_time, end_time) for the analysis window.

        Returns:
            DetectionResult with detected launch events.
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
        df = observations_df.copy()
        df["ob_time"] = pd.to_datetime(df["ob_time"])

        # Find first observation time and total count per object
        first_obs = df.groupby("sat_no").agg(
            first_time=("ob_time", "min"),
            obs_count=("ob_time", "count"),
        ).reset_index()

        # Filter to objects whose first appearance is within the time window
        new_objects = first_obs[
            (first_obs["first_time"] >= pd.Timestamp(start_time))
            & (first_obs["first_time"] <= pd.Timestamp(end_time))
            & (first_obs["obs_count"] >= self.min_observations)
        ].copy()

        if new_objects.empty:
            result.processing_time_seconds = _time.monotonic() - t0
            return result

        # Sort by first appearance time for clustering
        new_objects = new_objects.sort_values("first_time")

        # Cluster new objects by temporal proximity
        clusters: List[List[dict]] = []
        current_cluster: List[dict] = []

        for _, row in new_objects.iterrows():
            obj_info = {
                "sat_no": int(row["sat_no"]),
                "first_time": row["first_time"].to_pydatetime(),
                "obs_count": int(row["obs_count"]),
            }

            if not current_cluster:
                current_cluster.append(obj_info)
            else:
                last_time = current_cluster[-1]["first_time"]
                gap_hours = (obj_info["first_time"] - last_time).total_seconds() / 3600.0
                if gap_hours <= self.new_object_window_hours:
                    current_cluster.append(obj_info)
                else:
                    clusters.append(current_cluster)
                    current_cluster = [obj_info]

        if current_cluster:
            clusters.append(current_cluster)

        # Create EventLabels for each cluster
        for cluster in clusters:
            sat_nos = [obj["sat_no"] for obj in cluster]
            first_times = [obj["first_time"] for obj in cluster]
            obs_counts = [obj["obs_count"] for obj in cluster]

            cluster_start = min(first_times)
            cluster_end = max(first_times) + timedelta(hours=1)

            # Confidence based on number of objects and observation counts
            # More objects and more observations = higher confidence
            obj_factor = min(1.0, len(cluster) / 5.0)
            obs_factor = min(1.0, sum(obs_counts) / (len(cluster) * 10))
            score = 0.4 * obj_factor + 0.6 * obs_factor

            if score < self.confidence_threshold:
                continue

            event = EventLabel(
                event_id=_generate_event_id("lnch"),
                event_type="launch",
                confidence=confidence_from_score(score),
                source="automated_detection",
                primary_object_ids=sat_nos,
                event_window=EventWindow(
                    start_time=cluster_start,
                    end_time=cluster_end,
                    peak_time=cluster_start,
                ),
                metadata={
                    "object_count": len(cluster),
                    "first_appearances": {
                        str(obj["sat_no"]): obj["first_time"].isoformat()
                        for obj in cluster
                    },
                    "detector": self.detector_name,
                },
            )
            result.events.append(event)

        result.processing_time_seconds = _time.monotonic() - t0
        logger.info(
            f"{self.detector_name}: detected {len(result.events)} launch events "
            f"from {len(new_objects)} new objects"
        )
        return result
