"""
Regression tests for QA_PROD_RUN_2026-04-17 L4.

DatabaseJobManager.list_jobs must merge in-memory jobs with rows from the
`jobs` table so historical jobs that have aged out of the in-memory dict
remain visible to /api/v1/jobs operators. Without this, prod ops see only
the live-in-memory subset and lose forensic visibility on failed runs.

These tests exercise the override at backend_api/jobs/__init__.py.

Standalone file (not test_db_job_manager.py) so we don't inherit the
existing fixtures in that file, which target a different DatabaseJobManager
API (pre-existing tech debt unrelated to this change).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from backend_api.jobs import (
    DatabaseJobManager,
    Job,
    JobStatus,
    JobType,
)


def _make_db_row(job_id: str, job_type: str, status: str, created_at: datetime):
    """Minimal jobs-table row tuple matching the SELECT order in list_jobs."""
    return (
        job_id,
        job_type,
        status,
        0,        # progress
        None,     # result
        None,     # error
        None,     # metadata
        created_at,
        None,     # started_at
        None,     # completed_at
    )


def _fake_db_with_rows(rows):
    """Build a minimal MagicMock db.execute(...) returning the given rows."""
    columns = [
        "id", "job_type", "status", "progress", "result", "error",
        "metadata", "created_at", "started_at", "completed_at",
    ]
    fake_db = MagicMock()
    fake_result = MagicMock()
    fake_result.description = [(c,) for c in columns]
    fake_result.fetchall.return_value = rows
    fake_db.execute.return_value = fake_result
    return fake_db


class TestListJobsDbMerge:
    """L4: list_jobs surfaces DB-persisted jobs that aren't in memory."""

    def test_returns_db_only_job_when_memory_empty(self):
        """A job persisted to DB (and absent from memory) must still appear."""
        now = datetime.now(timezone.utc) - timedelta(hours=2)
        rows = [_make_db_row("evicted-job-1", "evaluation", "failed", now)]
        fake_db = _fake_db_with_rows(rows)

        mgr = DatabaseJobManager(db=fake_db)
        # Memory is empty — only DB rows should surface.

        jobs = mgr.list_jobs()

        assert len(jobs) == 1
        assert jobs[0].id == "evicted-job-1"
        assert jobs[0].status == JobStatus.FAILED
        assert jobs[0].job_type == JobType.EVALUATION

    def test_dedupes_in_memory_over_db(self):
        """If the same job id is both in memory and the DB, memory wins."""
        now = datetime.now(timezone.utc)
        # In-memory job
        mgr = DatabaseJobManager(db=_fake_db_with_rows([
            _make_db_row("dup-id", "evaluation", "failed", now - timedelta(hours=1)),
        ]))
        # Manually inject an in-memory job with the same id but RUNNING status
        # to prove the in-memory copy takes precedence over the stale DB row.
        live_job = Job(
            id="dup-id",
            job_type=JobType.EVALUATION,
            status=JobStatus.RUNNING,
            created_at=now,
        )
        mgr._jobs["dup-id"] = live_job

        jobs = mgr.list_jobs()

        assert len(jobs) == 1
        assert jobs[0].id == "dup-id"
        # Memory's RUNNING wins over DB's FAILED.
        assert jobs[0].status == JobStatus.RUNNING

    def test_filters_by_status_apply_to_db_rows(self):
        """status= filter should be honoured in the DB SELECT, not just memory."""
        now = datetime.now(timezone.utc)
        rows = [_make_db_row("only-failed", "evaluation", "failed", now)]
        fake_db = _fake_db_with_rows(rows)
        mgr = DatabaseJobManager(db=fake_db)

        jobs = mgr.list_jobs(status=JobStatus.FAILED)

        # The fake db returns the row regardless; we're verifying it ends up
        # in the merged result and the status= filter parameter was passed.
        assert len(jobs) == 1
        assert jobs[0].status == JobStatus.FAILED
        # Confirm the executed SQL referenced the status filter.
        executed_sql = fake_db.execute.call_args[0][0]
        assert "status = ?" in executed_sql

    def test_db_failure_falls_back_to_memory_only(self):
        """If the DB query raises, list_jobs must still return memory jobs."""
        fake_db = MagicMock()
        fake_db.execute.side_effect = RuntimeError("connection lost")

        mgr = DatabaseJobManager(db=fake_db)
        live_job = Job(
            id="mem-job",
            job_type=JobType.DATASET_GENERATION,
            status=JobStatus.RUNNING,
        )
        mgr._jobs["mem-job"] = live_job

        # Should NOT raise — falls back to memory subset.
        jobs = mgr.list_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "mem-job"

    def test_no_db_configured_returns_memory_only(self):
        """DatabaseJobManager(db=None) behaves like the in-memory base class."""
        mgr = DatabaseJobManager(db=None)
        live_job = Job(
            id="mem-only",
            job_type=JobType.EVALUATION,
            status=JobStatus.PENDING,
        )
        mgr._jobs["mem-only"] = live_job

        jobs = mgr.list_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "mem-only"
