"""Results retrieval endpoints."""

import json
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask
from loguru import logger

from backend_api.middleware.auth import AuthUser, get_current_user
from backend_api.middleware.rate_limit import limiter

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
    user: AuthUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """List all submission results with optional filtering."""
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

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

    if not user.is_admin:
        query += " AND s.user_id = ?"
        params.append(user.id)

    if dataset_id:
        query += " AND s.dataset_id = ?"
        params.append(int(dataset_id))
    if status:
        query += " AND s.status = ?"
        params.append(status)
    if algorithm_name:
        safe_name = algorithm_name.replace("%", "\\%").replace("_", "\\_")
        query += " AND LOWER(s.algorithm_name) LIKE LOWER(?)"
        params.append(f"%{safe_name}%")

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
    user: AuthUser = Depends(get_current_user),
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
            sr.processing_time_seconds,
            RANK() OVER (PARTITION BY s.dataset_id ORDER BY sr.f1_score DESC NULLS LAST) as rank
        FROM submissions s
        LEFT JOIN submission_results sr ON s.id = sr.submission_id
        WHERE s.id = ? AND (s.user_id = ? OR ? = TRUE)
        """,
        (int(submission_id), user.id, user.is_admin),
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    row_dict = dict(zip(columns, row))

    # Parse raw results for satellite breakdown and histogram data
    satellite_results = []
    ra_residual_histogram = None
    dec_residual_histogram = None
    position_error_histogram = None
    raw_results = row_dict.get("raw_results")
    if raw_results:
        try:
            parsed = json.loads(raw_results) if isinstance(raw_results, str) else raw_results
            if "per_satellite" in parsed:
                per_sat = parsed["per_satellite"]
                # per_satellite may be a dict (keyed by sat_id) or a list
                sat_list = per_sat if isinstance(per_sat, list) else []
                for sat_data in sat_list:
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
            # Extract histogram data if present
            ra_residual_histogram = parsed.get("ra_residual_histogram")
            dec_residual_histogram = parsed.get("dec_residual_histogram")
            position_error_histogram = parsed.get("position_error_histogram")
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse raw_results JSON for submission {submission_id}: {e}")

    # Extract rank from the window function in the main query
    rank = row_dict.get("rank")

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
        ra_residual_histogram=ra_residual_histogram,
        dec_residual_histogram=dec_residual_histogram,
        position_error_histogram=position_error_histogram,
        rank=rank,
        processing_time_seconds=row_dict.get("processing_time_seconds"),
    )


@router.get("/{submission_id}/metrics")
async def get_detailed_metrics(
    submission_id: str,
    user: AuthUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Get detailed metrics breakdown for a submission.

    Args:
        submission_id: The submission ID

    Returns:
        Per-satellite and per-track metrics breakdown
    """
    # Verify submission exists and user owns it
    submission = db.execute(
        "SELECT id, status FROM submissions WHERE id = ? AND (user_id = ? OR ? = TRUE)",
        (int(submission_id), user.id, user.is_admin),
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
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse detailed metrics JSON for submission {submission_id}: {e}")

    return {
        "submission_id": submission_id,
        "per_satellite_metrics": per_satellite_metrics,
        "per_track_metrics": per_track_metrics,
        "temporal_breakdown": temporal_breakdown,
    }


@router.get("/{submission_id}/visualization")
async def get_visualization_data(
    submission_id: str,
    user: AuthUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Get data for result visualizations.

    Args:
        submission_id: The submission ID

    Returns:
        Data formatted for orbit plots, error distributions, and temporal analysis
    """
    # Verify submission exists and user owns it
    submission = db.execute(
        "SELECT id, status FROM submissions WHERE id = ? AND (user_id = ? OR ? = TRUE)",
        (int(submission_id), user.id, user.is_admin),
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
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse visualization data JSON for submission {submission_id}: {e}")

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
    user: AuthUser = Depends(get_current_user),
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

    # Get full results with explicit columns to avoid name collisions
    result = db.execute(
        """
        SELECT
            s.id as submission_id,
            s.dataset_id,
            s.algorithm_name,
            s.version,
            s.description,
            s.status,
            s.created_at as submitted_at,
            s.completed_at,
            sr.id as result_id,
            sr.f1_score,
            sr.precision,
            sr.recall,
            sr.accuracy,
            sr.specificity,
            sr.true_positives,
            sr.false_positives,
            sr.true_negatives,
            sr.false_negatives,
            sr.position_rms_km,
            sr.velocity_rms_km_s,
            sr.mahalanobis_distance,
            sr.ra_residual_rms_arcsec,
            sr.dec_residual_rms_arcsec,
            sr.raw_results,
            sr.processing_time_seconds
        FROM submissions s
        LEFT JOIN submission_results sr ON s.id = sr.submission_id
        WHERE s.id = ? AND (s.user_id = ? OR ? = TRUE)
        """,
        (int(submission_id), user.id, user.is_admin),
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    row_dict = dict(zip(columns, row))

    # Convert non-JSON-serializable types
    import math
    from decimal import Decimal

    for key, value in row_dict.items():
        if hasattr(value, "isoformat"):
            row_dict[key] = value.isoformat()
        elif isinstance(value, Decimal):
            row_dict[key] = float(value)
        elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            row_dict[key] = None

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


@router.get("/{submission_id}/report")
@limiter.limit("5/minute")
async def generate_report(
    request: Request,
    submission_id: str,
    format: str = "pdf",
    user: AuthUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Generate a comprehensive evaluation report for a submission.

    Per Louis's specification: "Taking all of those metrics... we compile a
    comprehensive report. It's got, you know, graphs, it's got numbers, and it
    essentially gives an overall picture of how well the UCT processor performs."

    Args:
        submission_id: The submission ID
        format: Report format - 'pdf', 'html', or 'json'

    Returns:
        Report file in the requested format
    """
    # Get submission and results data
    result = db.execute(
        """
        SELECT
            s.id, s.dataset_id, s.algorithm_name, s.version, s.status, s.completed_at,
            sr.true_positives, sr.true_negatives, sr.false_positives, sr.false_negatives,
            sr.precision, sr.recall, sr.f1_score, sr.accuracy, sr.specificity,
            sr.position_rms_km, sr.velocity_rms_km_s, sr.mahalanobis_distance,
            sr.ra_residual_rms_arcsec, sr.dec_residual_rms_arcsec,
            sr.raw_results, sr.processing_time_seconds,
            d.name as dataset_name, d.orbital_regime, d.tier, d.legacy_code
        FROM submissions s
        LEFT JOIN submission_results sr ON s.id = sr.submission_id
        LEFT JOIN datasets d ON s.dataset_id = d.id
        WHERE s.id = ? AND (s.user_id = ? OR ? = TRUE)
        """,
        (int(submission_id), user.id, user.is_admin),
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    row_dict = dict(zip(columns, row))

    if row_dict.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail="Results not yet available. Submission status: " + str(row_dict.get("status")),
        )

    # Parse raw results for detailed data
    raw_results = {}
    if row_dict.get("raw_results"):
        try:
            raw_results = (
                json.loads(row_dict["raw_results"])
                if isinstance(row_dict["raw_results"], str)
                else row_dict["raw_results"]
            )
        except (json.JSONDecodeError, TypeError):
            pass

    # Build report data structure
    report_data = {
        "submission_id": str(row_dict["id"]),
        "dataset_id": str(row_dict["dataset_id"]),
        "dataset_name": row_dict.get("dataset_name", "Unknown"),
        "algorithm_name": row_dict["algorithm_name"],
        "algorithm_version": row_dict.get("version", "1.0"),
        "orbital_regime": row_dict.get("orbital_regime", "Unknown"),
        "tier": row_dict.get("tier", "Unknown"),
        "legacy_code": row_dict.get("legacy_code"),
        "completed_at": str(row_dict.get("completed_at", "")),
        "processing_time_seconds": row_dict.get("processing_time_seconds"),
        "binary_metrics": {
            "true_positives": row_dict.get("true_positives") or 0,
            "true_negatives": row_dict.get("true_negatives") or 0,
            "false_positives": row_dict.get("false_positives") or 0,
            "false_negatives": row_dict.get("false_negatives") or 0,
            "precision": float(row_dict.get("precision") or 0),
            "recall": float(row_dict.get("recall") or 0),
            "f1_score": float(row_dict.get("f1_score") or 0),
            "accuracy": float(row_dict.get("accuracy") or 0),
            "specificity": float(row_dict.get("specificity") or 0),
        },
        "state_metrics": {
            "position_rms_km": float(row_dict.get("position_rms_km") or 0),
            "velocity_rms_km_s": float(row_dict.get("velocity_rms_km_s") or 0),
            "mahalanobis_distance": row_dict.get("mahalanobis_distance"),
        },
        "residual_metrics": {
            "ra_residual_rms_arcsec": row_dict.get("ra_residual_rms_arcsec"),
            "dec_residual_rms_arcsec": row_dict.get("dec_residual_rms_arcsec"),
        },
        "per_satellite": raw_results.get("per_satellite", []),
        "state_results": raw_results.get("state_results", []),
        "residual_ref_results": raw_results.get("residual_ref_results", []),
        "residual_cand_results": raw_results.get("residual_cand_results", []),
    }

    if format == "json":
        return JSONResponse(
            content=report_data,
            headers={
                "Content-Disposition": f'attachment; filename="report_{submission_id}.json"'
            },
        )

    if format == "pdf":
        try:
            from uct_benchmark.evaluation.evaluationReport import generate_pdf_report

            # Generate PDF to temp file
            output_dir = Path(tempfile.mkdtemp())
            output_path = output_dir / f"report_{submission_id}.pdf"

            success = generate_pdf_report(report_data, str(output_path))

            if success and output_path.exists():
                return FileResponse(
                    path=str(output_path),
                    media_type="application/pdf",
                    filename=f"report_{submission_id}.pdf",
                    background=BackgroundTask(shutil.rmtree, output_dir, ignore_errors=True),
                )
            else:
                raise HTTPException(
                    status_code=500, detail="PDF generation failed. Check server logs."
                )
        except ImportError:
            logger.warning("PDF generation libraries not available, falling back to JSON")
            raise HTTPException(
                status_code=501,
                detail="PDF generation not available. Use format=json instead.",
            )

    if format == "html":
        try:
            from uct_benchmark.evaluation.evaluationReport import export_report_to_html

            output_dir = Path(tempfile.mkdtemp())
            output_path = output_dir / f"report_{submission_id}.html"

            export_report_to_html(report_data, str(output_path))

            if output_path.exists():
                return FileResponse(
                    path=str(output_path),
                    media_type="text/html",
                    filename=f"report_{submission_id}.html",
                    background=BackgroundTask(shutil.rmtree, output_dir, ignore_errors=True),
                )
            else:
                raise HTTPException(
                    status_code=500, detail="HTML report generation failed."
                )
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="HTML report generation not available. Use format=json instead.",
            )

    raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Use 'pdf', 'html', or 'json'.")
