"""
Tests for the DatabaseJobManager.

Verifies that the database-backed job manager correctly:
- Creates, retrieves, and updates jobs via SQL
- Persists jobs across manager re-instantiation
- Filters jobs by type and status
- Matches the interface of the in-memory JobManager
"""

import json
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from backend_api.jobs import Job, JobStatus, JobType
from backend_api.jobs.db_job_manager import DatabaseJobManager


# =============================================================================
# FIXTURES
# =============================================================================


class FakeResultSet:
    """Simulates a database result set for testing."""

    def __init__(self, rows=None):
        self._rows = rows or []
        self._index = 0

    def fetchone(self):
        if self._rows:
            return self._rows[0]
        return None

    def fetchall(self):
        return self._rows


class FakeDB:
    """
    In-memory fake database that stores jobs in a dictionary.
    Supports the execute() interface used by DatabaseJobManager.
    """

    def __init__(self):
        self._jobs = {}

    def execute(self, sql, params=()):
        sql_upper = sql.strip().upper()

        if sql_upper.startswith("INSERT INTO JOBS"):
            # Parse INSERT params: (id, job_type, status, progress, stage,
            #                       result, error, created_at, started_at,
            #                       completed_at, metadata)
            self._jobs[params[0]] = list(params)
            return FakeResultSet()

        elif sql_upper.startswith("SELECT") and "WHERE JOB_ID =" in sql_upper:
            job_id = params[0]
            row = self._jobs.get(job_id)
            return FakeResultSet([tuple(row)] if row else [])

        elif sql_upper.startswith("SELECT") and "FROM JOBS" in sql_upper:
            # list_jobs query
            rows = list(self._jobs.values())

            # Apply WHERE filters
            if "WHERE" in sql_upper:
                filtered = rows
                param_idx = 0

                # Parse simple WHERE clauses
                if "JOB_TYPE = ?" in sql_upper:
                    job_type_val = params[param_idx]
                    param_idx += 1
                    filtered = [r for r in filtered if r[1] == job_type_val]

                if "STATUS = ?" in sql_upper:
                    status_val = params[param_idx]
                    param_idx += 1
                    filtered = [r for r in filtered if r[2] == status_val]

                rows = filtered

            # Sort by created_at DESC
            rows.sort(key=lambda r: r[7] if r[7] else "", reverse=True)

            # Apply LIMIT (last param)
            limit = params[-1]
            rows = rows[:limit]

            return FakeResultSet([tuple(r) for r in rows])

        elif sql_upper.startswith("UPDATE JOBS"):
            # Parse dynamic UPDATE
            # Find the job_id (last param)
            job_id = params[-1]
            row = self._jobs.get(job_id)
            if row is None:
                return FakeResultSet()

            # Parse SET clauses from the SQL
            set_part = sql.split("SET")[1].split("WHERE")[0].strip()
            set_fields = [f.strip().split("=")[0].strip().lower() for f in set_part.split(",")]

            field_map = {
                "status": 2,
                "progress": 3,
                "stage": 4,
                "result": 5,
                "error_message": 6,
                "started_at": 8,
                "completed_at": 9,
            }

            param_idx = 0
            for field_name in set_fields:
                if field_name in field_map:
                    row[field_map[field_name]] = params[param_idx]
                param_idx += 1

            return FakeResultSet()

        elif sql_upper.startswith("SELECT COUNT"):
            # cleanup_old_jobs count query
            return FakeResultSet([(0,)])

        elif sql_upper.startswith("DELETE"):
            return FakeResultSet()

        return FakeResultSet()


@pytest.fixture
def fake_db():
    """Create a fake in-memory database."""
    return FakeDB()


@pytest.fixture
def manager(fake_db):
    """Create a DatabaseJobManager with the fake database."""
    with patch.object(DatabaseJobManager, '_get_db', return_value=fake_db):
        yield DatabaseJobManager()


# =============================================================================
# CREATE JOB TESTS
# =============================================================================


class TestCreateJob:
    """Tests for DatabaseJobManager.create_job."""

    def test_create_job_returns_job(self, manager):
        """Test that create_job returns a Job instance."""
        job = manager.create_job(JobType.DATASET_GENERATION)

        assert isinstance(job, Job)
        assert job.id is not None
        assert job.job_type == JobType.DATASET_GENERATION
        assert job.status == JobStatus.PENDING
        assert job.progress == 0

    def test_create_job_with_metadata(self, manager):
        """Test creating a job with metadata."""
        metadata = {"dataset_id": 42, "tier": "T1"}
        job = manager.create_job(JobType.DATASET_GENERATION, metadata=metadata)

        assert job.metadata == metadata

    def test_create_job_default_metadata(self, manager):
        """Test that default metadata is an empty dict."""
        job = manager.create_job(JobType.EVALUATION)

        assert job.metadata == {}

    def test_create_job_has_created_at(self, manager):
        """Test that created_at is set on creation."""
        job = manager.create_job(JobType.EVALUATION)

        assert job.created_at is not None
        assert isinstance(job.created_at, datetime)

    def test_create_job_no_started_or_completed(self, manager):
        """Test that started_at and completed_at are None on creation."""
        job = manager.create_job(JobType.DATASET_GENERATION)

        assert job.started_at is None
        assert job.completed_at is None


# =============================================================================
# GET JOB TESTS
# =============================================================================


class TestGetJob:
    """Tests for DatabaseJobManager.get_job."""

    def test_get_job_exists(self, manager):
        """Test retrieving an existing job."""
        created = manager.create_job(JobType.DATASET_GENERATION, metadata={"key": "val"})
        retrieved = manager.get_job(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.job_type == JobType.DATASET_GENERATION
        assert retrieved.status == JobStatus.PENDING

    def test_get_job_not_found(self, manager):
        """Test retrieving a non-existent job returns None."""
        result = manager.get_job("nonexistent-id")

        assert result is None

    def test_get_job_preserves_metadata(self, manager):
        """Test that metadata survives a round-trip to the database."""
        metadata = {"dataset_id": 1, "options": {"fast": True}}
        created = manager.create_job(JobType.EVALUATION, metadata=metadata)
        retrieved = manager.get_job(created.id)

        assert retrieved.metadata == metadata


# =============================================================================
# UPDATE JOB TESTS
# =============================================================================


class TestUpdateJob:
    """Tests for DatabaseJobManager.update_job."""

    def test_update_job_status(self, manager):
        """Test updating a job's status."""
        job = manager.create_job(JobType.DATASET_GENERATION)
        updated = manager.update_job(job.id, status=JobStatus.RUNNING)

        assert updated is not None
        assert updated.status == JobStatus.RUNNING

    def test_update_job_progress(self, manager):
        """Test updating a job's progress."""
        job = manager.create_job(JobType.DATASET_GENERATION)
        manager.start_job(job.id)
        updated = manager.update_job(job.id, progress=75)

        assert updated is not None
        assert updated.progress == 75

    def test_update_job_progress_clamped(self, manager):
        """Test that progress is clamped to 0-100."""
        job = manager.create_job(JobType.DATASET_GENERATION)
        updated = manager.update_job(job.id, progress=150)

        assert updated.progress == 100

    def test_update_job_progress_floor(self, manager):
        """Test that progress floor is 0."""
        job = manager.create_job(JobType.DATASET_GENERATION)
        updated = manager.update_job(job.id, progress=-10)

        assert updated.progress == 0

    def test_update_job_stage(self, manager):
        """Test updating a job's stage description."""
        job = manager.create_job(JobType.DATASET_GENERATION)
        updated = manager.update_job(job.id, stage="Generating observations")

        assert updated.stage == "Generating observations"

    def test_update_nonexistent_job(self, manager):
        """Test updating a non-existent job returns None."""
        result = manager.update_job("no-such-id", status=JobStatus.RUNNING)

        assert result is None

    def test_update_job_no_changes(self, manager):
        """Test updating with no changes returns the existing job."""
        job = manager.create_job(JobType.DATASET_GENERATION)
        result = manager.update_job(job.id)

        assert result is not None
        assert result.id == job.id


# =============================================================================
# START JOB TESTS
# =============================================================================


class TestStartJob:
    """Tests for DatabaseJobManager.start_job."""

    def test_start_job(self, manager):
        """Test starting a job sets status to RUNNING."""
        job = manager.create_job(JobType.DATASET_GENERATION)
        started = manager.start_job(job.id)

        assert started is not None
        assert started.status == JobStatus.RUNNING

    def test_start_job_sets_started_at(self, manager):
        """Test that start_job sets the started_at timestamp."""
        job = manager.create_job(JobType.DATASET_GENERATION)
        started = manager.start_job(job.id)

        assert started.started_at is not None

    def test_start_nonexistent_job(self, manager):
        """Test starting a non-existent job returns None."""
        result = manager.start_job("nonexistent")

        assert result is None


# =============================================================================
# COMPLETE JOB TESTS
# =============================================================================


class TestCompleteJob:
    """Tests for DatabaseJobManager.complete_job."""

    def test_complete_job(self, manager):
        """Test completing a job sets status and progress."""
        job = manager.create_job(JobType.DATASET_GENERATION)
        manager.start_job(job.id)
        completed = manager.complete_job(job.id, result={"count": 100})

        assert completed is not None
        assert completed.status == JobStatus.COMPLETED
        assert completed.progress == 100
        assert completed.result == {"count": 100}

    def test_complete_job_sets_completed_at(self, manager):
        """Test that complete_job sets the completed_at timestamp."""
        job = manager.create_job(JobType.EVALUATION)
        manager.start_job(job.id)
        completed = manager.complete_job(job.id, result={})

        assert completed.completed_at is not None

    def test_complete_job_without_result(self, manager):
        """Test completing a job without a result."""
        job = manager.create_job(JobType.EVALUATION)
        manager.start_job(job.id)
        completed = manager.complete_job(job.id)

        assert completed.status == JobStatus.COMPLETED
        assert completed.progress == 100


# =============================================================================
# FAIL JOB TESTS
# =============================================================================


class TestFailJob:
    """Tests for DatabaseJobManager.fail_job."""

    def test_fail_job(self, manager):
        """Test failing a job sets status and error."""
        job = manager.create_job(JobType.DATASET_GENERATION)
        manager.start_job(job.id)
        failed = manager.fail_job(job.id, error="Something went wrong")

        assert failed is not None
        assert failed.status == JobStatus.FAILED
        assert failed.error == "Something went wrong"

    def test_fail_job_sets_completed_at(self, manager):
        """Test that fail_job sets the completed_at timestamp."""
        job = manager.create_job(JobType.EVALUATION)
        manager.start_job(job.id)
        failed = manager.fail_job(job.id, error="Timeout")

        assert failed.completed_at is not None


# =============================================================================
# LIST JOBS TESTS
# =============================================================================


class TestListJobs:
    """Tests for DatabaseJobManager.list_jobs."""

    def test_list_all_jobs(self, manager):
        """Test listing all jobs."""
        manager.create_job(JobType.DATASET_GENERATION)
        manager.create_job(JobType.EVALUATION)
        manager.create_job(JobType.DATASET_GENERATION)

        jobs = manager.list_jobs()

        assert len(jobs) == 3

    def test_list_jobs_filter_by_type(self, manager):
        """Test filtering jobs by type."""
        manager.create_job(JobType.DATASET_GENERATION)
        manager.create_job(JobType.EVALUATION)
        manager.create_job(JobType.DATASET_GENERATION)

        dataset_jobs = manager.list_jobs(job_type=JobType.DATASET_GENERATION)
        eval_jobs = manager.list_jobs(job_type=JobType.EVALUATION)

        assert len(dataset_jobs) == 2
        assert len(eval_jobs) == 1

    def test_list_jobs_filter_by_status(self, manager):
        """Test filtering jobs by status."""
        job1 = manager.create_job(JobType.DATASET_GENERATION)
        job2 = manager.create_job(JobType.EVALUATION)
        manager.start_job(job1.id)
        manager.complete_job(job1.id, result={})

        pending = manager.list_jobs(status=JobStatus.PENDING)
        completed = manager.list_jobs(status=JobStatus.COMPLETED)

        assert len(pending) == 1
        assert len(completed) == 1

    def test_list_jobs_combined_filters(self, manager):
        """Test combining type and status filters."""
        job1 = manager.create_job(JobType.DATASET_GENERATION)
        job2 = manager.create_job(JobType.EVALUATION)
        job3 = manager.create_job(JobType.DATASET_GENERATION)

        manager.start_job(job1.id)
        manager.fail_job(job1.id, error="failed")

        failed_datasets = manager.list_jobs(
            job_type=JobType.DATASET_GENERATION, status=JobStatus.FAILED
        )

        assert len(failed_datasets) == 1

    def test_list_jobs_with_limit(self, manager):
        """Test limiting the number of returned jobs."""
        for _ in range(5):
            manager.create_job(JobType.EVALUATION)

        jobs = manager.list_jobs(limit=3)

        assert len(jobs) == 3

    def test_list_jobs_empty(self, manager):
        """Test listing when no jobs exist."""
        jobs = manager.list_jobs()

        assert jobs == []


# =============================================================================
# PERSISTENCE TESTS
# =============================================================================


class TestPersistence:
    """Tests verifying that jobs persist across manager instances."""

    def test_job_survives_reinitialization(self, fake_db):
        """Test that a job created by one manager is visible to another."""
        with patch.object(DatabaseJobManager, '_get_db', return_value=fake_db):
            manager1 = DatabaseJobManager()
            job = manager1.create_job(
                JobType.DATASET_GENERATION, metadata={"dataset_id": 99}
            )
            manager1.start_job(job.id)
            manager1.update_job(job.id, progress=50, stage="Halfway there")

            # Create a new manager instance backed by the same database
            manager2 = DatabaseJobManager()
            retrieved = manager2.get_job(job.id)

        assert retrieved is not None
        assert retrieved.id == job.id
        assert retrieved.job_type == JobType.DATASET_GENERATION
        assert retrieved.status == JobStatus.RUNNING
        assert retrieved.progress == 50

    def test_completed_job_persists(self, fake_db):
        """Test that completed jobs persist across manager instances."""
        with patch.object(DatabaseJobManager, '_get_db', return_value=fake_db):
            manager1 = DatabaseJobManager()
            job = manager1.create_job(JobType.EVALUATION)
            manager1.start_job(job.id)
            manager1.complete_job(job.id, result={"score": 0.95})

            manager2 = DatabaseJobManager()
            retrieved = manager2.get_job(job.id)

        assert retrieved is not None
        assert retrieved.status == JobStatus.COMPLETED
        assert retrieved.result == {"score": 0.95}

    def test_list_jobs_across_managers(self, fake_db):
        """Test listing jobs from a different manager instance."""
        with patch.object(DatabaseJobManager, '_get_db', return_value=fake_db):
            manager1 = DatabaseJobManager()
            manager1.create_job(JobType.DATASET_GENERATION)
            manager1.create_job(JobType.EVALUATION)

            manager2 = DatabaseJobManager()
            jobs = manager2.list_jobs()

        assert len(jobs) == 2


# =============================================================================
# INIT_JOB_MANAGER INTEGRATION TESTS
# =============================================================================


class TestInitJobManager:
    """Tests for the init_job_manager factory function."""

    def test_init_defaults_to_in_memory(self):
        """Test that init_job_manager defaults to in-memory JobManager."""
        from backend_api.jobs import JobManager, init_job_manager

        with patch("backend_api.config.get_config") as mock_config:
            from backend_api.config import DatabaseBackend

            mock_cfg = MagicMock()
            mock_cfg.db_backend = DatabaseBackend.DUCKDB
            mock_config.return_value = mock_cfg

            manager = init_job_manager()
            assert isinstance(manager, JobManager)

    def test_init_selects_db_manager_for_postgres(self):
        """Test that init_job_manager selects DatabaseJobManager for postgres."""
        from backend_api.jobs import init_job_manager

        with patch("backend_api.config.get_config") as mock_config:
            from backend_api.config import DatabaseBackend

            mock_cfg = MagicMock()
            mock_cfg.db_backend = DatabaseBackend.POSTGRES
            mock_config.return_value = mock_cfg

            manager = init_job_manager()
            assert isinstance(manager, DatabaseJobManager)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
