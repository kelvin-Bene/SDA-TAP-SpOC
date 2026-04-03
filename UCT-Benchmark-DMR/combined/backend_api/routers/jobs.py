"""Job status endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from backend_api.jobs import JobStatus, get_job_manager
from backend_api.auth import CurrentUser
from backend_api.middleware.auth import get_current_user
from backend_api.models import JobResponse, JobStatusEnum

router = APIRouter()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str, user: CurrentUser = Depends(get_current_user)):
    """
    Get the status of a background job.

    Args:
        job_id: The unique job identifier

    Returns:
        Job status including progress, result, or error
    """
    job_manager = get_job_manager()
    job = job_manager.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Ownership check
    if not user.is_admin and job.metadata.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=job.id,
        job_type=job.job_type.value,
        status=JobStatusEnum(job.status.value),
        progress=job.progress,
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        metadata=job.metadata,
    )


@router.get("/")
async def list_jobs(
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    user: CurrentUser = Depends(get_current_user),
):
    """
    List background jobs with optional filtering.

    Requires authentication. Returns jobs owned by the current user (admins see all).

    Args:
        job_type: Filter by job type (dataset_generation, evaluation)
        status: Filter by status (pending, running, completed, failed)
        limit: Maximum number of jobs to return

    Returns:
        List of jobs matching the filters
    """
    logger.info(f"User {user.id} ({user.email}) listing jobs (type={job_type}, status={status})")
    limit = max(1, min(limit, 100))

    from backend_api.jobs import JobType

    job_manager = get_job_manager()

    # Convert string filters to enums with validation
    job_type_enum = None
    status_enum = None

    if job_type:
        try:
            job_type_enum = JobType(job_type)
        except ValueError:
            valid_types = [t.value for t in JobType]
            logger.warning(f"Invalid job_type filter: {job_type}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid job_type: '{job_type}'. Valid values: {valid_types}",
            )

    if status:
        try:
            status_enum = JobStatus(status)
        except ValueError:
            valid_statuses = [s.value for s in JobStatus]
            logger.warning(f"Invalid status filter: {status}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: '{status}'. Valid values: {valid_statuses}",
            )

    jobs = job_manager.list_jobs(
        job_type=job_type_enum,
        status=status_enum,
        limit=limit,
    )

    # Filter by ownership unless admin
    if not user.is_admin:
        jobs = [j for j in jobs if j.metadata.get("user_id") == user.id]

    return [
        JobResponse(
            id=job.id,
            job_type=job.job_type.value,
            status=JobStatusEnum(job.status.value),
            progress=job.progress,
            result=job.result,
            error=job.error,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            metadata=job.metadata,
        )
        for job in jobs
    ]
