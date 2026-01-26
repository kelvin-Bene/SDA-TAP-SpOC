"""Job status endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from backend_api.jobs import JobStatus, get_job_manager
from backend_api.models import JobResponse, JobStatusEnum

router = APIRouter()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
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
):
    """
    List background jobs with optional filtering.

    Args:
        job_type: Filter by job type (dataset_generation, evaluation)
        status: Filter by status (pending, running, completed, failed)
        limit: Maximum number of jobs to return

    Returns:
        List of jobs matching the filters
    """
    from backend_api.jobs import JobType

    job_manager = get_job_manager()

    # Convert string filters to enums
    job_type_enum = None
    status_enum = None

    if job_type:
        try:
            job_type_enum = JobType(job_type)
        except ValueError:
            pass

    if status:
        try:
            status_enum = JobStatus(status)
        except ValueError:
            pass

    jobs = job_manager.list_jobs(
        job_type=job_type_enum,
        status=status_enum,
        limit=limit,
    )

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
