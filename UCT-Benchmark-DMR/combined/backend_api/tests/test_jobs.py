"""
Tests for the Jobs API router.

Tests the GET /api/v1/jobs endpoints for job status
and management.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend_api.jobs import JobManager, JobStatus, JobType

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_job_manager():
    """Create a mock job manager with sample jobs."""
    manager = JobManager()

    # Create sample jobs with different statuses
    job1 = manager.create_job(JobType.DATASET_GENERATION, metadata={"dataset_id": 1})
    manager.start_job(job1.id)
    manager.update_job(job1.id, progress=50)

    job2 = manager.create_job(JobType.EVALUATION, metadata={"submission_id": 1})
    manager.start_job(job2.id)
    manager.complete_job(job2.id, result={"status": "success"})

    job3 = manager.create_job(JobType.DATASET_GENERATION, metadata={"dataset_id": 2})
    manager.start_job(job3.id)
    manager.fail_job(job3.id, error="Test error message")

    job4 = manager.create_job(JobType.EVALUATION, metadata={"submission_id": 2})
    # Leave as pending

    return manager


@pytest.fixture
def client_with_jobs(mock_job_manager):
    """Create a test client with mocked job manager."""
    import backend_api.database as db_module
    from backend_api.main import app
    from uct_benchmark.database.connection import DatabaseManager

    # Create a minimal in-memory database for the app lifespan
    test_db = DatabaseManager(in_memory=True)
    test_db.initialize()
    original_db = db_module._db_manager
    db_module._db_manager = test_db

    with patch("backend_api.main.init_database", return_value=test_db):
        with patch("backend_api.main.close_database"):
            with patch("backend_api.main.init_job_manager", return_value=mock_job_manager):
                with patch("backend_api.main.shutdown_executor"):
                    with patch(
                        "backend_api.routers.jobs.get_job_manager", return_value=mock_job_manager
                    ):
                        with TestClient(app) as client:
                            yield client

    db_module._db_manager = original_db
    test_db.close()


@pytest.fixture
def client_empty_jobs():
    """Create a test client with empty job manager."""
    import backend_api.database as db_module
    from backend_api.main import app
    from uct_benchmark.database.connection import DatabaseManager

    empty_manager = JobManager()

    # Create a minimal in-memory database for the app lifespan
    test_db = DatabaseManager(in_memory=True)
    test_db.initialize()
    original_db = db_module._db_manager
    db_module._db_manager = test_db

    with patch("backend_api.main.init_database", return_value=test_db):
        with patch("backend_api.main.close_database"):
            with patch("backend_api.main.init_job_manager", return_value=empty_manager):
                with patch("backend_api.main.shutdown_executor"):
                    with patch(
                        "backend_api.routers.jobs.get_job_manager", return_value=empty_manager
                    ):
                        with TestClient(app) as client:
                            yield client

    db_module._db_manager = original_db
    test_db.close()


# =============================================================================
# HELPER FUNCTION FOR TEST CLIENT
# =============================================================================

from contextlib import contextmanager


@contextmanager
def create_test_client_with_job_manager(job_manager):
    """Create a test client with the given job manager."""
    import backend_api.database as db_module
    from backend_api.main import app
    from uct_benchmark.database.connection import DatabaseManager

    test_db = DatabaseManager(in_memory=True)
    test_db.initialize()
    original_db = db_module._db_manager
    db_module._db_manager = test_db

    with patch("backend_api.main.init_database", return_value=test_db):
        with patch("backend_api.main.close_database"):
            with patch("backend_api.main.init_job_manager", return_value=job_manager):
                with patch("backend_api.main.shutdown_executor"):
                    with patch(
                        "backend_api.routers.jobs.get_job_manager", return_value=job_manager
                    ):
                        with TestClient(app) as client:
                            yield client

    db_module._db_manager = original_db
    test_db.close()


# =============================================================================
# GET /api/v1/jobs/{job_id} TESTS
# =============================================================================


class TestGetJobStatus:
    """Tests for GET /api/v1/jobs/{job_id}."""

    def test_get_job_status_running(self, mock_job_manager):
        """Test getting status of running job."""
        # Get the running job ID
        jobs = mock_job_manager.list_jobs(status=JobStatus.RUNNING)
        running_job = jobs[0]

        with create_test_client_with_job_manager(mock_job_manager) as client:
            response = client.get(f"/api/v1/jobs/{running_job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == running_job.id
        assert data["status"] == "running"
        assert data["progress"] == 50
        assert data["job_type"] == "dataset_generation"

    def test_get_job_status_completed(self, mock_job_manager):
        """Test getting status of completed job."""
        # Get the completed job
        jobs = mock_job_manager.list_jobs(status=JobStatus.COMPLETED)
        completed_job = jobs[0]

        with create_test_client_with_job_manager(mock_job_manager) as client:
            response = client.get(f"/api/v1/jobs/{completed_job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "completed"
        assert data["result"] is not None
        assert data["completed_at"] is not None

    def test_get_job_status_failed(self, mock_job_manager):
        """Test getting status of failed job."""
        # Get the failed job
        jobs = mock_job_manager.list_jobs(status=JobStatus.FAILED)
        failed_job = jobs[0]

        with create_test_client_with_job_manager(mock_job_manager) as client:
            response = client.get(f"/api/v1/jobs/{failed_job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "failed"
        assert data["error"] == "Test error message"

    def test_get_job_status_pending(self, mock_job_manager):
        """Test getting status of pending job."""
        # Get the pending job
        jobs = mock_job_manager.list_jobs(status=JobStatus.PENDING)
        pending_job = jobs[0]

        with create_test_client_with_job_manager(mock_job_manager) as client:
            response = client.get(f"/api/v1/jobs/{pending_job.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "pending"
        assert data["progress"] == 0
        assert data["started_at"] is None

    def test_get_job_status_not_found(self, client_with_jobs):
        """Test 404 for non-existent job."""
        response = client_with_jobs.get("/api/v1/jobs/non-existent-job-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_job_status_fields(self, mock_job_manager):
        """Test that job response contains all expected fields."""
        jobs = mock_job_manager.list_jobs()
        job = jobs[0]

        with create_test_client_with_job_manager(mock_job_manager) as client:
            response = client.get(f"/api/v1/jobs/{job.id}")

        assert response.status_code == 200
        data = response.json()

        # Check all expected fields
        assert "id" in data
        assert "job_type" in data
        assert "status" in data
        assert "progress" in data
        assert "result" in data
        assert "error" in data
        assert "created_at" in data
        assert "started_at" in data
        assert "completed_at" in data
        assert "metadata" in data


# =============================================================================
# GET /api/v1/jobs/ TESTS
# =============================================================================


class TestListJobs:
    """Tests for GET /api/v1/jobs/."""

    def test_list_jobs_all(self, client_with_jobs):
        """Test listing all jobs."""
        response = client_with_jobs.get("/api/v1/jobs/")

        assert response.status_code == 200
        data = response.json()

        # Should return all 4 jobs
        assert len(data) == 4

    def test_list_jobs_filter_by_type_dataset(self, client_with_jobs):
        """Test filtering jobs by dataset_generation type."""
        response = client_with_jobs.get("/api/v1/jobs/?job_type=dataset_generation")

        assert response.status_code == 200
        data = response.json()

        # 2 dataset generation jobs
        assert len(data) == 2
        for job in data:
            assert job["job_type"] == "dataset_generation"

    def test_list_jobs_filter_by_type_evaluation(self, client_with_jobs):
        """Test filtering jobs by evaluation type."""
        response = client_with_jobs.get("/api/v1/jobs/?job_type=evaluation")

        assert response.status_code == 200
        data = response.json()

        # 2 evaluation jobs
        assert len(data) == 2
        for job in data:
            assert job["job_type"] == "evaluation"

    def test_list_jobs_filter_by_status_running(self, client_with_jobs):
        """Test filtering jobs by running status."""
        response = client_with_jobs.get("/api/v1/jobs/?status=running")

        assert response.status_code == 200
        data = response.json()

        # 1 running job
        assert len(data) == 1
        assert data[0]["status"] == "running"

    def test_list_jobs_filter_by_status_completed(self, client_with_jobs):
        """Test filtering jobs by completed status."""
        response = client_with_jobs.get("/api/v1/jobs/?status=completed")

        assert response.status_code == 200
        data = response.json()

        # 1 completed job
        assert len(data) == 1
        assert data[0]["status"] == "completed"

    def test_list_jobs_filter_by_status_failed(self, client_with_jobs):
        """Test filtering jobs by failed status."""
        response = client_with_jobs.get("/api/v1/jobs/?status=failed")

        assert response.status_code == 200
        data = response.json()

        # 1 failed job
        assert len(data) == 1
        assert data[0]["status"] == "failed"

    def test_list_jobs_filter_by_status_pending(self, client_with_jobs):
        """Test filtering jobs by pending status."""
        response = client_with_jobs.get("/api/v1/jobs/?status=pending")

        assert response.status_code == 200
        data = response.json()

        # 1 pending job
        assert len(data) == 1
        assert data[0]["status"] == "pending"

    def test_list_jobs_combined_filters(self, client_with_jobs):
        """Test combining type and status filters."""
        response = client_with_jobs.get("/api/v1/jobs/?job_type=dataset_generation&status=failed")

        assert response.status_code == 200
        data = response.json()

        # 1 failed dataset generation job
        assert len(data) == 1
        assert data[0]["job_type"] == "dataset_generation"
        assert data[0]["status"] == "failed"

    def test_list_jobs_limit(self, client_with_jobs):
        """Test limiting number of jobs returned."""
        response = client_with_jobs.get("/api/v1/jobs/?limit=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2

    def test_list_jobs_empty(self, client_empty_jobs):
        """Test listing jobs when none exist."""
        response = client_empty_jobs.get("/api/v1/jobs/")

        assert response.status_code == 200
        data = response.json()

        assert data == []

    def test_list_jobs_invalid_type_filter(self, client_with_jobs):
        """Test that invalid job type filter is ignored."""
        response = client_with_jobs.get("/api/v1/jobs/?job_type=invalid_type")

        assert response.status_code == 200
        # Should return all jobs since invalid filter is ignored
        data = response.json()
        assert len(data) == 4

    def test_list_jobs_invalid_status_filter(self, client_with_jobs):
        """Test that invalid status filter is ignored."""
        response = client_with_jobs.get("/api/v1/jobs/?status=invalid_status")

        assert response.status_code == 200
        # Should return all jobs since invalid filter is ignored
        data = response.json()
        assert len(data) == 4


# =============================================================================
# JOB MANAGER UNIT TESTS
# =============================================================================


class TestJobManager:
    """Unit tests for JobManager class."""

    def test_create_job(self):
        """Test creating a new job."""
        manager = JobManager()
        job = manager.create_job(JobType.DATASET_GENERATION, metadata={"test": True})

        assert job.id is not None
        assert job.job_type == JobType.DATASET_GENERATION
        assert job.status == JobStatus.PENDING
        assert job.progress == 0
        assert job.metadata == {"test": True}
        assert job.created_at is not None

    def test_get_job(self):
        """Test retrieving a job by ID."""
        manager = JobManager()
        created = manager.create_job(JobType.EVALUATION)

        retrieved = manager.get_job(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_nonexistent_job(self):
        """Test retrieving non-existent job returns None."""
        manager = JobManager()

        result = manager.get_job("nonexistent-id")

        assert result is None

    def test_start_job(self):
        """Test starting a job."""
        manager = JobManager()
        job = manager.create_job(JobType.DATASET_GENERATION)

        manager.start_job(job.id)

        updated = manager.get_job(job.id)
        assert updated.status == JobStatus.RUNNING
        assert updated.started_at is not None

    def test_update_job_progress(self):
        """Test updating job progress."""
        manager = JobManager()
        job = manager.create_job(JobType.DATASET_GENERATION)
        manager.start_job(job.id)

        manager.update_job(job.id, progress=75)

        updated = manager.get_job(job.id)
        assert updated.progress == 75

    def test_complete_job(self):
        """Test completing a job."""
        manager = JobManager()
        job = manager.create_job(JobType.DATASET_GENERATION)
        manager.start_job(job.id)

        manager.complete_job(job.id, result={"count": 100})

        updated = manager.get_job(job.id)
        assert updated.status == JobStatus.COMPLETED
        assert updated.progress == 100
        assert updated.result == {"count": 100}
        assert updated.completed_at is not None

    def test_fail_job(self):
        """Test failing a job."""
        manager = JobManager()
        job = manager.create_job(JobType.DATASET_GENERATION)
        manager.start_job(job.id)

        manager.fail_job(job.id, error="Something went wrong")

        updated = manager.get_job(job.id)
        assert updated.status == JobStatus.FAILED
        assert updated.error == "Something went wrong"
        assert updated.completed_at is not None

    def test_list_jobs_by_type(self):
        """Test listing jobs filtered by type."""
        manager = JobManager()
        manager.create_job(JobType.DATASET_GENERATION)
        manager.create_job(JobType.EVALUATION)
        manager.create_job(JobType.DATASET_GENERATION)

        dataset_jobs = manager.list_jobs(job_type=JobType.DATASET_GENERATION)
        eval_jobs = manager.list_jobs(job_type=JobType.EVALUATION)

        assert len(dataset_jobs) == 2
        assert len(eval_jobs) == 1

    def test_list_jobs_by_status(self):
        """Test listing jobs filtered by status."""
        manager = JobManager()
        job1 = manager.create_job(JobType.DATASET_GENERATION)
        job2 = manager.create_job(JobType.EVALUATION)

        manager.start_job(job1.id)
        manager.complete_job(job1.id, result={})

        pending = manager.list_jobs(status=JobStatus.PENDING)
        completed = manager.list_jobs(status=JobStatus.COMPLETED)

        assert len(pending) == 1
        assert len(completed) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
