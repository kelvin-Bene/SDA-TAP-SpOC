"""
Data model classes for the Event Labelling System.

Provides dataclass-based models for event labels, observation labels,
event time windows, and labelled datasets. These are used by the
detection pipeline to represent detected events before persisting
them to the database.

Uses dataclasses (not Pydantic) since this lives in the uct_benchmark
module rather than backend_api.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# Valid event types matching the event_types table
VALID_EVENT_TYPES = {"launch", "maneuver", "proximity", "breakup", "reentry", "unknown"}

# Confidence levels ordered from highest to lowest
VALID_CONFIDENCE_LEVELS = {"confirmed", "high", "medium", "low", "speculative"}

# Detection sources
VALID_SOURCES = {"automated_detection", "external_database", "manual", "ml_model"}

# Observation relevance levels
VALID_RELEVANCE_LEVELS = {"primary", "secondary", "context"}


@dataclass
class EventWindow:
    """Time window for an orbital event.

    Attributes:
        start_time: Beginning of the event window.
        end_time: End of the event window.
        peak_time: Optional peak/midpoint time of the event.
    """

    start_time: datetime
    end_time: datetime
    peak_time: Optional[datetime] = None

    def duration_seconds(self) -> float:
        """Return the duration of the event window in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    def contains(self, time: datetime) -> bool:
        """Check if a given time falls within this event window."""
        return self.start_time <= time <= self.end_time

    def overlaps(self, other: "EventWindow") -> bool:
        """Check if this window overlaps with another."""
        return self.start_time <= other.end_time and other.start_time <= self.end_time


@dataclass
class EventLabel:
    """Label for a detected orbital event.

    Attributes:
        event_id: Unique identifier for the event (generated string).
        event_type: Type of event (launch, maneuver, proximity, breakup, reentry).
        confidence: Confidence level string (confirmed, high, medium, low, speculative).
        source: Detection source (automated_detection, external_database, manual).
        primary_object_ids: NORAD IDs of primary objects involved.
        event_window: Time window of the event.
        secondary_object_ids: NORAD IDs of secondary objects (e.g., debris).
        metadata: Additional event-specific data.
        created_at: Timestamp when this label was created.
    """

    event_id: str
    event_type: str
    confidence: str
    source: str
    primary_object_ids: List[int]
    event_window: EventWindow
    secondary_object_ids: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.event_type not in VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type '{self.event_type}'. "
                f"Must be one of: {VALID_EVENT_TYPES}"
            )
        if self.confidence not in VALID_CONFIDENCE_LEVELS:
            raise ValueError(
                f"Invalid confidence '{self.confidence}'. "
                f"Must be one of: {VALID_CONFIDENCE_LEVELS}"
            )

    @property
    def confidence_score(self) -> float:
        """Convert confidence level string to a numeric score (0-1)."""
        mapping = {
            "confirmed": 1.0,
            "high": 0.85,
            "medium": 0.6,
            "low": 0.35,
            "speculative": 0.15,
        }
        return mapping.get(self.confidence, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "source": self.source,
            "primary_object_ids": self.primary_object_ids,
            "secondary_object_ids": self.secondary_object_ids,
            "event_window": {
                "start_time": self.event_window.start_time.isoformat(),
                "end_time": self.event_window.end_time.isoformat(),
                "peak_time": self.event_window.peak_time.isoformat() if self.event_window.peak_time else None,
                "duration_seconds": self.event_window.duration_seconds(),
            },
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ObservationLabel:
    """Links an observation to a detected event.

    Attributes:
        observation_id: ID of the observation being labelled.
        event_id: ID of the event this observation relates to.
        event_type: Type of the related event.
        relevance: How this observation relates to the event
                   (primary, secondary, context).
    """

    observation_id: str
    event_id: str
    event_type: str
    relevance: str = "primary"

    def __post_init__(self) -> None:
        if self.relevance not in VALID_RELEVANCE_LEVELS:
            raise ValueError(
                f"Invalid relevance '{self.relevance}'. "
                f"Must be one of: {VALID_RELEVANCE_LEVELS}"
            )


@dataclass
class LabelledDataset:
    """A collection of event labels and observation labels for a dataset.

    Attributes:
        dataset_id: Identifier for the dataset being labelled.
        event_labels: List of detected event labels.
        observation_labels: List of observation-to-event linkages.
    """

    dataset_id: str
    event_labels: List[EventLabel] = field(default_factory=list)
    observation_labels: List[ObservationLabel] = field(default_factory=list)

    def add_event_label(self, label: EventLabel) -> None:
        """Add an event label, avoiding duplicates by event_id."""
        existing_ids = {el.event_id for el in self.event_labels}
        if label.event_id not in existing_ids:
            self.event_labels.append(label)

    def add_observation_label(self, label: ObservationLabel) -> None:
        """Add an observation label."""
        self.observation_labels.append(label)

    def get_events_by_type(self, event_type: str) -> List[EventLabel]:
        """Filter event labels by event type."""
        return [el for el in self.event_labels if el.event_type == event_type]

    def get_events_in_window(
        self, start_time: datetime, end_time: datetime
    ) -> List[EventLabel]:
        """Get events whose windows overlap the given time range."""
        query_window = EventWindow(start_time=start_time, end_time=end_time)
        return [
            el for el in self.event_labels
            if el.event_window.overlaps(query_window)
        ]

    def summary(self) -> Dict[str, Any]:
        """Return a summary of this labelled dataset."""
        type_counts: Dict[str, int] = {}
        for el in self.event_labels:
            type_counts[el.event_type] = type_counts.get(el.event_type, 0) + 1

        confidence_counts: Dict[str, int] = {}
        for el in self.event_labels:
            confidence_counts[el.confidence] = confidence_counts.get(el.confidence, 0) + 1

        return {
            "dataset_id": self.dataset_id,
            "total_events": len(self.event_labels),
            "total_observation_labels": len(self.observation_labels),
            "events_by_type": type_counts,
            "events_by_confidence": confidence_counts,
        }
