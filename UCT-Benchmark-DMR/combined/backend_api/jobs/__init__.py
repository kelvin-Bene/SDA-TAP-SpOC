"""
Job queue system for managing background tasks.

Provides job tracking, status management, and async execution
for long-running operations like dataset generation and evaluation.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class JobStatus(str, Enum):
    """Status of a background job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    """Type of background job."""

    DATASET_GENERATION = "dataset_generation"
    EVALUATION = "evaluation"


@dataclass
class Job:
    """Represents a background job."""

    id: str
    job_type: JobType
    status: JobStatus = JobStatus.PENDING
    progress: int = 0  # 0-100
    stage: Optional[str] = None  # Current stage description for progress display
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for API response."""
        return {
            "id": self.id,
            "job_type": self.job_type.value,
            "status": self.status.value,
            "progress": self.progress,
            "stage": self.stage,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


class JobManager:
    """
    Manages background jobs with in-memory storage.

    Thread-safe job creation, updates, and queries.
    Can be migrated to Redis or a database for persistence.
    """

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create_job(self, job_type: JobType, metadata: Optional[Dict[str, Any]] = None) -> Job:
        """
        Create a new job and add it to the manager.

        Args:
            job_type: Type of the job
            metadata: Optional metadata for the job

        Returns:
            The created Job instance
        """
        job_id = str(uuid.uuid4())
        job = Job(id=job_id, job_type=job_type, metadata=metadata or {})

        with self._lock:
            self._jobs[job_id] = job

        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a job by its ID.

        Args:
            job_id: The job's unique identifier

        Returns:
            The Job instance or None if not found
        """
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        stage: Optional[str] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> Optional[Job]:
        """
        Update a job's status and progress.

        Args:
            job_id: The job's unique identifier
            status: New status (optional)
            progress: New progress value 0-100 (optional)
            stage: Current stage description (optional)
            result: Result data (optional)
            error: Error message (optional)

        Returns:
            The updated Job instance or None if not found
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None

            if status is not None:
                job.status = status
                if status == JobStatus.RUNNING and job.started_at is None:
                    job.started_at = datetime.utcnow()
                elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    job.completed_at = datetime.utcnow()

            if progress is not None:
                job.progress = min(100, max(0, progress))

            if stage is not None:
                job.stage = stage

            if result is not None:
                job.result = result

            if error is not None:
                job.error = error

            return job

    def start_job(self, job_id: str) -> Optional[Job]:
        """Mark a job as running."""
        return self.update_job(job_id, status=JobStatus.RUNNING)

    def complete_job(self, job_id: str, result: Any = None) -> Optional[Job]:
        """Mark a job as completed with an optional result."""
        return self.update_job(job_id, status=JobStatus.COMPLETED, progress=100, result=result)

    def fail_job(self, job_id: str, error: str) -> Optional[Job]:
        """Mark a job as failed with an error message."""
        return self.update_job(job_id, status=JobStatus.FAILED, error=error)

    def list_jobs(
        self,
        job_type: Optional[JobType] = None,
        status: Optional[JobStatus] = None,
        limit: int = 100,
    ) -> List[Job]:
        """
        List jobs with optional filtering.

        Args:
            job_type: Filter by job type (optional)
            status: Filter by status (optional)
            limit: Maximum number of jobs to return

        Returns:
            List of matching Job instances
        """
        with self._lock:
            jobs = list(self._jobs.values())

        # Apply filters
        if job_type is not None:
            jobs = [j for j in jobs if j.job_type == job_type]
        if status is not None:
            jobs = [j for j in jobs if j.status == status]

        # Sort by creation time (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        return jobs[:limit]

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Remove jobs older than the specified age.

        Args:
            max_age_hours: Maximum age in hours for jobs to keep

        Returns:
            Number of jobs removed
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        removed = 0

        with self._lock:
            to_remove = [
                job_id
                for job_id, job in self._jobs.items()
                if job.created_at < cutoff and job.status in (JobStatus.COMPLETED, JobStatus.FAILED)
            ]
            for job_id in to_remove:
                del self._jobs[job_id]
                removed += 1

        return removed


# Global job manager instance (singleton)
_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """
    Get the global job manager instance.

    Returns:
        JobManager: The singleton job manager
    """
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager


def init_job_manager() -> JobManager:
    """Initialize the global job manager."""
    global _job_manager
    _job_manager = JobManager()
    return _job_manager
