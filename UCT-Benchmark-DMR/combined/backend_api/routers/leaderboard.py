"""Leaderboard endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class LeaderboardEntry(BaseModel):
    """Single entry on the leaderboard."""
    rank: int
    algorithm_name: str
    team_name: Optional[str] = None
    overall_score: float
    submission_count: int
    best_submission_date: datetime
    metrics: dict


class LeaderboardResponse(BaseModel):
    """Complete leaderboard response."""
    dataset_id: str
    dataset_name: str
    last_updated: datetime
    entries: List[LeaderboardEntry]


# Mock leaderboard data
_mock_leaderboard = LeaderboardResponse(
    dataset_id="ds-001",
    dataset_name="LEO Mixed Fleet",
    last_updated=datetime(2025, 1, 18, 12, 0, 0),
    entries=[
        LeaderboardEntry(
            rank=1,
            algorithm_name="UCTP-v2",
            team_name="Space Analytics Lab",
            overall_score=0.92,
            submission_count=5,
            best_submission_date=datetime(2025, 1, 17, 16, 30, 0),
            metrics={"tpr": 0.95, "fpr": 0.05, "orbit_error_km": 0.8},
        ),
        LeaderboardEntry(
            rank=2,
            algorithm_name="UCTP-v1",
            team_name="Benchmark Team",
            overall_score=0.85,
            submission_count=3,
            best_submission_date=datetime(2025, 1, 16, 14, 30, 0),
            metrics={"tpr": 0.92, "fpr": 0.08, "orbit_error_km": 1.23},
        ),
        LeaderboardEntry(
            rank=3,
            algorithm_name="Neural-OD",
            team_name="ML Orbit Lab",
            overall_score=0.78,
            submission_count=2,
            best_submission_date=datetime(2025, 1, 15, 10, 0, 0),
            metrics={"tpr": 0.85, "fpr": 0.12, "orbit_error_km": 2.1},
        ),
    ],
)


@router.get("/", response_model=LeaderboardResponse)
async def get_leaderboard(
    dataset_id: Optional[str] = None,
    limit: int = 10,
):
    """Get the current leaderboard."""
    response = _mock_leaderboard
    if limit:
        response = LeaderboardResponse(
            **{**_mock_leaderboard.model_dump(), "entries": _mock_leaderboard.entries[:limit]}
        )
    return response


@router.get("/history")
async def get_leaderboard_history(
    dataset_id: Optional[str] = None,
    days: int = 30,
):
    """Get leaderboard history over time (stub)."""
    return {
        "dataset_id": dataset_id or "ds-001",
        "history": [],
        "period_days": days,
    }


@router.get("/statistics")
async def get_leaderboard_statistics(dataset_id: Optional[str] = None):
    """Get aggregate leaderboard statistics (stub)."""
    return {
        "dataset_id": dataset_id or "ds-001",
        "total_submissions": 10,
        "unique_algorithms": 5,
        "average_score": 0.82,
        "best_score": 0.92,
        "submission_trend": "increasing",
    }
