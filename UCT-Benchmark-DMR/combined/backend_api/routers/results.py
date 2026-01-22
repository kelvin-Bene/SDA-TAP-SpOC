"""Results retrieval endpoints."""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class MetricScore(BaseModel):
    """Individual metric score."""
    name: str
    value: float
    unit: Optional[str] = None
    description: Optional[str] = None


class SubmissionResult(BaseModel):
    """Complete results for a submission."""
    submission_id: str
    dataset_id: str
    algorithm_name: str
    status: str
    completed_at: Optional[datetime] = None
    overall_score: Optional[float] = None
    metrics: List[MetricScore]
    confusion_matrix: Optional[Dict] = None
    processing_time_seconds: Optional[float] = None


# Mock results
_mock_results = {
    "sub-001": SubmissionResult(
        submission_id="sub-001",
        dataset_id="ds-001",
        algorithm_name="UCTP-v1",
        status="completed",
        completed_at=datetime(2025, 1, 16, 15, 45, 0),
        overall_score=0.85,
        metrics=[
            MetricScore(name="True Positive Rate", value=0.92, description="Correct associations"),
            MetricScore(name="False Positive Rate", value=0.08, description="Incorrect associations"),
            MetricScore(name="Mean Orbit Error", value=1.23, unit="km", description="Average orbital error"),
            MetricScore(name="Processing Time", value=45.2, unit="seconds"),
        ],
        confusion_matrix={
            "true_positives": 1150,
            "false_positives": 100,
            "true_negatives": 980,
            "false_negatives": 50,
        },
        processing_time_seconds=45.2,
    ),
}


@router.get("/{submission_id}", response_model=SubmissionResult)
async def get_results(submission_id: str):
    """Get results for a specific submission."""
    if submission_id in _mock_results:
        return _mock_results[submission_id]

    # Check if submission exists but is still processing
    if submission_id == "sub-002":
        return SubmissionResult(
            submission_id="sub-002",
            dataset_id="ds-001",
            algorithm_name="Custom-IOD",
            status="processing",
            completed_at=None,
            overall_score=None,
            metrics=[],
            processing_time_seconds=None,
        )

    raise HTTPException(status_code=404, detail="Results not found")


@router.get("/{submission_id}/metrics")
async def get_detailed_metrics(submission_id: str):
    """Get detailed metrics breakdown for a submission (stub)."""
    if submission_id not in _mock_results and submission_id != "sub-002":
        raise HTTPException(status_code=404, detail="Submission not found")

    return {
        "submission_id": submission_id,
        "per_satellite_metrics": [],
        "per_track_metrics": [],
        "temporal_breakdown": [],
    }


@router.get("/{submission_id}/visualization")
async def get_visualization_data(submission_id: str):
    """Get data for result visualizations (stub)."""
    return {
        "submission_id": submission_id,
        "orbit_plots": [],
        "error_distribution": [],
        "temporal_analysis": [],
    }
