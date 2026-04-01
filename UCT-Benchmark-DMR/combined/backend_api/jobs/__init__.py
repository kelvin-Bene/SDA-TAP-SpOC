"""
Job queue system for managing background tasks.

Provides job tracking, status management, and async execution
for long-running operations like dataset generation and evaluation.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
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
                    job.started_at = datetime.now(timezone.utc)
                elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    job.completed_at = datetime.now(timezone.utc)

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

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
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


class DatabaseJobManager(JobManager):
    """
    Job manager that mirrors state to the database jobs table.

    In-memory dict remains primary for performance; DB is backup
    for crash recovery. On startup, recovers incomplete jobs from DB.
    """

    def __init__(self, db: Any = None):
        super().__init__()
        self._db = db

    def set_db(self, db: Any) -> None:
        """Set or update the database reference."""
        self._db = db
        self._recover_from_db()

    def _recover_from_db(self) -> None:
        """Load incomplete jobs from database on startup."""
        if self._db is None:
            return
        try:
            import json as _json

            result = self._db.execute(
                "SELECT id, job_type, status, progress, result, error, metadata, "
                "created_at, started_at, completed_at FROM jobs "
                "WHERE status IN ('pending', 'running') "
                "ORDER BY created_at DESC LIMIT 100"
            )
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()
            recovered = 0
            with self._lock:
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    job_id = row_dict["id"]
                    if job_id in self._jobs:
                        continue  # Already tracked in memory

                    # Parse metadata and result from JSON
                    metadata = {}
                    if row_dict.get("metadata"):
                        try:
                            raw = row_dict["metadata"]
                            metadata = _json.loads(raw) if isinstance(raw, str) else (raw or {})
                        except (ValueError, TypeError):
                            pass

                    job_result = None
                    if row_dict.get("result"):
                        try:
                            raw = row_dict["result"]
                            job_result = _json.loads(raw) if isinstance(raw, str) else raw
                        except (ValueError, TypeError):
                            pass

                    job = Job(
                        id=job_id,
                        job_type=JobType(row_dict["job_type"]),
                        status=JobStatus(row_dict.get("status", "pending")),
                        progress=row_dict.get("progress") or 0,
                        result=job_result,
                        error=row_dict.get("error"),
                        created_at=row_dict.get("created_at") or datetime.now(timezone.utc),
                        started_at=row_dict.get("started_at"),
                        completed_at=row_dict.get("completed_at"),
                        metadata=metadata,
                    )
                    self._jobs[job_id] = job
                    recovered += 1

            if recovered > 0:
                from loguru import logger
                logger.info(f"Recovered {recovered} incomplete jobs from database")
        except Exception as e:
            from loguru import logger
            logger.warning(f"Job recovery from database failed (non-critical): {e}")

    def _persist_job(self, job: Job) -> None:
        """Write job state to database (fire-and-forget)."""
        if self._db is None:
            return
        try:
            import json as _json

            self._db.execute(
                """
                INSERT INTO jobs (id, job_type, status, progress, result, error, metadata,
                                  created_at, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    progress = EXCLUDED.progress,
                    result = EXCLUDED.result,
                    error = EXCLUDED.error,
                    started_at = EXCLUDED.started_at,
                    completed_at = EXCLUDED.completed_at
                """,
                (
                    job.id,
                    job.job_type.value,
                    job.status.value,
                    job.progress,
                    _json.dumps(job.result) if job.result is not None else None,
                    job.error,
                    _json.dumps(job.metadata) if job.metadata else None,
                    job.created_at.isoformat() if job.created_at else None,
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                ),
            )
        except Exception:
            pass  # DB persistence is best-effort; in-memory is primary

    def create_job(self, job_type: JobType, metadata: Optional[Dict[str, Any]] = None) -> Job:
        job = super().create_job(job_type, metadata)
        self._persist_job(job)
        return job

    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        stage: Optional[str] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> Optional[Job]:
        job = super().update_job(job_id, status, progress, stage, result, error)
        if job is not None:
            self._persist_job(job)
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job from memory, falling back to database."""
        job = super().get_job(job_id)
        if job is not None:
            return job

        # Fall back to database lookup
        if self._db is None:
            return None
        try:
            import json as _json

            result = self._db.execute(
                "SELECT id, job_type, status, progress, result, error, metadata, "
                "created_at, started_at, completed_at FROM jobs WHERE id = ?",
                (job_id,),
            )
            columns = [desc[0] for desc in result.description]
            row = result.fetchone()
            if row is None:
                return None

            row_dict = dict(zip(columns, row))

            metadata = {}
            if row_dict.get("metadata"):
                try:
                    raw = row_dict["metadata"]
                    metadata = _json.loads(raw) if isinstance(raw, str) else (raw or {})
                except (ValueError, TypeError):
                    pass

            job_result = None
            if row_dict.get("result"):
                try:
                    raw = row_dict["result"]
                    job_result = _json.loads(raw) if isinstance(raw, str) else raw
                except (ValueError, TypeError):
                    pass

            job = Job(
                id=job_id,
                job_type=JobType(row_dict["job_type"]),
                status=JobStatus(row_dict.get("status", "pending")),
                progress=row_dict.get("progress") or 0,
                result=job_result,
                error=row_dict.get("error"),
                created_at=row_dict.get("created_at") or datetime.now(timezone.utc),
                started_at=row_dict.get("started_at"),
                completed_at=row_dict.get("completed_at"),
                metadata=metadata,
            )
            # Cache in memory
            with self._lock:
                self._jobs[job_id] = job
            return job
        except Exception:
            return None


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
        _job_manager = DatabaseJobManager()
    return _job_manager


def init_job_manager(db: Any = None) -> JobManager:
    """Initialize the global job manager, optionally with DB persistence."""
    global _job_manager
    if db is not None:
        _job_manager = DatabaseJobManager(db)
    else:
        _job_manager = DatabaseJobManager()
    return _job_manager
