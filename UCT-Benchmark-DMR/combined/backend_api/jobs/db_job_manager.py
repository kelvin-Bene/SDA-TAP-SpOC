"""Database-backed job manager for PostgreSQL persistence.

Stores jobs in the ``jobs`` table so they survive server restarts.
Uses the same API as the in-memory ``JobManager`` for drop-in
replacement controlled by the DB_BACKEND feature flag.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from backend_api.jobs import Job, JobStatus, JobType


class DatabaseJobManager:
    """Persists jobs in the PostgreSQL jobs table.

    Provides the same public API as ``JobManager`` so it can be
    used as a drop-in replacement.
    """

    def _get_db(self):
        from backend_api.database import get_db
        return get_db()

    def create_job(self, job_type: JobType, metadata: Optional[Dict[str, Any]] = None) -> Job:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        meta_json = json.dumps(metadata) if metadata else "{}"

        db = self._get_db()
        db.execute(
            """
            INSERT INTO jobs (job_id, job_type, status, progress, stage, result, error_message,
                              created_at, started_at, completed_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, job_type.value, JobStatus.PENDING.value, 0, None, None, None,
             now.isoformat(), None, None, meta_json),
        )

        return Job(
            id=job_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            progress=0,
            created_at=now,
            metadata=metadata or {},
        )

    def get_job(self, job_id: str) -> Optional[Job]:
        db = self._get_db()
        row = db.execute(
            "SELECT job_id, job_type, status, progress, stage, result, error_message, "
            "created_at, started_at, completed_at, metadata FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_job(row)

    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        stage: Optional[str] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> Optional[Job]:
        job = self.get_job(job_id)
        if job is None:
            return None

        updates = []
        params = []

        if status is not None:
            updates.append("status = ?")
            params.append(status.value)
            if status == JobStatus.RUNNING and job.started_at is None:
                updates.append("started_at = ?")
                params.append(datetime.now(timezone.utc).isoformat())
            elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
                updates.append("completed_at = ?")
                params.append(datetime.now(timezone.utc).isoformat())

        if progress is not None:
            updates.append("progress = ?")
            params.append(min(100, max(0, progress)))

        if stage is not None:
            updates.append("stage = ?")
            params.append(stage)

        if result is not None:
            updates.append("result = ?")
            params.append(json.dumps(result) if not isinstance(result, str) else result)

        if error is not None:
            updates.append("error_message = ?")
            params.append(error)

        if not updates:
            return job

        params.append(job_id)
        db = self._get_db()
        db.execute(
            f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?",
            tuple(params),
        )

        return self.get_job(job_id)

    def start_job(self, job_id: str) -> Optional[Job]:
        return self.update_job(job_id, status=JobStatus.RUNNING)

    def complete_job(self, job_id: str, result: Any = None) -> Optional[Job]:
        return self.update_job(job_id, status=JobStatus.COMPLETED, progress=100, result=result)

    def fail_job(self, job_id: str, error: str) -> Optional[Job]:
        return self.update_job(job_id, status=JobStatus.FAILED, error=error)

    def list_jobs(
        self,
        job_type: Optional[JobType] = None,
        status: Optional[JobStatus] = None,
        limit: int = 100,
    ) -> List[Job]:
        clauses = []
        params = []

        if job_type is not None:
            clauses.append("job_type = ?")
            params.append(job_type.value)
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)

        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        params.append(limit)
        db = self._get_db()
        rows = db.execute(
            f"SELECT job_id, job_type, status, progress, stage, result, error_message, "
            f"created_at, started_at, completed_at, metadata "
            f"FROM jobs {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        ).fetchall()

        return [self._row_to_job(row) for row in rows]

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        db = self._get_db()
        result = db.execute(
            "DELETE FROM jobs WHERE created_at < ? AND status IN (?, ?)",
            (cutoff.isoformat(), JobStatus.COMPLETED.value, JobStatus.FAILED.value),
        )
        return getattr(result, "rowcount", 0)

    @staticmethod
    def _row_to_job(row: tuple) -> Job:
        (job_id, job_type, status, progress, stage, result,
         error_message, created_at, started_at, completed_at, metadata) = row

        def _parse_dt(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            try:
                return datetime.fromisoformat(str(val))
            except (ValueError, TypeError):
                return None

        def _parse_json(val):
            if val is None:
                return {}
            if isinstance(val, dict):
                return val
            try:
                return json.loads(str(val))
            except (json.JSONDecodeError, TypeError):
                return {}

        return Job(
            id=job_id,
            job_type=JobType(job_type),
            status=JobStatus(status),
            progress=progress or 0,
            stage=stage,
            result=_parse_json(result) if result else None,
            error=error_message,
            created_at=_parse_dt(created_at) or datetime.now(timezone.utc),
            started_at=_parse_dt(started_at),
            completed_at=_parse_dt(completed_at),
            metadata=_parse_json(metadata),
        )
