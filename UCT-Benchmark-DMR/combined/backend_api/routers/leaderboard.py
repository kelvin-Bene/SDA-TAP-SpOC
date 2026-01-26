"""Leaderboard endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends

from backend_api.database import get_db
from backend_api.models import LeaderboardEntry, LeaderboardResponse
from uct_benchmark.database.connection import DatabaseManager

router = APIRouter()


@router.get("/", response_model=LeaderboardResponse)
async def get_leaderboard(
    dataset_id: Optional[str] = None,
    regime: Optional[str] = None,
    tier: Optional[str] = None,
    period: Optional[str] = None,  # all, month, week
    limit: int = 50,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get the current leaderboard.

    Args:
        dataset_id: Filter by specific dataset
        regime: Filter by orbital regime (LEO, MEO, GEO, HEO)
        tier: Filter by complexity tier (T1, T2, T3, T4)
        period: Time period filter (all, month, week)
        limit: Maximum number of entries to return

    Returns:
        Leaderboard with ranked entries sorted by F1 score
    """
    # Build query for completed submissions with results
    query = """
        SELECT
            s.id as submission_id,
            s.algorithm_name,
            s.version,
            s.dataset_id,
            s.completed_at,
            d.name as dataset_name,
            d.orbital_regime,
            d.tier,
            sr.f1_score,
            sr.precision,
            sr.recall,
            sr.position_rms_km
        FROM submissions s
        JOIN submission_results sr ON s.id = sr.submission_id
        JOIN datasets d ON s.dataset_id = d.id
        WHERE s.status = 'completed'
          AND sr.f1_score IS NOT NULL
    """
    params = []

    if dataset_id:
        query += " AND s.dataset_id = ?"
        params.append(int(dataset_id))

    if regime:
        query += " AND d.orbital_regime = ?"
        params.append(regime)

    if tier:
        query += " AND d.tier = ?"
        params.append(tier)

    if period == "week":
        query += " AND s.completed_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'"
    elif period == "month":
        query += " AND s.completed_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'"

    # Order by F1 score descending and limit
    query += " ORDER BY sr.f1_score DESC LIMIT ?"
    params.append(limit)

    result = db.execute(query, tuple(params))
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    # Build leaderboard entries with rank
    entries = []
    for rank, row in enumerate(rows, start=1):
        row_dict = dict(zip(columns, row))
        entries.append(
            LeaderboardEntry(
                rank=rank,
                algorithm_name=row_dict["algorithm_name"],
                team=None,  # Would need user/team table
                version=row_dict.get("version", "1.0"),
                f1_score=float(row_dict.get("f1_score") or 0),
                precision=float(row_dict.get("precision") or 0),
                recall=float(row_dict.get("recall") or 0),
                position_rms_km=float(row_dict.get("position_rms_km") or 0),
                submission_id=str(row_dict["submission_id"]),
                submitted_at=row_dict.get("completed_at") or datetime.utcnow(),
                is_current_user=False,  # Would need auth context
            )
        )

    # Get dataset info for response
    dataset_name = None
    if dataset_id and entries:
        dataset_name = entries[0].algorithm_name  # Placeholder - would get from dataset

        ds_result = db.execute(
            "SELECT name FROM datasets WHERE id = ?", (int(dataset_id),)
        ).fetchone()
        if ds_result:
            dataset_name = ds_result[0]

    return LeaderboardResponse(
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        last_updated=datetime.utcnow(),
        total_entries=len(entries),
        entries=entries,
    )


@router.get("/history")
async def get_leaderboard_history(
    dataset_id: Optional[str] = None,
    days: int = 30,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get leaderboard history over time.

    Args:
        dataset_id: Filter by specific dataset
        days: Number of days of history

    Returns:
        Historical ranking data for trend visualization
    """
    # Get completed submissions over time
    query = f"""
        SELECT
            DATE(s.completed_at) as date,
            s.algorithm_name,
            MAX(sr.f1_score) as best_f1
        FROM submissions s
        JOIN submission_results sr ON s.id = sr.submission_id
        WHERE s.status = 'completed'
          AND s.completed_at >= CURRENT_TIMESTAMP - INTERVAL '{days} days'
    """
    params = []

    if dataset_id:
        query += " AND s.dataset_id = ?"
        params.append(int(dataset_id))

    query += " GROUP BY DATE(s.completed_at), s.algorithm_name ORDER BY date"

    result = db.execute(query, tuple(params))
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    history = []
    for row in rows:
        row_dict = dict(zip(columns, row))
        history.append(
            {
                "date": str(row_dict["date"]),
                "algorithm_name": row_dict["algorithm_name"],
                "best_f1": float(row_dict.get("best_f1") or 0),
            }
        )

    return {
        "dataset_id": dataset_id,
        "history": history,
        "period_days": days,
    }


@router.get("/statistics")
async def get_leaderboard_statistics(
    dataset_id: Optional[str] = None,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get aggregate leaderboard statistics.

    Args:
        dataset_id: Filter by specific dataset

    Returns:
        Aggregate stats including total submissions, unique algorithms, averages
    """
    # Build base query
    base_query = """
        FROM submissions s
        JOIN submission_results sr ON s.id = sr.submission_id
        WHERE s.status = 'completed'
    """
    params = []

    if dataset_id:
        base_query += " AND s.dataset_id = ?"
        params.append(int(dataset_id))

    # Get counts and averages
    stats_query = f"""
        SELECT
            COUNT(*) as total_submissions,
            COUNT(DISTINCT s.algorithm_name) as unique_algorithms,
            AVG(sr.f1_score) as average_score,
            MAX(sr.f1_score) as best_score,
            MIN(sr.f1_score) as worst_score
        {base_query}
    """

    result = db.execute(stats_query, tuple(params))
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        return {
            "dataset_id": dataset_id,
            "total_submissions": 0,
            "unique_algorithms": 0,
            "average_score": 0,
            "best_score": 0,
            "worst_score": 0,
            "submission_trend": "stable",
        }

    row_dict = dict(zip(columns, row))

    # Determine trend (compare last week to previous week)
    trend_query = f"""
        SELECT
            SUM(CASE WHEN s.completed_at >= CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 1 ELSE 0 END) as this_week,
            SUM(CASE WHEN s.completed_at >= CURRENT_TIMESTAMP - INTERVAL '14 days'
                 AND s.completed_at < CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 1 ELSE 0 END) as last_week
        {base_query}
    """

    trend_result = db.execute(trend_query, tuple(params))
    trend_row = trend_result.fetchone()

    trend = "stable"
    if trend_row:
        this_week = trend_row[0] or 0
        last_week = trend_row[1] or 0
        if this_week > last_week * 1.2:
            trend = "increasing"
        elif this_week < last_week * 0.8:
            trend = "decreasing"

    return {
        "dataset_id": dataset_id,
        "total_submissions": row_dict.get("total_submissions") or 0,
        "unique_algorithms": row_dict.get("unique_algorithms") or 0,
        "average_score": round(float(row_dict.get("average_score") or 0), 4),
        "best_score": round(float(row_dict.get("best_score") or 0), 4),
        "worst_score": round(float(row_dict.get("worst_score") or 0), 4),
        "submission_trend": trend,
    }
