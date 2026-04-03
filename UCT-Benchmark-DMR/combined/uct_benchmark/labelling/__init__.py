"""
Event Labelling System for the UCT Benchmark platform.

Detects space events (launches, maneuvers, proximity events, breakups)
from observation patterns and wraps existing TLE-based heuristics in
eventDetection.py.
"""

from .schema import EventLabel, EventWindow, LabelledDataset, ObservationLabel
from .detection_base import DetectionResult, EventDetector
from .pipeline import LabellingPipeline

__all__ = [
    "EventLabel",
    "EventWindow",
    "LabelledDataset",
    "ObservationLabel",
    "DetectionResult",
    "EventDetector",
    "LabellingPipeline",
]
