"""Submission handling endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

router = APIRouter()


class SubmissionSummary(BaseModel):
    """Summary of a submission."""
    id: str
    dataset_id: str
    algorithm_name: str
    submitted_at: datetime
    status: str
    score: Optional[float] = None


class SubmissionCreate(BaseModel):
    """Request to create a new submission."""
    dataset_id: str
    algorithm_name: str
    description: Optional[str] = None


# Mock data
_mock_submissions = [
    SubmissionSummary(
        id="sub-001",
        dataset_id="ds-001",
        algorithm_name="UCTP-v1",
        submitted_at=datetime(2025, 1, 16, 14, 30, 0),
        status="completed",
        score=0.85,
    ),
    SubmissionSummary(
        id="sub-002",
        dataset_id="ds-001",
        algorithm_name="Custom-IOD",
        submitted_at=datetime(2025, 1, 17, 9, 15, 0),
        status="processing",
        score=None,
    ),
]


@router.get("/", response_model=List[SubmissionSummary])
async def list_submissions(
    dataset_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
):
    """List all submissions."""
    submissions = _mock_submissions
    if dataset_id:
        submissions = [s for s in submissions if s.dataset_id == dataset_id]
    if status:
        submissions = [s for s in submissions if s.status == status]
    return submissions[offset : offset + limit]


@router.get("/{submission_id}", response_model=SubmissionSummary)
async def get_submission(submission_id: str):
    """Get details of a specific submission."""
    for sub in _mock_submissions:
        if sub.id == submission_id:
            return sub
    raise HTTPException(status_code=404, detail="Submission not found")


@router.post("/", response_model=SubmissionSummary)
async def create_submission(request: SubmissionCreate):
    """Create a new submission (stub)."""
    new_submission = SubmissionSummary(
        id=f"sub-{len(_mock_submissions) + 1:03d}",
        dataset_id=request.dataset_id,
        algorithm_name=request.algorithm_name,
        submitted_at=datetime.utcnow(),
        status="queued",
        score=None,
    )
    return new_submission


@router.post("/{submission_id}/results")
async def upload_results(
    submission_id: str,
    file: UploadFile = File(...),
):
    """Upload results file for a submission (stub)."""
    return {
        "submission_id": submission_id,
        "filename": file.filename,
        "status": "uploaded",
        "message": "Results file received, processing started",
    }
