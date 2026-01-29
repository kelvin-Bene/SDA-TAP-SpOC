"""Results retrieval endpoints."""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from backend_api.database import get_db
from backend_api.models import (
    ResultSummary,
    SatelliteResult,
    SubmissionResults,
    SubmissionStatus,
)
from uct_benchmark.database.connection import DatabaseManager

router = APIRouter()


def _row_to_result_summary(row: tuple, columns: list) -> ResultSummary:
    """Convert database row to ResultSummary."""
    row_dict = dict(zip(columns, row))
    return ResultSummary(
        submission_id=str(row_dict["submission_id"]),
        dataset_id=str(row_dict["dataset_id"]),
        dataset_name=row_dict.get("dataset_name"),
        algorithm_name=row_dict["algorithm_name"],
        version=row_dict.get("version", "1.0"),
        status=SubmissionStatus(row_dict.get("status", "completed")),
        completed_at=row_dict.get("completed_at"),
        f1_score=float(row_dict.get("f1_score") or 0),
        precision=float(row_dict.get("precision") or 0),
        recall=float(row_dict.get("recall") or 0),
        position_rms_km=float(row_dict.get("position_rms_km") or 0),
        rank=row_dict.get("rank"),
    )


@router.get("/", response_model=List[ResultSummary])
async def list_results(
    dataset_id: Optional[str] = None,
    status: Optional[str] = None,
    algorithm_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: DatabaseManager = Depends(get_db),
):
    """List all submission results with optional filtering."""
    query = """
        SELECT
            s.id as submission_id,
            s.dataset_id,
            d.name as dataset_name,
            s.algorithm_name,
            s.version,
            s.status,
            s.completed_at,
            sr.f1_score,
            sr.precision,
            sr.recall,
            sr.position_rms_km,
            RANK() OVER (PARTITION BY s.dataset_id ORDER BY sr.f1_score DESC) as rank
        FROM submissions s
        INNER JOIN submission_results sr ON s.id = sr.submission_id
        LEFT JOIN datasets d ON s.dataset_id = d.id
        WHERE 1=1
    """
    params = []

    if dataset_id:
        query += " AND s.dataset_id = ?"
        params.append(int(dataset_id))
    if status:
        query += " AND s.status = ?"
        params.append(status)
    if algorithm_name:
        query += " AND s.algorithm_name ILIKE ?"
        params.append(f"%{algorithm_name}%")

    query += " ORDER BY s.completed_at DESC, sr.f1_score DESC"
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    result = db.execute(query, tuple(params))
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    return [_row_to_result_summary(row, columns) for row in rows]


@router.get("/{submission_id}", response_model=SubmissionResults)
async def get_results(
    submission_id: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get complete results for a submission.

    Args:
        submission_id: The submission ID

    Returns:
        Complete results including binary metrics, state metrics, and per-satellite breakdown
    """
    # Get submission and results
    result = db.execute(
        """
        SELECT
            s.id,
            s.dataset_id,
            s.algorithm_name,
            s.status,
            s.completed_at,
            sr.true_positives,
            sr.false_positives,
            sr.false_negatives,
            sr.precision,
            sr.recall,
            sr.f1_score,
            sr.position_rms_km,
            sr.velocity_rms_km_s,
            sr.mahalanobis_distance,
            sr.ra_residual_rms_arcsec,
            sr.dec_residual_rms_arcsec,
            sr.raw_results,
            sr.processing_time_seconds
        FROM submissions s
        LEFT JOIN submission_results sr ON s.id = sr.submission_id
        WHERE s.id = ?
        """,
        (int(submission_id),),
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    row_dict = dict(zip(columns, row))

    # Parse raw results for satellite breakdown
    satellite_results = []
    raw_results = row_dict.get("raw_results")
    if raw_results:
        try:
            parsed = json.loads(raw_results) if isinstance(raw_results, str) else raw_results
            if "per_satellite" in parsed:
                for sat_data in parsed["per_satellite"]:
                    satellite_results.append(
                        SatelliteResult(
                            satellite_id=str(sat_data.get("satellite_id", "")),
                            status=sat_data.get("status", "FN"),
                            observations_used=sat_data.get("observations_used", 0),
                            total_observations=sat_data.get("total_observations", 0),
                            position_error_km=sat_data.get("position_error_km"),
                            velocity_error_km_s=sat_data.get("velocity_error_km_s"),
                            confidence=sat_data.get("confidence"),
                        )
                    )
        except (json.JSONDecodeError, TypeError):
            pass

    # Calculate rank (optional - based on F1 score for same dataset)
    rank = None
    if row_dict.get("f1_score") is not None:
        rank_result = db.execute(
            """
            SELECT COUNT(*) + 1
            FROM submission_results sr2
            JOIN submissions s2 ON sr2.submission_id = s2.id
            WHERE s2.dataset_id = (SELECT dataset_id FROM submissions WHERE id = ?)
              AND sr2.f1_score > ?
            """,
            (int(submission_id), row_dict["f1_score"]),
        ).fetchone()
        rank = rank_result[0] if rank_result else None

    return SubmissionResults(
        submission_id=str(row_dict["id"]),
        dataset_id=str(row_dict["dataset_id"]),
        algorithm_name=row_dict["algorithm_name"],
        status=SubmissionStatus(row_dict.get("status", "queued")),
        completed_at=row_dict.get("completed_at"),
        true_positives=row_dict.get("true_positives") or 0,
        false_positives=row_dict.get("false_positives") or 0,
        false_negatives=row_dict.get("false_negatives") or 0,
        precision=float(row_dict.get("precision") or 0),
        recall=float(row_dict.get("recall") or 0),
        f1_score=float(row_dict.get("f1_score") or 0),
        position_rms_km=float(row_dict.get("position_rms_km") or 0),
        velocity_rms_km_s=float(row_dict.get("velocity_rms_km_s") or 0),
        mahalanobis_distance=row_dict.get("mahalanobis_distance"),
        ra_residual_rms_arcsec=row_dict.get("ra_residual_rms_arcsec"),
        dec_residual_rms_arcsec=row_dict.get("dec_residual_rms_arcsec"),
        satellite_results=satellite_results,
        rank=rank,
        processing_time_seconds=row_dict.get("processing_time_seconds"),
    )


@router.get("/{submission_id}/metrics")
async def get_detailed_metrics(
    submission_id: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get detailed metrics breakdown for a submission.

    Args:
        submission_id: The submission ID

    Returns:
        Per-satellite and per-track metrics breakdown
    """
    # Verify submission exists
    submission = db.execute(
        "SELECT id, status FROM submissions WHERE id = ?", (int(submission_id),)
    ).fetchone()

    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Get raw results for detailed breakdown
    result = db.execute(
        "SELECT raw_results FROM submission_results WHERE submission_id = ?", (int(submission_id),)
    ).fetchone()

    per_satellite_metrics = []
    per_track_metrics = []
    temporal_breakdown = []

    if result and result[0]:
        try:
            raw_results = json.loads(result[0]) if isinstance(result[0], str) else result[0]

            per_satellite_metrics = raw_results.get("per_satellite", [])
            per_track_metrics = raw_results.get("per_track", [])
            temporal_breakdown = raw_results.get("temporal_breakdown", [])
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "submission_id": submission_id,
        "per_satellite_metrics": per_satellite_metrics,
        "per_track_metrics": per_track_metrics,
        "temporal_breakdown": temporal_breakdown,
    }


@router.get("/{submission_id}/visualization")
async def get_visualization_data(
    submission_id: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get data for result visualizations.

    Args:
        submission_id: The submission ID

    Returns:
        Data formatted for orbit plots, error distributions, and temporal analysis
    """
    # Verify submission exists
    submission = db.execute(
        "SELECT id, status FROM submissions WHERE id = ?", (int(submission_id),)
    ).fetchone()

    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Get raw results for visualization data
    result = db.execute(
        "SELECT raw_results FROM submission_results WHERE submission_id = ?", (int(submission_id),)
    ).fetchone()

    orbit_plots = []
    error_distribution = []
    temporal_analysis = []

    if result and result[0]:
        try:
            raw_results = json.loads(result[0]) if isinstance(result[0], str) else result[0]

            # Extract visualization data if available
            orbit_plots = raw_results.get("orbit_plots", [])
            error_distribution = raw_results.get("error_distribution", [])
            temporal_analysis = raw_results.get("temporal_analysis", [])
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "submission_id": submission_id,
        "orbit_plots": orbit_plots,
        "error_distribution": error_distribution,
        "temporal_analysis": temporal_analysis,
    }


@router.get("/{submission_id}/export")
async def export_results(
    submission_id: str,
    format: str = "json",
    db: DatabaseManager = Depends(get_db),
):
    """
    Export results in various formats.

    Args:
        submission_id: The submission ID
        format: Export format (json, csv)

    Returns:
        Results in the requested format
    """
    from fastapi.responses import JSONResponse

    # Get full results
    result = db.execute(
        """
        SELECT
            s.*,
            sr.*
        FROM submissions s
        LEFT JOIN submission_results sr ON s.id = sr.submission_id
        WHERE s.id = ?
        """,
        (int(submission_id),),
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    row_dict = dict(zip(columns, row))

    # Convert non-JSON-serializable types
    from decimal import Decimal

    for key, value in row_dict.items():
        if hasattr(value, "isoformat"):
            row_dict[key] = value.isoformat()
        elif isinstance(value, Decimal):
            row_dict[key] = float(value)

    if format == "json":
        return JSONResponse(
            content=row_dict,
            headers={"Content-Disposition": f'attachment; filename="results_{submission_id}.json"'},
        )
    elif format == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=row_dict.keys())
        writer.writeheader()
        writer.writerow(row_dict)

        from fastapi.responses import StreamingResponse

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="results_{submission_id}.csv"'},
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
