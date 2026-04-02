"""Event labelling endpoints.

Provides REST endpoints for listing, querying, and triggering
event detection on observation data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

from backend_api.auth import CurrentUser, get_current_user
from backend_api.database import get_db
from backend_api.middleware.auth import require_admin
from uct_benchmark.database.connection import DatabaseManager
from uct_benchmark.database.repository import EventRepository

router = APIRouter()


# ============================================================
# Pydantic response / request models
# ============================================================


class EventTypeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None


class EventSummary(BaseModel):
    id: int
    event_type: str
    primary_sat_no: int
    secondary_sat_no: Optional[int] = None
    event_time_start: Optional[str] = None
    event_time_end: Optional[str] = None
    confidence: Optional[float] = None
    detection_method: Optional[str] = None
    source: Optional[str] = None
    dataset_id: Optional[int] = None


class EventDetail(EventSummary):
    external_id: Optional[str] = None
    labelled_by: Optional[str] = None
    labelled_at: Optional[str] = None
    notes: Optional[str] = None
    detection_config: Optional[str] = None
    observations: List[Dict[str, Any]] = []


class DetectEventsRequest(BaseModel):
    sat_nos: List[int] = Field(..., min_length=1, description="NORAD IDs to analyze")
    time_window_start: str = Field(..., description="ISO datetime start")
    time_window_end: str = Field(..., description="ISO datetime end")
    detector_types: List[str] = Field(
        default=["launch", "maneuver", "breakup"],
        description="Detector types to run: launch, maneuver, proximity, breakup",
    )


class DetectEventsResponse(BaseModel):
    job_id: str
    message: str


# ============================================================
# Helper: get DB dependency
# ============================================================


def _get_db() -> DatabaseManager:
    """Retrieve the global DatabaseManager."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return db


# ============================================================
# Endpoints
# ============================================================


@router.get("/types", response_model=List[EventTypeResponse])
async def list_event_types(
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all available event types."""
    db = _get_db()
    repo = EventRepository(db)
    df = repo.list_event_types()
    return [
        EventTypeResponse(
            id=int(row["id"]),
            name=row["name"],
            description=row.get("description"),
        )
        for _, row in df.iterrows()
    ]


@router.get("/", response_model=List[EventSummary])
async def list_events(
    event_type: Optional[str] = Query(None, description="Filter by event type name"),
    sat_no: Optional[int] = Query(None, description="Filter by satellite NORAD ID"),
    start_time: Optional[str] = Query(None, description="ISO datetime lower bound"),
    end_time: Optional[str] = Query(None, description="ISO datetime upper bound"),
    dataset_id: Optional[int] = Query(None, description="Filter by dataset ID"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
):
    """List events with optional filters."""
    db = _get_db()
    repo = EventRepository(db)

    # Build dynamic query
    conditions = []
    params: list = []

    if event_type:
        conditions.append("et.name = ?")
        params.append(event_type)
    if sat_no:
        conditions.append("(e.primary_sat_no = ? OR e.secondary_sat_no = ?)")
        params.extend([sat_no, sat_no])
    if start_time:
        try:
            dt = datetime.fromisoformat(start_time)
            conditions.append("e.event_time_start >= ?")
            params.append(dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")
    if end_time:
        try:
            dt = datetime.fromisoformat(end_time)
            conditions.append("e.event_time_end <= ?")
            params.append(dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")
    if dataset_id is not None:
        conditions.append("e.dataset_id = ?")
        params.append(dataset_id)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT
            e.id,
            et.name as event_type,
            e.primary_sat_no,
            e.secondary_sat_no,
            e.event_time_start,
            e.event_time_end,
            e.confidence,
            e.detection_method,
            e.source,
            e.dataset_id
        FROM events e
        JOIN event_types et ON e.event_type_id = et.id
        WHERE {where_clause}
        ORDER BY e.event_time_start DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    try:
        df = repo.to_dataframe(query, tuple(params))
    except Exception as exc:
        logger.error(f"Event list query failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to query events")

    results = []
    for _, row in df.iterrows():
        results.append(EventSummary(
            id=int(row["id"]),
            event_type=row["event_type"],
            primary_sat_no=int(row["primary_sat_no"]) if row.get("primary_sat_no") else 0,
            secondary_sat_no=int(row["secondary_sat_no"]) if row.get("secondary_sat_no") else None,
            event_time_start=str(row["event_time_start"]) if row.get("event_time_start") else None,
            event_time_end=str(row["event_time_end"]) if row.get("event_time_end") else None,
            confidence=float(row["confidence"]) if row.get("confidence") is not None else None,
            detection_method=row.get("detection_method"),
            source=row.get("source"),
            dataset_id=int(row["dataset_id"]) if row.get("dataset_id") else None,
        ))

    return results


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get event detail with linked observations."""
    db = _get_db()
    repo = EventRepository(db)

    event = repo.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get linked observations
    obs_df = repo.get_event_observations(event_id)
    observations = []
    for _, obs_row in obs_df.iterrows():
        observations.append({
            "id": obs_row.get("id"),
            "sat_no": int(obs_row["sat_no"]) if obs_row.get("sat_no") else None,
            "ob_time": str(obs_row["ob_time"]) if obs_row.get("ob_time") else None,
            "ra": float(obs_row["ra"]) if obs_row.get("ra") is not None else None,
            "declination": float(obs_row["declination"]) if obs_row.get("declination") is not None else None,
        })

    return EventDetail(
        id=int(event["id"]),
        event_type=event.get("event_type_name", "unknown"),
        primary_sat_no=int(event["primary_sat_no"]) if event.get("primary_sat_no") else 0,
        secondary_sat_no=int(event["secondary_sat_no"]) if event.get("secondary_sat_no") else None,
        event_time_start=str(event["event_time_start"]) if event.get("event_time_start") else None,
        event_time_end=str(event["event_time_end"]) if event.get("event_time_end") else None,
        confidence=float(event["confidence"]) if event.get("confidence") is not None else None,
        detection_method=event.get("detection_method"),
        source=event.get("source"),
        dataset_id=int(event["dataset_id"]) if event.get("dataset_id") else None,
        external_id=event.get("external_id"),
        labelled_by=event.get("labelled_by"),
        labelled_at=str(event["labelled_at"]) if event.get("labelled_at") else None,
        notes=event.get("notes"),
        detection_config=event.get("detection_config"),
        observations=observations,
    )


@router.post("/detect", response_model=DetectEventsResponse)
async def trigger_event_detection(
    body: DetectEventsRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Trigger event detection as a background job."""
    from backend_api.jobs.workers import submit_event_detection

    try:
        start_dt = datetime.fromisoformat(body.time_window_start)
        end_dt = datetime.fromisoformat(body.time_window_end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {exc}")

    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="end time must be after start time")

    # Validate detector types
    valid_types = {"launch", "maneuver", "proximity", "breakup"}
    invalid = set(body.detector_types) - valid_types
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid detector types: {invalid}. Valid: {valid_types}",
        )

    job = submit_event_detection(
        sat_nos=body.sat_nos,
        time_window_start=start_dt,
        time_window_end=end_dt,
        detector_types=body.detector_types,
        user_id=current_user.id,
    )

    logger.info(
        f"Event detection job {job.id} created by {current_user.email} "
        f"for {len(body.sat_nos)} objects, detectors={body.detector_types}"
    )

    return DetectEventsResponse(
        job_id=job.id,
        message=f"Event detection job started for {len(body.sat_nos)} objects",
    )


@router.delete("/{event_id}")
async def delete_event(
    event_id: int,
    current_user: CurrentUser = Depends(require_admin),
):
    """Delete an event (admin only)."""
    db = _get_db()
    repo = EventRepository(db)

    existing = repo.get_event(event_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Event not found")

    repo.delete_event(event_id)
    logger.info(f"Event {event_id} deleted by admin {current_user.email}")

    return {"detail": f"Event {event_id} deleted"}
