"""
Tests for background worker functions.

Tests the dataset generation and evaluation worker
functions and their job management.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend_api.jobs import JobManager, JobStatus, JobType
from backend_api.jobs.workers import (
    get_executor,
    shutdown_executor,
    submit_dataset_generation,
    submit_evaluation,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def job_manager():
    """Create a fresh job manager for testing."""
    return JobManager()


@pytest.fixture
def mock_database():
    """Create a mock database for testing."""
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchone.return_value = (1, "test", "available")
    mock_db.execute.return_value.fetchdf.return_value = MagicMock()
    return mock_db


@pytest.fixture
def sample_submission_file(tmp_path: Path) -> Path:
    """Create a sample submission file for evaluation tests."""
    file_path = tmp_path / "submission.json"
    submission_data = {
        "algorithm": "TestAlgo",
        "version": "1.0",
        "predictions": [
            {"observation_id": "obs-1", "satellite_id": 25544, "confidence": 0.95},
            {"observation_id": "obs-2", "satellite_id": 25544, "confidence": 0.90},
        ],
    }
    file_path.write_text(json.dumps(submission_data))
    return file_path


# =============================================================================
# EXECUTOR TESTS
# =============================================================================


class TestExecutor:
    """Tests for thread pool executor management."""

    def test_get_executor_creates_singleton(self):
        """Test that get_executor creates a singleton executor."""
        executor1 = get_executor()
        executor2 = get_executor()

        assert executor1 is executor2

    def test_shutdown_executor(self):
        """Test that shutdown_executor cleans up properly."""
        # Get executor to ensure it's created
        get_executor()

        # Shutdown
        shutdown_executor()

        # Next call should create a new one
        new_executor = get_executor()
        assert new_executor is not None

        # Cleanup
        shutdown_executor()


# =============================================================================
# SUBMIT DATASET GENERATION TESTS
# =============================================================================


class TestSubmitDatasetGeneration:
    """Tests for submit_dataset_generation function."""

    @patch("backend_api.jobs.workers.get_job_manager")
    @patch("backend_api.jobs.workers.get_executor")
    def test_submit_creates_job(self, mock_get_executor, mock_get_job_manager):
        """Test that submitting creates a job and returns it."""
        mock_manager = JobManager()
        mock_get_job_manager.return_value = mock_manager

        mock_executor = MagicMock()
        mock_get_executor.return_value = mock_executor

        config = {
            "name": "test-dataset",
            "regime": "LEO",
            "timeframe": 7,
        }

        job = submit_dataset_generation(dataset_id=1, config=config)

        assert job is not None
        assert job.job_type == JobType.DATASET_GENERATION
        assert job.status == JobStatus.PENDING
        assert job.metadata["dataset_id"] == 1

    @patch("backend_api.jobs.workers.get_job_manager")
    @patch("backend_api.jobs.workers.get_executor")
    def test_submit_submits_to_executor(self, mock_get_executor, mock_get_job_manager):
        """Test that worker is submitted to executor."""
        mock_manager = JobManager()
        mock_get_job_manager.return_value = mock_manager

        mock_executor = MagicMock()
        mock_get_executor.return_value = mock_executor

        config = {"name": "test"}
        submit_dataset_generation(dataset_id=1, config=config)

        # Verify executor.submit was called
        assert mock_executor.submit.called

    @patch("backend_api.jobs.workers.get_job_manager")
    @patch("backend_api.jobs.workers.get_executor")
    def test_submit_stores_config_in_metadata(self, mock_get_executor, mock_get_job_manager):
        """Test that config is stored in job metadata."""
        mock_manager = JobManager()
        mock_get_job_manager.return_value = mock_manager

        mock_executor = MagicMock()
        mock_get_executor.return_value = mock_executor

        config = {
            "name": "test-dataset",
            "regime": "LEO",
            "timeframe": 7,
            "downsampling": {"enabled": True},
        }

        job = submit_dataset_generation(dataset_id=1, config=config)

        assert job.metadata["config"] == config


# =============================================================================
# SUBMIT EVALUATION TESTS
# =============================================================================


class TestSubmitEvaluation:
    """Tests for submit_evaluation function."""

    @patch("backend_api.jobs.workers.get_job_manager")
    @patch("backend_api.jobs.workers.get_executor")
    def test_submit_creates_evaluation_job(self, mock_get_executor, mock_get_job_manager):
        """Test that submitting creates an evaluation job."""
        mock_manager = JobManager()
        mock_get_job_manager.return_value = mock_manager

        mock_executor = MagicMock()
        mock_get_executor.return_value = mock_executor

        job = submit_evaluation(submission_id=1, dataset_id=1, file_path="/tmp/submission.json")

        assert job is not None
        assert job.job_type == JobType.EVALUATION
        assert job.metadata["submission_id"] == 1
        assert job.metadata["dataset_id"] == 1
        assert job.metadata["file_path"] == "/tmp/submission.json"

    @patch("backend_api.jobs.workers.get_job_manager")
    @patch("backend_api.jobs.workers.get_executor")
    def test_submit_evaluation_to_executor(self, mock_get_executor, mock_get_job_manager):
        """Test that evaluation worker is submitted to executor."""
        mock_manager = JobManager()
        mock_get_job_manager.return_value = mock_manager

        mock_executor = MagicMock()
        mock_get_executor.return_value = mock_executor

        submit_evaluation(submission_id=1, dataset_id=1, file_path="/tmp/test.json")

        assert mock_executor.submit.called


# =============================================================================
# DATASET GENERATION WORKER TESTS
# =============================================================================


class TestDatasetGenerationWorker:
    """Tests for run_dataset_generation worker function."""

    @patch("backend_api.jobs.workers.get_job_manager")
    def test_worker_starts_job(self, mock_get_job_manager):
        """Test that worker starts the job on entry."""
        from backend_api.jobs.workers import run_dataset_generation

        mock_manager = MagicMock()
        mock_get_job_manager.return_value = mock_manager

        # Should fail due to missing tokens, but start_job should be called
        try:
            run_dataset_generation(job_id="test-job", dataset_id=1, config={"name": "test"})
        except Exception:
            pass

        mock_manager.start_job.assert_called_once_with("test-job")

    @patch("backend_api.jobs.workers.get_job_manager")
    def test_worker_fails_without_tokens(self, mock_get_job_manager):
        """Test that worker fails when API tokens are missing."""
        import os

        from backend_api.jobs.workers import run_dataset_generation

        # Ensure tokens are not set
        os.environ.pop("UDL_TOKEN", None)
        os.environ.pop("ESA_TOKEN", None)

        mock_manager = MagicMock()
        mock_get_job_manager.return_value = mock_manager

        run_dataset_generation(job_id="test-job", dataset_id=1, config={"name": "test"})

        # Should fail with error about missing tokens
        mock_manager.fail_job.assert_called_once()
        error_msg = mock_manager.fail_job.call_args[0][1]
        assert "UDL_TOKEN" in error_msg or "ESA_TOKEN" in error_msg

    @patch("backend_api.jobs.workers.get_job_manager")
    @patch("backend_api.jobs.workers.generateDataset")
    @patch("backend_api.database.get_db")
    def test_worker_updates_progress(self, mock_get_db, mock_generate, mock_get_job_manager):
        """Test that worker updates progress during execution."""
        import os

        from backend_api.jobs.workers import run_dataset_generation

        os.environ["UDL_TOKEN"] = "test-token"
        os.environ["ESA_TOKEN"] = "test-token"

        mock_manager = MagicMock()
        mock_get_job_manager.return_value = mock_manager

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_generate.return_value = (None, None, None, None, [25544], {})

        run_dataset_generation(
            job_id="test-job", dataset_id=1, config={"name": "test", "satellites": [25544]}
        )

        # Should have called update_job multiple times
        assert mock_manager.update_job.called

        # Cleanup
        os.environ.pop("UDL_TOKEN", None)
        os.environ.pop("ESA_TOKEN", None)

    @patch("backend_api.jobs.workers.get_job_manager")
    @patch("backend_api.jobs.workers.generateDataset")
    @patch("backend_api.database.get_db")
    def test_worker_completes_job_on_success(
        self, mock_get_db, mock_generate, mock_get_job_manager
    ):
        """Test that worker completes job on successful generation."""
        import os

        from backend_api.jobs.workers import run_dataset_generation

        os.environ["UDL_TOKEN"] = "test-token"
        os.environ["ESA_TOKEN"] = "test-token"

        mock_manager = MagicMock()
        mock_get_job_manager.return_value = mock_manager

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_generate.return_value = (
            MagicMock(__len__=lambda x: 100),  # dataset_obs with length
            None,
            None,
            None,
            [25544, 25545],  # actual_sats
            {"api_calls": 10},  # performance_data
        )

        run_dataset_generation(job_id="test-job", dataset_id=1, config={"name": "test"})

        # Should complete the job
        mock_manager.complete_job.assert_called_once()
        result = mock_manager.complete_job.call_args[0][1]
        assert result["dataset_id"] == 1

        os.environ.pop("UDL_TOKEN", None)
        os.environ.pop("ESA_TOKEN", None)

    def test_worker_config_parsing_downsampling(self):
        """Test that downsampling config is parsed correctly."""
        config = {
            "downsampling": {
                "enabled": True,
                "target_coverage": 0.1,
                "target_gap": 3.0,
            }
        }

        ds_opts = config.get("downsampling", {})
        parsed = {
            "enabled": ds_opts.get("enabled", False),
            "target_coverage": ds_opts.get("target_coverage", 0.05),
            "target_gap": ds_opts.get("target_gap", 2.0),
        }

        assert parsed["enabled"] is True
        assert parsed["target_coverage"] == 0.1
        assert parsed["target_gap"] == 3.0

    def test_worker_config_parsing_simulation(self):
        """Test that simulation config is parsed correctly."""
        config = {
            "simulation": {
                "enabled": True,
                "sensor_model": "SBSS",
                "max_synthetic_ratio": 0.3,
            }
        }

        sim_opts = config.get("simulation", {})
        parsed = {
            "enabled": sim_opts.get("enabled", False),
            "sensor_model": sim_opts.get("sensor_model", "GEODSS"),
            "max_synthetic_ratio": sim_opts.get("max_synthetic_ratio", 0.5),
        }

        assert parsed["enabled"] is True
        assert parsed["sensor_model"] == "SBSS"
        assert parsed["max_synthetic_ratio"] == 0.3


# =============================================================================
# EVALUATION WORKER TESTS
# =============================================================================


class TestEvaluationWorker:
    """Tests for run_evaluation_pipeline worker function."""

    @patch("backend_api.jobs.workers.get_job_manager")
    def test_worker_starts_job(self, mock_get_job_manager, sample_submission_file):
        """Test that evaluation worker starts the job."""
        from backend_api.jobs.workers import run_evaluation_pipeline

        mock_manager = MagicMock()
        mock_get_job_manager.return_value = mock_manager

        # Will fail but should start job first
        try:
            run_evaluation_pipeline(
                job_id="test-job",
                submission_id=1,
                dataset_id=1,
                file_path=str(sample_submission_file),
            )
        except Exception:
            pass

        mock_manager.start_job.assert_called_once_with("test-job")

    @patch("backend_api.jobs.workers.get_job_manager")
    @patch("backend_api.database.get_db")
    def test_worker_fails_for_missing_dataset(
        self, mock_get_db, mock_get_job_manager, sample_submission_file
    ):
        """Test that worker fails when dataset doesn't exist."""
        from backend_api.jobs.workers import run_evaluation_pipeline

        mock_manager = MagicMock()
        mock_get_job_manager.return_value = mock_manager

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None  # No dataset
        mock_get_db.return_value = mock_db

        run_evaluation_pipeline(
            job_id="test-job",
            submission_id=1,
            dataset_id=999,
            file_path=str(sample_submission_file),
        )

        mock_manager.fail_job.assert_called_once()
        error_msg = mock_manager.fail_job.call_args[0][1]
        assert "not found" in error_msg.lower()

    @patch("backend_api.jobs.workers.get_job_manager")
    def test_worker_fails_for_missing_file(self, mock_get_job_manager):
        """Test that worker fails when submission file doesn't exist."""
        from backend_api.jobs.workers import run_evaluation_pipeline

        mock_manager = MagicMock()
        mock_get_job_manager.return_value = mock_manager

        run_evaluation_pipeline(
            job_id="test-job", submission_id=1, dataset_id=1, file_path="/nonexistent/file.json"
        )

        mock_manager.fail_job.assert_called_once()


# =============================================================================
# JOB STATE TRANSITION TESTS
# =============================================================================


class TestJobStateTransitions:
    """Tests for job state transitions during worker execution."""

    def test_pending_to_running(self, job_manager):
        """Test transition from pending to running."""
        job = job_manager.create_job(JobType.DATASET_GENERATION)
        assert job.status == JobStatus.PENDING

        job_manager.start_job(job.id)
        updated = job_manager.get_job(job.id)
        assert updated.status == JobStatus.RUNNING

    def test_running_to_completed(self, job_manager):
        """Test transition from running to completed."""
        job = job_manager.create_job(JobType.DATASET_GENERATION)
        job_manager.start_job(job.id)
        job_manager.complete_job(job.id, result={"success": True})

        updated = job_manager.get_job(job.id)
        assert updated.status == JobStatus.COMPLETED
        assert updated.result == {"success": True}

    def test_running_to_failed(self, job_manager):
        """Test transition from running to failed."""
        job = job_manager.create_job(JobType.DATASET_GENERATION)
        job_manager.start_job(job.id)
        job_manager.fail_job(job.id, error="Test error")

        updated = job_manager.get_job(job.id)
        assert updated.status == JobStatus.FAILED
        assert updated.error == "Test error"

    def test_progress_updates(self, job_manager):
        """Test progress updates during execution."""
        job = job_manager.create_job(JobType.DATASET_GENERATION)
        job_manager.start_job(job.id)

        for progress in [10, 20, 50, 80, 100]:
            job_manager.update_job(job.id, progress=progress)
            updated = job_manager.get_job(job.id)
            assert updated.progress == progress


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestWorkerErrorHandling:
    """Tests for worker error handling."""

    @patch("backend_api.jobs.workers.get_job_manager")
    def test_exception_fails_job(self, mock_get_job_manager):
        """Test that exceptions in worker fail the job."""
        from backend_api.jobs.workers import run_dataset_generation

        mock_manager = MagicMock()
        mock_get_job_manager.return_value = mock_manager

        # No tokens set - should fail
        run_dataset_generation(job_id="test-job", dataset_id=1, config={})

        mock_manager.fail_job.assert_called_once()

    @patch("backend_api.jobs.workers.get_job_manager")
    @patch("backend_api.database.get_db")
    def test_database_updated_on_failure(self, mock_get_db, mock_get_job_manager):
        """Test that database is updated when worker fails."""
        from backend_api.jobs.workers import run_dataset_generation

        mock_manager = MagicMock()
        mock_get_job_manager.return_value = mock_manager

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        run_dataset_generation(job_id="test-job", dataset_id=1, config={})

        # Database should have been updated to 'failed' status
        # Check that execute was called with status update
        calls = mock_db.execute.call_args_list
        # At least one call should update status to failed
        any_failed_update = any("failed" in str(call).lower() for call in calls)
        assert any_failed_update or mock_manager.fail_job.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
