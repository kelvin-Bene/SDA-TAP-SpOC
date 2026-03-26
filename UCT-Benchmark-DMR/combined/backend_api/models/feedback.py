"""Pydantic models for the feedback/bug report system."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """Schema for submitting new feedback or bug reports."""

    description: str = Field(..., min_length=1, max_length=5000)
    severity: Literal["bug", "suggestion", "question"]
    screenshot_base64: Optional[str] = Field(None, max_length=3_000_000)
    page_url: Optional[str] = Field(None, max_length=2048)
    user_agent: Optional[str] = Field(None, max_length=500)
    viewport: Optional[str] = Field(None, max_length=100)
    recent_actions: Optional[list[dict]] = Field(None, max_length=30)
    console_errors: Optional[list[str]] = Field(None, max_length=10)
    sentry_event_id: Optional[str] = Field(None, max_length=200)


class FeedbackResponse(BaseModel):
    """Response returned after submitting feedback."""

    success: bool
    feedback_id: str
    message: str


class FeedbackListItem(BaseModel):
    """Summary item for feedback list views."""

    id: str
    severity: str
    description: str
    page_url: str
    reporter_email: str
    status: str
    created_at: str


class FeedbackUpdate(BaseModel):
    """Schema for updating feedback status/resolution (admin only)."""

    status: Optional[str] = Field(None, max_length=50)
    resolution: Optional[str] = Field(None, max_length=5000)
