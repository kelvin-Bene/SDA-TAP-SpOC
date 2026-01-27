"""Submission handling endpoints."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend_api.database import get_db
from backend_api.jobs.workers import submit_evaluation
from backend_api.models import (
    SubmissionDetail,
    SubmissionStatus,
    SubmissionSummary,
)
from uct_benchmark.database.connection import DatabaseManager

router = APIRouter()

# Directory for storing uploaded submission files
UPLOADS_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _row_to_submission_summary(row: tuple, columns: list) -> SubmissionSummary:
    """Convert a database row to SubmissionSummary model."""
    row_dict = dict(zip(columns, row))

    return SubmissionSummary(
        id=str(row_dict["id"]),
        dataset_id=str(row_dict["dataset_id"]),
        dataset_name=row_dict.get("dataset_name"),
        algorithm_name=row_dict["algorithm_name"],
        version=row_dict.get("version", "1.0"),
        status=SubmissionStatus(row_dict.get("status", "queued")),
        created_at=row_dict["created_at"] or datetime.utcnow(),
        completed_at=row_dict.get("completed_at"),
        score=row_dict.get("f1_score"),
        job_id=row_dict.get("job_id"),
        queue_position=None,  # Could calculate from pending submissions
    )


@router.get("/", response_model=List[SubmissionSummary])
async def list_submissions(
    dataset_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: DatabaseManager = Depends(get_db),
):
    """
    List all submissions with optional filtering.

    Args:
        dataset_id: Filter by dataset ID
        status: Filter by status (queued, validating, processing, completed, failed)
        limit: Maximum number of submissions to return
        offset: Number of submissions to skip

    Returns:
        List of submission summaries
    """
    # Build query with optional filters and join for dataset name and score
    query = """
        SELECT
            s.*,
            d.name as dataset_name,
            sr.f1_score
        FROM submissions s
        LEFT JOIN datasets d ON s.dataset_id = d.id
        LEFT JOIN submission_results sr ON s.id = sr.submission_id
        WHERE 1=1
    """
    params = []

    if dataset_id:
        query += " AND s.dataset_id = ?"
        params.append(int(dataset_id))

    if status:
        query += " AND s.status = ?"
        params.append(status)

    query += " ORDER BY s.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    result = db.execute(query, tuple(params))
    columns = [desc[0] for desc in result.description]
    rows = result.fetchall()

    return [_row_to_submission_summary(row, columns) for row in rows]


@router.get("/{submission_id}", response_model=SubmissionDetail)
async def get_submission(
    submission_id: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get details of a specific submission.

    Args:
        submission_id: The submission ID

    Returns:
        Detailed submission information
    """
    result = db.execute(
        """
        SELECT
            s.*,
            d.name as dataset_name,
            sr.f1_score
        FROM submissions s
        LEFT JOIN datasets d ON s.dataset_id = d.id
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

    return SubmissionDetail(
        id=str(row_dict["id"]),
        dataset_id=str(row_dict["dataset_id"]),
        dataset_name=row_dict.get("dataset_name"),
        algorithm_name=row_dict["algorithm_name"],
        version=row_dict.get("version", "1.0"),
        status=SubmissionStatus(row_dict.get("status", "queued")),
        created_at=row_dict["created_at"] or datetime.utcnow(),
        completed_at=row_dict.get("completed_at"),
        score=row_dict.get("f1_score"),
        job_id=row_dict.get("job_id"),
        file_path=row_dict.get("file_path"),
        error_message=row_dict.get("error_message"),
    )


@router.post("/", response_model=SubmissionSummary, status_code=201)
async def create_submission(
    dataset_id: str = Form(...),
    algorithm_name: str = Form(...),
    version: str = Form(default="1.0"),
    description: Optional[str] = Form(default=None),
    file: UploadFile = File(...),
    db: DatabaseManager = Depends(get_db),
):
    """
    Create a new submission with file upload.

    This endpoint accepts a multipart form with the submission metadata
    and the results file (JSON format).

    Args:
        dataset_id: The dataset ID to evaluate against
        algorithm_name: Name of the algorithm
        version: Version string
        description: Optional description
        file: The results file (JSON)

    Returns:
        The created submission summary with job_id for tracking progress
    """
    # Verify dataset exists and is available
    dataset = db.execute(
        "SELECT id, status FROM datasets WHERE id = ?", (int(dataset_id),)
    ).fetchone()

    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset[1] != "available":
        raise HTTPException(status_code=400, detail="Dataset is not available for submissions")

    # Save uploaded file
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix if file.filename else ".json"
    file_path = UPLOADS_DIR / f"{file_id}{file_extension}"

    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    # Create submission record using RETURNING to get the ID
    result = db.execute(
        """
        INSERT INTO submissions (
            dataset_id, algorithm_name, version, description, file_path, status, created_at
        ) VALUES (?, ?, ?, ?, ?, 'queued', CURRENT_TIMESTAMP)
        RETURNING id
        """,
        (
            int(dataset_id),
            algorithm_name,
            version,
            description,
            str(file_path),
        ),
    )
    submission_id = result.fetchone()[0]

    # Submit evaluation job
    job = submit_evaluation(
        submission_id=submission_id,
        dataset_id=int(dataset_id),
        file_path=str(file_path),
    )

    # Update submission with job_id
    db.execute(
        "UPDATE submissions SET job_id = ? WHERE id = ?",
        (job.id, submission_id),
    )

    return SubmissionSummary(
        id=str(submission_id),
        dataset_id=dataset_id,
        dataset_name=None,
        algorithm_name=algorithm_name,
        version=version,
        status=SubmissionStatus.QUEUED,
        created_at=datetime.utcnow(),
        completed_at=None,
        score=None,
        job_id=job.id,
    )


@router.post("/{submission_id}/results")
async def upload_results(
    submission_id: str,
    file: UploadFile = File(...),
    db: DatabaseManager = Depends(get_db),
):
    """
    Upload or re-upload results file for an existing submission.

    Args:
        submission_id: The submission ID
        file: The results file (JSON)

    Returns:
        Upload status and job_id for tracking
    """
    # Verify submission exists
    submission = db.execute(
        "SELECT id, dataset_id, status FROM submissions WHERE id = ?", (int(submission_id),)
    ).fetchone()

    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Don't allow re-upload if currently processing
    if submission[2] in ("validating", "processing"):
        raise HTTPException(
            status_code=400, detail="Cannot upload results while submission is being processed"
        )

    # Save uploaded file
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix if file.filename else ".json"
    file_path = UPLOADS_DIR / f"{file_id}{file_extension}"

    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    # Update submission with new file path and reset status
    db.execute(
        """
        UPDATE submissions
        SET file_path = ?, status = 'queued', completed_at = NULL, error_message = NULL
        WHERE id = ?
        """,
        (str(file_path), int(submission_id)),
    )

    # Submit new evaluation job
    job = submit_evaluation(
        submission_id=int(submission_id),
        dataset_id=submission[1],
        file_path=str(file_path),
    )

    # Update submission with job_id
    db.execute(
        "UPDATE submissions SET job_id = ? WHERE id = ?",
        (job.id, int(submission_id)),
    )

    return {
        "submission_id": submission_id,
        "filename": file.filename,
        "status": "uploaded",
        "message": "Results file received, processing started",
        "job_id": job.id,
    }
