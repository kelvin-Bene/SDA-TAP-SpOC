"""Submission handling endpoints."""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from loguru import logger

from backend_api.database import get_db
from backend_api.jobs.workers import submit_evaluation
from backend_api.auth import CurrentUser
from backend_api.middleware.auth import get_current_user
from backend_api.middleware.rate_limit import limiter
from backend_api.models import (
    SubmissionDetail,
    SubmissionStatus,
    SubmissionSummary,
)
from uct_benchmark.database.connection import DatabaseManager

router = APIRouter()


# =============================================================================
# UCTP Output Schema Validation (per Louis's Benchmarking Documentation)
# =============================================================================

# Required fields for state-vector UCTP output
UCTP_SV_REQUIRED_FIELDS = {
    "sourcedData": list,       # List of observation IDs grouped by this orbit
    "epoch": str,              # Epoch of the state vector (ISO datetime)
    "xpos": (int, float),      # Position X [km]
    "ypos": (int, float),      # Position Y [km]
    "zpos": (int, float),      # Position Z [km]
    "xvel": (int, float),      # Velocity X [km/s]
    "yvel": (int, float),      # Velocity Y [km/s]
    "zvel": (int, float),      # Velocity Z [km/s]
}

# Optional but documented fields for state-vector output
UCTP_SV_OPTIONAL_FIELDS = {
    "idStateVector": str,            # Unique alphanumeric identifier (per Louis's spec)
    "sourcedDataTypes": list,        # Type of each sourced observation (e.g., "EO")
    "referenceFrame": str,           # Reference frame (e.g., "EME2000", "J2000")
    "covReferenceFrame": str,        # Covariance reference frame
    "cov": list,                     # 21 lower-triangular covariance elements
    "classificationMarking": str,    # Organization label (e.g., "U//LSAS")
}

# Required fields for TLE UCTP output
UCTP_TLE_REQUIRED_FIELDS = {
    "sourcedData": list,
    "line1": str,
    "line2": str,
}

# Optional but documented fields for TLE output
UCTP_TLE_OPTIONAL_FIELDS = {
    "idElset": str,                  # Unique TLE identifier
    "sourcedDataTypes": list,        # Type of each sourced item (e.g., "ELSET")
    "epoch": str,                    # TLE epoch
    "meanMotion": (int, float),
    "eccentricity": (int, float),
    "inclination": (int, float),
    "raan": (int, float),
    "argOfPerigee": (int, float),
    "meanAnomaly": (int, float),
    "bStar": (int, float),
    "semiMajorAxis": (int, float),
    "period": (int, float),
}


def validate_uctp_output(data: Any) -> Tuple[bool, List[str]]:
    """
    Validate UCTP output against the documented schema.

    Accepts both state-vector and TLE formats.

    Args:
        data: Parsed JSON data (list of orbit records)

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors: List[str] = []

    if not isinstance(data, list):
        return False, ["UCTP output must be a JSON array of orbit records"]

    if len(data) == 0:
        return False, ["UCTP output is empty (no orbit records)"]

    # Detect format from first record
    first_record = data[0]
    if not isinstance(first_record, dict):
        return False, ["Each orbit record must be a JSON object"]

    is_tle = "line1" in first_record and "line2" in first_record
    required = UCTP_TLE_REQUIRED_FIELDS if is_tle else UCTP_SV_REQUIRED_FIELDS
    format_name = "TLE" if is_tle else "state-vector"

    # Common field name aliases that map to canonical UCTP field names
    aliases_map = {
        "sourcedData": ["grouped_ops", "sourced_data"],
        "xpos": ["X", "x", "posX"],
        "ypos": ["Y", "y", "posY"],
        "zpos": ["Z", "z", "posZ"],
        "xvel": ["VX", "vx", "velX", "Xdot"],
        "yvel": ["VY", "vy", "velY", "Ydot"],
        "zvel": ["VZ", "vz", "velZ", "Zdot"],
    }

    for i, record in enumerate(data):
        if not isinstance(record, dict):
            errors.append(f"Record {i}: expected JSON object, got {type(record).__name__}")
            continue

        # Check required fields (also accepting known aliases)
        for field, expected_type in required.items():
            # Resolve the actual value: prefer canonical name, then try aliases
            value = record.get(field)
            resolved_name = field
            if value is None and field not in record:
                for alias in aliases_map.get(field, []):
                    if alias in record:
                        value = record[alias]
                        resolved_name = alias
                        break
                else:
                    errors.append(f"Record {i}: missing required field '{field}'")
                    continue

            # Type-check the resolved value
            if not isinstance(value, expected_type):
                # Format expected type for readability
                if isinstance(expected_type, tuple):
                    type_label = "/".join(t.__name__ for t in expected_type)
                else:
                    type_label = expected_type.__name__
                errors.append(
                    f"Record {i}: field '{resolved_name}' expected {type_label}, "
                    f"got {type(value).__name__}"
                )

        # Validate covariance if present (21 lower-triangular elements)
        if not is_tle and "cov" in record:
            cov = record["cov"]
            if isinstance(cov, list) and len(cov) != 21:
                errors.append(
                    f"Record {i}: 'cov' must have exactly 21 lower-triangular elements, "
                    f"got {len(cov)}"
                )

        # Cap error reporting to first 20 errors
        if len(errors) >= 20:
            errors.append(f"... and possibly more errors (checked {i+1}/{len(data)} records)")
            break

    is_valid = len(errors) == 0
    if is_valid:
        logger.info(f"UCTP schema validation passed: {len(data)} {format_name} records")

    return is_valid, errors

# Directory for storing uploaded submission files
UPLOADS_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Maximum upload size: 50 MB
MAX_UPLOAD_SIZE = 50 * 1024 * 1024


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
        created_at=row_dict["created_at"] or datetime.now(timezone.utc),
        completed_at=row_dict.get("completed_at"),
        score=row_dict.get("f1_score"),
        job_id=row_dict.get("job_id"),
        queue_position=None,  # Could calculate from pending submissions
        rank=row_dict.get("rank"),
    )


@router.get("/", response_model=List[SubmissionSummary])
async def list_submissions(
    dataset_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    List submissions for the current user, with optional filtering.

    Args:
        dataset_id: Filter by dataset ID
        status: Filter by status (queued, validating, processing, completed, failed)
        limit: Maximum number of submissions to return
        offset: Number of submissions to skip

    Returns:
        List of submission summaries
    """
    # Clamp pagination
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    # Build query with optional filters, join for dataset name, score, and rank.
    # RANK() partitions by dataset so each submission is ranked against others
    # on the same dataset, ordered by F1-score descending.
    # Filter by user_id to prevent IDOR (users only see their own submissions).
    query = """
        SELECT
            s.*,
            d.name as dataset_name,
            sr.f1_score,
            RANK() OVER (PARTITION BY s.dataset_id ORDER BY sr.f1_score DESC NULLS LAST) as rank
        FROM submissions s
        LEFT JOIN datasets d ON s.dataset_id = d.id
        LEFT JOIN submission_results sr ON s.id = sr.submission_id
        WHERE s.user_id = ?
    """
    params: list = [user.id]

    if dataset_id:
        query += " AND s.dataset_id = ?"
        params.append(int(dataset_id))

    if status:
        query += " AND s.status = ?"
        params.append(status)

    query += " ORDER BY s.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        result = db.execute(query, tuple(params))
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
    except Exception as e:
        logger.error(f"Failed to list submissions: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    return [_row_to_submission_summary(row, columns) for row in rows]


@router.get("/{submission_id}", response_model=SubmissionDetail)
async def get_submission(
    submission_id: str,
    user: CurrentUser = Depends(get_current_user),
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
        WHERE s.id = ? AND (s.user_id = ? OR ? = TRUE)
        """,
        (int(submission_id), user.id, user.is_admin),
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    row_dict = dict(zip(columns, row))

    # Sanitize file_path to only return the filename, not internal server paths
    raw_file_path = row_dict.get("file_path")
    sanitized_file_path = Path(raw_file_path).name if raw_file_path else None

    return SubmissionDetail(
        id=str(row_dict["id"]),
        dataset_id=str(row_dict["dataset_id"]),
        dataset_name=row_dict.get("dataset_name"),
        algorithm_name=row_dict["algorithm_name"],
        version=row_dict.get("version", "1.0"),
        status=SubmissionStatus(row_dict.get("status", "queued")),
        created_at=row_dict["created_at"] or datetime.now(timezone.utc),
        completed_at=row_dict.get("completed_at"),
        score=row_dict.get("f1_score"),
        job_id=row_dict.get("job_id"),
        file_path=sanitized_file_path,
        error_message=row_dict.get("error_message"),
    )


@router.post("/", response_model=SubmissionSummary, status_code=201)
@limiter.limit("10/minute")
async def create_submission(
    request: Request,
    dataset_id: str = Form(...),
    algorithm_name: str = Form(...),
    version: str = Form(default="1.0"),
    description: Optional[str] = Form(default=None),
    classification_marking: Optional[str] = Form(default=None),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
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

    # Validate content type
    allowed_content_types = ["application/json", "text/json", "application/octet-stream"]
    if file.content_type and file.content_type not in allowed_content_types:
        logger.warning(f"Rejected upload with content_type: {file.content_type}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected JSON, got: {file.content_type}",
        )

    # Save uploaded file and validate JSON
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix.lower() if file.filename else ".json"
    if file_extension not in (".json",):
        file_extension = ".json"
    file_path = UPLOADS_DIR / f"{file_id}{file_extension}"

    try:
        # Read only up to MAX+1 bytes to detect oversized uploads without OOM
        contents = await file.read(MAX_UPLOAD_SIZE + 1)

        # Check file size
        if len(contents) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({len(contents) / (1024*1024):.1f} MB). "
                       f"Maximum upload size is {MAX_UPLOAD_SIZE / (1024*1024):.0f} MB.",
            )

        # Quick sanity check: file content should start with JSON structure
        stripped = contents.lstrip()
        if stripped and stripped[0:1] not in (b"[", b"{"):
            raise HTTPException(
                status_code=400,
                detail="File content does not appear to be JSON (must start with [ or {).",
            )

        # Validate that the content is valid JSON
        try:
            parsed_data = json.loads(contents)
        except json.JSONDecodeError:
            logger.warning("Rejected upload with invalid JSON")
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON file. Ensure the upload is well-formed JSON.",
            )

        # Validate UCTP output schema (per Louis's Benchmarking Documentation)
        is_valid, schema_errors = validate_uctp_output(parsed_data)
        if not is_valid:
            logger.warning(f"UCTP schema validation failed: {schema_errors[:5]}")
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "UCTP output does not match expected schema",
                    "errors": schema_errors,
                    "hint": (
                        "Expected fields: sourcedData, epoch, xpos, ypos, zpos, "
                        "xvel, yvel, zvel (state-vector) OR sourcedData, line1, line2 (TLE)"
                    ),
                },
            )

        with open(file_path, "wb") as f:
            f.write(contents)

        # S17: Compute SHA-256 hash for data integrity verification
        file_hash = hashlib.sha256(contents).hexdigest()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # Create submission record using RETURNING to get the ID
    try:
        result = db.execute(
            """
            INSERT INTO submissions (
                dataset_id, algorithm_name, version, description,
                classification_marking, file_path, status, user_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            (
                int(dataset_id),
                algorithm_name,
                version,
                description,
                classification_marking,
                str(file_path),
                user.id,
            ),
        )
        submission_id = result.fetchone()[0]
    except Exception as e:
        # Clean up the uploaded file if DB insert fails
        file_path.unlink(missing_ok=True)
        logger.error(f"Failed to insert submission record: {e}")
        raise HTTPException(status_code=500, detail="Failed to create submission record")

    # S17: Log file hash for audit trail
    logger.info(f"Submission {submission_id}: file_hash=sha256:{file_hash}")

    # Submit evaluation job
    job = submit_evaluation(
        submission_id=submission_id,
        dataset_id=int(dataset_id),
        file_path=str(file_path),
        user_id=user.id,
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
        created_at=datetime.now(timezone.utc),
        completed_at=None,
        score=None,
        job_id=job.id,
    )


@router.post("/{submission_id}/results")
async def upload_results(
    submission_id: str,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
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
        "SELECT id, dataset_id, status, user_id FROM submissions WHERE id = ?", (int(submission_id),)
    ).fetchone()

    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Ownership check: only the submitter (or an admin) may re-upload results
    if submission[3] is not None and submission[3] != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to modify this submission")

    # Don't allow re-upload if currently processing
    if submission[2] in ("validating", "processing"):
        raise HTTPException(
            status_code=400, detail="Cannot upload results while submission is being processed"
        )

    # Validate content type
    allowed_content_types = ["application/json", "text/json", "application/octet-stream"]
    if file.content_type and file.content_type not in allowed_content_types:
        logger.warning(f"Rejected upload with content_type: {file.content_type}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Expected JSON, got: {file.content_type}",
        )

    # Save uploaded file and validate JSON
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix.lower() if file.filename else ".json"
    if file_extension not in (".json",):
        file_extension = ".json"
    file_path = UPLOADS_DIR / f"{file_id}{file_extension}"

    try:
        # Read only up to MAX+1 bytes to detect oversized uploads without OOM
        contents = await file.read(MAX_UPLOAD_SIZE + 1)

        # Check file size
        if len(contents) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({len(contents) / (1024*1024):.1f} MB). "
                       f"Maximum upload size is {MAX_UPLOAD_SIZE / (1024*1024):.0f} MB.",
            )

        # Validate that the content is valid JSON
        try:
            parsed_data = json.loads(contents)
        except json.JSONDecodeError as e:
            logger.warning(f"Rejected re-upload with invalid JSON: {e}")
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON file. Please verify the file contains valid JSON and try again.",
            )

        # Validate UCTP output schema
        is_valid, schema_errors = validate_uctp_output(parsed_data)
        if not is_valid:
            logger.warning(f"UCTP schema validation failed on re-upload: {schema_errors[:5]}")
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "UCTP output does not match expected schema",
                    "errors": schema_errors,
                    "hint": (
                        "Expected fields: sourcedData, epoch, xpos, ypos, zpos, "
                        "xvel, yvel, zvel (state-vector) OR sourcedData, line1, line2 (TLE)"
                    ),
                },
            )

        with open(file_path, "wb") as f:
            f.write(contents)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save uploaded results file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

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
        user_id=user.id,
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
