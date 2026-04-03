"""
Labelling pipeline orchestrator.

Runs multiple event detectors on an observation dataset, aggregates
their results, deduplicates overlapping events, and persists the
labelled dataset to the database.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .detection_base import DetectionResult, EventDetector
from .schema import EventLabel, EventWindow, LabelledDataset

import pandas as pd


class LabellingPipeline:
    """Orchestrate multiple event detectors on a single dataset.

    Usage::

        pipeline = LabellingPipeline([
            LaunchDetector(),
            ManeuverDetector(),
            ProximityDetector(),
            BreakupDetector(),
        ])
        dataset = pipeline.run(observations_df, (start, end))
        count = pipeline.persist(dataset, db)

    Args:
        detectors: List of EventDetector instances to run.
        dataset_id: Optional dataset identifier. If not provided,
            one is generated at run time.
    """

    def __init__(
        self,
        detectors: List[EventDetector],
        dataset_id: Optional[str] = None,
    ):
        self.detectors = detectors
        self.dataset_id = dataset_id

    def run(
        self,
        observations_df: pd.DataFrame,
        time_window: Tuple[datetime, datetime],
        **kwargs,
    ) -> LabelledDataset:
        """Run all detectors and aggregate results.

        Args:
            observations_df: Observation DataFrame with at minimum
                'sat_no' and 'ob_time' columns.
            time_window: (start_time, end_time) for the analysis.
            **kwargs: Extra keyword arguments forwarded to each detector.

        Returns:
            LabelledDataset containing all detected events.
        """
        import time as _time

        t0 = _time.monotonic()
        ds_id = self.dataset_id or f"ds_{id(observations_df)}"

        labelled = LabelledDataset(dataset_id=ds_id)
        all_warnings: List[str] = []

        for detector in self.detectors:
            detector_name = detector.detector_name
            logger.info(f"Running {detector_name}...")

            try:
                result: DetectionResult = detector.detect(
                    observations_df, time_window, **kwargs
                )

                for event in result.events:
                    labelled.add_event_label(event)

                if result.warnings:
                    for w in result.warnings:
                        all_warnings.append(f"[{detector_name}] {w}")

                logger.info(
                    f"{detector_name}: {result.event_count} events, "
                    f"{result.processing_time_seconds:.2f}s"
                )

            except Exception as exc:
                msg = f"[{detector_name}] Detector failed: {exc}"
                logger.error(msg)
                all_warnings.append(msg)

        # Deduplicate overlapping events of the same type on the same objects
        labelled.event_labels = self._deduplicate(labelled.event_labels)

        elapsed = _time.monotonic() - t0
        summary = labelled.summary()
        logger.info(
            f"LabellingPipeline complete: {summary['total_events']} events "
            f"in {elapsed:.2f}s | types={summary['events_by_type']}"
        )

        if all_warnings:
            logger.warning(
                f"Pipeline generated {len(all_warnings)} warnings: "
                + "; ".join(all_warnings[:5])
            )

        return labelled

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def persist(self, dataset: LabelledDataset, db: Any) -> int:
        """Write detected events to the database via EventRepository.

        Args:
            dataset: LabelledDataset to persist.
            db: DatabaseManager instance.

        Returns:
            Number of events created in the database.
        """
        from uct_benchmark.database.repository import EventRepository

        repo = EventRepository(db)
        created = 0

        for label in dataset.event_labels:
            try:
                # Map confidence string to numeric for the DB
                primary_sat = label.primary_object_ids[0] if label.primary_object_ids else 0
                secondary_sat = (
                    label.secondary_object_ids[0]
                    if label.secondary_object_ids
                    else None
                )

                event_id = repo.create_event(
                    event_type=label.event_type,
                    primary_sat_no=primary_sat,
                    event_time_start=label.event_window.start_time,
                    event_time_end=label.event_window.end_time,
                    secondary_sat_no=secondary_sat,
                    confidence=label.confidence_score,
                    detection_method="AUTOMATIC",
                    source=label.source,
                    external_id=label.event_id,
                    labelled_by=f"pipeline:{','.join(d.detector_name for d in self.detectors)}",
                    notes=str(label.metadata) if label.metadata else None,
                )

                if event_id > 0:
                    created += 1

            except Exception as exc:
                logger.error(
                    f"Failed to persist event {label.event_id}: {exc}"
                )

        logger.info(f"Persisted {created}/{len(dataset.event_labels)} events to database")
        return created

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(events: List[EventLabel]) -> List[EventLabel]:
        """Remove duplicate / overlapping events of the same type.

        Two events are considered duplicates when they share the same
        event_type, overlap in time, and involve at least one common
        primary object. The higher-confidence event is kept.
        """
        if len(events) <= 1:
            return events

        # Group by event type
        by_type: Dict[str, List[EventLabel]] = {}
        for ev in events:
            by_type.setdefault(ev.event_type, []).append(ev)

        unique: List[EventLabel] = []

        for event_type, group in by_type.items():
            # Sort by confidence score descending so we keep the best
            group.sort(key=lambda e: e.confidence_score, reverse=True)
            kept: List[EventLabel] = []

            for candidate in group:
                is_dup = False
                for existing in kept:
                    # Check temporal overlap
                    if not candidate.event_window.overlaps(existing.event_window):
                        continue
                    # Check object overlap
                    cand_objects = set(candidate.primary_object_ids)
                    exist_objects = set(existing.primary_object_ids)
                    if cand_objects & exist_objects:
                        is_dup = True
                        break

                if not is_dup:
                    kept.append(candidate)

            unique.extend(kept)

        return unique
