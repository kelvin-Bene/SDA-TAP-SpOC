"""
Abstract base class and utilities for event detectors.

All concrete detectors (launch, maneuver, proximity, breakup) inherit
from EventDetector and implement detect() and validate_input().
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd
from loguru import logger

from .schema import EventLabel


@dataclass
class DetectionResult:
    """Result container from an event detection run.

    Attributes:
        events: List of detected EventLabel objects.
        processing_time_seconds: Wall-clock time for detection.
        observations_processed: Number of observations analyzed.
        warnings: Non-fatal issues encountered during detection.
    """

    events: List[EventLabel] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    observations_processed: int = 0
    warnings: List[str] = field(default_factory=list)

    @property
    def event_count(self) -> int:
        return len(self.events)


class EventDetector(ABC):
    """Abstract base class for orbital event detectors.

    Subclasses must implement detect(), validate_input(), and the
    detector_name property.
    """

    @abstractmethod
    def detect(
        self,
        observations_df: pd.DataFrame,
        time_window: Tuple[datetime, datetime],
        **kwargs,
    ) -> DetectionResult:
        """Run event detection on the given observations.

        Args:
            observations_df: DataFrame of observations with at least
                'sat_no' and 'ob_time' columns.
            time_window: (start_time, end_time) tuple defining the
                analysis window.
            **kwargs: Detector-specific parameters.

        Returns:
            DetectionResult containing detected events and metadata.
        """
        ...

    @abstractmethod
    def validate_input(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """Validate that the input DataFrame has required columns.

        Args:
            df: DataFrame to validate.

        Returns:
            Tuple of (is_valid, error_message). error_message is empty
            when is_valid is True.
        """
        ...

    @property
    @abstractmethod
    def detector_name(self) -> str:
        """Human-readable name for this detector."""
        ...


# ================================================================
# Utility functions
# ================================================================


def get_unique_objects(
    df: pd.DataFrame, id_column: str = "sat_no"
) -> List[int]:
    """Get a sorted list of unique satellite IDs from a DataFrame.

    Args:
        df: DataFrame containing satellite observations.
        id_column: Name of the column holding satellite NORAD IDs.

    Returns:
        Sorted list of unique integer satellite IDs.
    """
    if id_column not in df.columns:
        logger.warning(f"Column '{id_column}' not found in DataFrame")
        return []
    return sorted(df[id_column].dropna().unique().astype(int).tolist())


def find_observation_gaps(
    df: pd.DataFrame,
    min_gap_hours: float,
    time_column: str = "ob_time",
) -> pd.DataFrame:
    """Find gaps in observation times that exceed a threshold.

    Args:
        df: DataFrame of observations (should be for a single object).
        min_gap_hours: Minimum gap duration in hours to flag.
        time_column: Name of the datetime column.

    Returns:
        DataFrame with columns 'gap_start', 'gap_end', 'gap_hours'
        for each gap exceeding the threshold.
    """
    if time_column not in df.columns:
        logger.warning(f"Column '{time_column}' not found in DataFrame")
        return pd.DataFrame(columns=["gap_start", "gap_end", "gap_hours"])

    sorted_df = df.sort_values(time_column).copy()
    sorted_df[time_column] = pd.to_datetime(sorted_df[time_column])

    times = sorted_df[time_column].values
    gaps = []

    for i in range(1, len(times)):
        gap_seconds = (
            pd.Timestamp(times[i]) - pd.Timestamp(times[i - 1])
        ).total_seconds()
        gap_hours = gap_seconds / 3600.0

        if gap_hours >= min_gap_hours:
            gaps.append(
                {
                    "gap_start": pd.Timestamp(times[i - 1]).to_pydatetime(),
                    "gap_end": pd.Timestamp(times[i]).to_pydatetime(),
                    "gap_hours": gap_hours,
                }
            )

    return pd.DataFrame(gaps, columns=["gap_start", "gap_end", "gap_hours"])


def _generate_event_id(prefix: str = "evt") -> str:
    """Generate a unique event ID string.

    Args:
        prefix: Short prefix indicating the event type
                (e.g., 'lnch', 'mnvr', 'prox', 'brkp').

    Returns:
        String like 'lnch_a1b2c3d4'.
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def confidence_from_score(score: float) -> str:
    """Convert a numeric confidence score (0-1) to a confidence level string.

    Args:
        score: Numeric confidence between 0.0 and 1.0.

    Returns:
        One of: confirmed, high, medium, low, speculative.
    """
    if score >= 0.95:
        return "confirmed"
    elif score >= 0.75:
        return "high"
    elif score >= 0.50:
        return "medium"
    elif score >= 0.25:
        return "low"
    else:
        return "speculative"
