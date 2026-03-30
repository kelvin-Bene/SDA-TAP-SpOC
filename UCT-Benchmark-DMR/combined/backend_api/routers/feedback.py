"""Feedback and bug report endpoints."""

import json
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger

from backend_api.middleware.auth import AuthUser as CurrentUser, get_current_user, get_optional_user
from backend_api.database import get_db
from backend_api.models.feedback import (
    FeedbackCreate,
    FeedbackListItem,
    FeedbackResponse,
    FeedbackUpdate,
)
from uct_benchmark.database.connection import DatabaseManager

router = APIRouter()


# ---------------------------------------------------------------------------
# Lightweight in-process rate limiter (no slowapi dependency required)
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Simple per-IP sliding-window rate limiter."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_hits: int, window_seconds: int) -> None:
        """Raise 429 if *key* has exceeded *max_hits* within *window_seconds*."""
        now = time.monotonic()
        timestamps = self._hits[key]
        # Prune expired entries
        self._hits[key] = [t for t in timestamps if now - t < window_seconds]
        if len(self._hits[key]) >= max_hits:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
            )
        self._hits[key].append(now)


_limiter = _RateLimiter()


def _rate_limit(request: Request, max_hits: int = 5, window_seconds: int = 60) -> None:
    """Apply rate limiting based on client IP."""
    client_ip = request.client.host if request.client else "unknown"
    _limiter.check(client_ip, max_hits, window_seconds)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_description(text: str) -> str:
    """Strip HTML and script tags from user-supplied text."""
    # Remove <script>...</script> blocks (including content)
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# POST /feedback  --  submit feedback (auth optional)
# ---------------------------------------------------------------------------

@router.post("/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    body: FeedbackCreate,
    request: Request,
    user: Optional[CurrentUser] = Depends(get_optional_user),
    db: DatabaseManager = Depends(get_db),
) -> FeedbackResponse:
    """
    Submit a feedback or bug report.

    Authentication is optional -- anonymous submissions are accepted.
    Rate-limited to 5 requests per minute per IP.
    """
    # Rate limit
    _rate_limit(request)

    feedback_id = str(uuid.uuid4())

    # Sanitize description
    description = _sanitize_description(body.description)
    if not description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Description must not be empty after sanitization.",
        )

    # Screenshot handling: store base64 as-is for now (storage integration later)
    screenshot_url: Optional[str] = None
    if body.screenshot_base64:
        # Validate that it's valid base64
        try:
            import base64
            base64.b64decode(body.screenshot_base64, validate=True)
            # Placeholder: save raw base64; real upload in Phase 5.2
            screenshot_url = f"pending://{feedback_id}"
        except Exception:
            logger.warning(f"Invalid base64 screenshot for feedback {feedback_id}")

    # Serialise list fields to JSON for storage
    recent_actions_json = json.dumps(body.recent_actions) if body.recent_actions else None
    console_errors_json = json.dumps(body.console_errors) if body.console_errors else None

    # Reporter info from JWT (if authenticated)
    reporter_id: Optional[str] = user.id if user else None
    reporter_email: Optional[str] = user.email if user else None

    try:
        db.execute(
            """
            INSERT INTO feedback (
                id, description, severity, screenshot_url,
                page_url, user_agent, viewport,
                recent_actions, console_errors, sentry_event_id,
                reporter_id, reporter_email, status, created_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (
                feedback_id,
                description,
                body.severity,
                screenshot_url,
                body.page_url,
                body.user_agent,
                body.viewport,
                recent_actions_json,
                console_errors_json,
                body.sentry_event_id,
                reporter_id,
                reporter_email,
                "open",
                datetime.utcnow().isoformat(),
            ),
        )
    except Exception as e:
        logger.error(f"Failed to insert feedback {feedback_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save feedback. Please try again.",
        )

    logger.info(
        f"Feedback {feedback_id} submitted "
        f"(severity={body.severity}, user={reporter_email or 'anonymous'})"
    )

    return FeedbackResponse(
        success=True,
        feedback_id=feedback_id,
        message="Feedback submitted successfully.",
    )


# ---------------------------------------------------------------------------
# GET /feedback  --  list feedback (admin only)
# ---------------------------------------------------------------------------

@router.get("/feedback", response_model=list[FeedbackListItem])
async def list_feedback(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
    status_filter: Optional[str] = None,
    severity: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[FeedbackListItem]:
    """
    List all feedback entries.

    Admin only. Supports filtering by status, severity, and date range.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    query = (
        "SELECT id, severity, description, page_url, reporter_email, status, created_at "
        "FROM feedback WHERE 1=1"
    )
    params: list = []

    if status_filter:
        query += " AND status = %s"
        params.append(status_filter)

    if severity:
        query += " AND severity = %s"
        params.append(severity)

    if date_from:
        query += " AND created_at >= %s"
        params.append(date_from)

    if date_to:
        query += " AND created_at <= %s"
        params.append(date_to)

    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    try:
        result = db.execute(query, tuple(params))
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
    except Exception as e:
        logger.error(f"Failed to list feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback list.",
        )

    items: list[FeedbackListItem] = []
    for row in rows:
        row_dict = dict(zip(columns, row))
        items.append(
            FeedbackListItem(
                id=str(row_dict["id"]),
                severity=row_dict.get("severity", ""),
                description=row_dict.get("description", ""),
                page_url=row_dict.get("page_url") or "",
                reporter_email=row_dict.get("reporter_email") or "anonymous",
                status=row_dict.get("status", "open"),
                created_at=str(row_dict.get("created_at", "")),
            )
        )

    return items


# ---------------------------------------------------------------------------
# GET /feedback/{id}  --  feedback detail (admin only)
# ---------------------------------------------------------------------------

@router.get("/feedback/{feedback_id}")
async def get_feedback(
    feedback_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
) -> dict:
    """
    Get detailed information about a single feedback entry.

    Admin only.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    try:
        result = db.execute(
            "SELECT * FROM feedback WHERE id = %s",
            (feedback_id,),
        )
        columns = [desc[0] for desc in result.description]
        row = result.fetchone()
    except Exception as e:
        logger.error(f"Failed to fetch feedback {feedback_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback.",
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found.",
        )

    row_dict = dict(zip(columns, row))

    # Deserialise JSON fields
    for json_field in ("recent_actions", "console_errors"):
        value = row_dict.get(json_field)
        if isinstance(value, str):
            try:
                row_dict[json_field] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass

    # Ensure datetime values are strings
    for key, value in row_dict.items():
        if isinstance(value, datetime):
            row_dict[key] = value.isoformat()

    return row_dict


# ---------------------------------------------------------------------------
# PATCH /feedback/{id}  --  update status / resolution (admin only)
# ---------------------------------------------------------------------------

@router.patch("/feedback/{feedback_id}")
async def update_feedback(
    feedback_id: str,
    body: FeedbackUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
) -> dict:
    """
    Update the status or resolution of a feedback entry.

    Admin only.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    # Verify the feedback exists
    try:
        result = db.execute(
            "SELECT id FROM feedback WHERE id = %s",
            (feedback_id,),
        )
        if result.fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to look up feedback {feedback_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to look up feedback.",
        )

    # Build dynamic SET clause
    set_parts: list[str] = []
    params: list = []

    if body.status is not None:
        set_parts.append("status = %s")
        params.append(body.status)

    if body.resolution is not None:
        set_parts.append("resolution = %s")
        params.append(body.resolution)

    if not set_parts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    set_parts.append("updated_at = %s")
    params.append(datetime.utcnow().isoformat())
    params.append(feedback_id)

    set_clause = ", ".join(set_parts)

    try:
        db.execute(
            f"UPDATE feedback SET {set_clause} WHERE id = %s",
            tuple(params),
        )
    except Exception as e:
        logger.error(f"Failed to update feedback {feedback_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update feedback.",
        )

    logger.info(f"Feedback {feedback_id} updated by admin {user.email}")

    return {"success": True, "feedback_id": feedback_id, "message": "Feedback updated."}
