"""
Integration tests for the backend API.

These tests verify the full flow of operations across multiple components.

Run with: uv run pytest backend_api/tests/test_integration.py -v
"""

import json
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend_api.jobs import JobStatus, get_job_manager, init_job_manager
from uct_benchmark.database.connection import DatabaseManager


@pytest.fixture
def integration_db() -> Generator[DatabaseManager, None, None]:
    """Create a fresh in-memory database for integration testing."""
    db = DatabaseManager(in_memory=True)
    db.initialize()
    yield db
    db.close()


@pytest.fixture
def integration_client(integration_db: DatabaseManager) -> Generator[TestClient, None, None]:
    """Create a test client for integration tests."""
    from backend_api.database import get_db
    from backend_api.main import app

    def override_get_db():
        return integration_db

    app.dependency_overrides[get_db] = override_get_db

    # Initialize job manager
    init_job_manager()

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestDatasetGenerationFlow:
    """Integration tests for the dataset generation workflow."""

    @patch("backend_api.jobs.workers.run_dataset_generation")
    def test_create_dataset_starts_job(
        self,
        mock_generation: MagicMock,
        integration_client: TestClient,
    ):
        """Test that creating a dataset starts a background job."""
        # Create dataset
        response = integration_client.post(
            "/api/v1/datasets/",
            json={
                "name": "Integration Test Dataset",
                "regime": "LEO",
                "tier": "T1",
                "object_count": 3,
                "timeframe": 1,
                "timeunit": "days",
                "sensors": ["optical"],
                "coverage": 0.8,
                "include_hamr": False,
            },
        )

        assert response.status_code == 200
        dataset = response.json()
        assert dataset["status"] == "generating"
        assert dataset["job_id"] is not None

        # Verify job was created
        job_id = dataset["job_id"]
        job_response = integration_client.get(f"/api/v1/jobs/{job_id}")
        assert job_response.status_code == 200

        job = job_response.json()
        assert job["id"] == job_id
        assert job["job_type"] == "dataset_generation"

    @patch("backend_api.jobs.workers.run_dataset_generation")
    def test_dataset_flow_with_job_completion(
        self,
        mock_generation: MagicMock,
        integration_client: TestClient,
        integration_db: DatabaseManager,
    ):
        """Test the full dataset generation flow including job completion."""
        # Create dataset
        response = integration_client.post(
            "/api/v1/datasets/",
            json={
                "name": "Full Flow Test",
                "regime": "LEO",
                "tier": "T1",
                "object_count": 2,
                "timeframe": 1,
                "timeunit": "days",
                "sensors": ["optical"],
            },
        )

        dataset = response.json()
        dataset_id = dataset["id"]
        job_id = dataset["job_id"]

        # Simulate job completion by updating the database directly
        integration_db.execute(
            """
            UPDATE datasets
            SET status = 'available', observation_count = 100, satellite_count = 2
            WHERE id = ?
            """,
            (int(dataset_id),),
        )

        # Update job status
        job_manager = get_job_manager()
        job_manager.update_job(job_id, status=JobStatus.COMPLETED, progress=100)

        # Verify dataset is now available
        dataset_response = integration_client.get(f"/api/v1/datasets/{dataset_id}")
        assert dataset_response.status_code == 200
        updated_dataset = dataset_response.json()
        assert updated_dataset["status"] == "available"
        assert updated_dataset["observation_count"] == 100

        # Verify job shows completed
        job_response = integration_client.get(f"/api/v1/jobs/{job_id}")
        job = job_response.json()
        assert job["status"] == "completed"


class TestSubmissionEvaluationFlow:
    """Integration tests for the submission evaluation workflow."""

    @patch("backend_api.jobs.workers.run_evaluation_pipeline")
    def test_submission_creates_evaluation_job(
        self,
        mock_evaluation: MagicMock,
        integration_client: TestClient,
        integration_db: DatabaseManager,
        tmp_path: Path,
    ):
        """Test that creating a submission starts an evaluation job."""
        # First create an available dataset
        integration_db.execute(
            """
            INSERT INTO datasets (id, name, tier, orbital_regime, status, observation_count)
            VALUES (1, 'Test Dataset', 'T1', 'LEO', 'available', 100)
            """
        )

        # Create submission file
        submission_file = tmp_path / "test_submission.json"
        submission_file.write_text(json.dumps({"predictions": [{"obs_id": "1", "track_id": 1}]}))

        # Create submission
        with open(submission_file, "rb") as f:
            response = integration_client.post(
                "/api/v1/submissions/",
                data={
                    "dataset_id": "1",
                    "algorithm_name": "TestAlgo",
                    "version": "v1.0",
                },
                files={"file": ("submission.json", f, "application/json")},
            )

        assert response.status_code == 200
        submission = response.json()
        assert submission["status"] == "queued"
        assert submission["job_id"] is not None

        # Verify job exists
        job_response = integration_client.get(f"/api/v1/jobs/{submission['job_id']}")
        assert job_response.status_code == 200

    @patch("backend_api.jobs.workers.run_evaluation_pipeline")
    def test_submission_results_flow(
        self,
        mock_evaluation: MagicMock,
        integration_client: TestClient,
        integration_db: DatabaseManager,
        tmp_path: Path,
    ):
        """Test the full submission and results flow."""
        # Create dataset
        integration_db.execute(
            """
            INSERT INTO datasets (id, name, tier, orbital_regime, status, observation_count)
            VALUES (1, 'Results Flow Dataset', 'T1', 'LEO', 'available', 100)
            """
        )

        # Create submission file
        submission_file = tmp_path / "submission.json"
        submission_file.write_text(json.dumps({"predictions": []}))

        # Create submission
        with open(submission_file, "rb") as f:
            response = integration_client.post(
                "/api/v1/submissions/",
                data={
                    "dataset_id": "1",
                    "algorithm_name": "ResultsTestAlgo",
                    "version": "v1.0",
                },
                files={"file": ("submission.json", f, "application/json")},
            )

        submission = response.json()
        submission_id = submission["id"]

        # Simulate evaluation completion
        integration_db.execute(
            """
            UPDATE submissions
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (int(submission_id),),
        )

        integration_db.execute(
            """
            INSERT INTO submission_results (
                submission_id, true_positives, false_positives, false_negatives,
                precision, recall, f1_score, position_rms_km, velocity_rms_km_s
            ) VALUES (?, 80, 10, 10, 0.889, 0.889, 0.889, 15.0, 0.03)
            """,
            (int(submission_id),),
        )

        # Get results
        results_response = integration_client.get(f"/api/v1/results/{submission_id}")
        assert results_response.status_code == 200

        results = results_response.json()
        assert results["f1_score"] == pytest.approx(0.889, rel=0.01)
        assert results["precision"] == pytest.approx(0.889, rel=0.01)
        assert results["recall"] == pytest.approx(0.889, rel=0.01)


class TestLeaderboardIntegration:
    """Integration tests for leaderboard functionality."""

    def test_leaderboard_aggregates_completed_submissions(
        self,
        integration_client: TestClient,
        integration_db: DatabaseManager,
    ):
        """Test that leaderboard correctly aggregates completed submissions."""
        # Create datasets
        integration_db.execute(
            """
            INSERT INTO datasets (id, name, tier, orbital_regime, status)
            VALUES
                (1, 'Dataset 1', 'T1', 'LEO', 'available'),
                (2, 'Dataset 2', 'T1', 'LEO', 'available')
            """
        )

        # Create submissions with results
        integration_db.execute(
            """
            INSERT INTO submissions (id, dataset_id, algorithm_name, version, status, created_at)
            VALUES
                (1, 1, 'AlgoA', 'v1.0', 'completed', CURRENT_TIMESTAMP),
                (2, 1, 'AlgoB', 'v1.0', 'completed', CURRENT_TIMESTAMP),
                (3, 2, 'AlgoA', 'v2.0', 'completed', CURRENT_TIMESTAMP)
            """
        )

        integration_db.execute(
            """
            INSERT INTO submission_results (
                submission_id, true_positives, false_positives, false_negatives,
                precision, recall, f1_score, position_rms_km, velocity_rms_km_s
            ) VALUES
                (1, 90, 5, 5, 0.947, 0.947, 0.947, 10.0, 0.02),
                (2, 80, 10, 10, 0.889, 0.889, 0.889, 15.0, 0.03),
                (3, 95, 3, 2, 0.969, 0.979, 0.974, 8.0, 0.015)
            """
        )

        # Get leaderboard
        response = integration_client.get("/api/v1/leaderboard/")
        assert response.status_code == 200

        leaderboard = response.json()
        assert len(leaderboard) >= 2

        # Should be sorted by F1 score descending
        f1_scores = [entry["f1_score"] for entry in leaderboard]
        assert f1_scores == sorted(f1_scores, reverse=True)

    def test_leaderboard_filter_by_regime(
        self,
        integration_client: TestClient,
        integration_db: DatabaseManager,
    ):
        """Test filtering leaderboard by orbital regime."""
        # Create datasets in different regimes
        integration_db.execute(
            """
            INSERT INTO datasets (id, name, tier, orbital_regime, status)
            VALUES
                (1, 'LEO Dataset', 'T1', 'LEO', 'available'),
                (2, 'GEO Dataset', 'T1', 'GEO', 'available')
            """
        )

        integration_db.execute(
            """
            INSERT INTO submissions (id, dataset_id, algorithm_name, version, status, created_at)
            VALUES
                (1, 1, 'LEOAlgo', 'v1.0', 'completed', CURRENT_TIMESTAMP),
                (2, 2, 'GEOAlgo', 'v1.0', 'completed', CURRENT_TIMESTAMP)
            """
        )

        integration_db.execute(
            """
            INSERT INTO submission_results (
                submission_id, true_positives, false_positives, false_negatives,
                precision, recall, f1_score, position_rms_km, velocity_rms_km_s
            ) VALUES
                (1, 80, 10, 10, 0.889, 0.889, 0.889, 15.0, 0.03),
                (2, 90, 5, 5, 0.947, 0.947, 0.947, 10.0, 0.02)
            """
        )

        # Filter by LEO
        leo_response = integration_client.get("/api/v1/leaderboard/?regime=LEO")
        assert leo_response.status_code == 200
        leo_leaderboard = leo_response.json()
        assert len(leo_leaderboard) == 1
        assert leo_leaderboard[0]["algorithm_name"] == "LEOAlgo"


class TestJobStatusPolling:
    """Integration tests for job status polling."""

    def test_job_status_updates(
        self,
        integration_client: TestClient,
    ):
        """Test that job status can be polled and updated."""
        # Create a job manually
        job_manager = get_job_manager()
        from backend_api.jobs import JobType

        job = job_manager.create_job(JobType.DATASET_GENERATION, {"test": True})

        # Poll job status
        response = integration_client.get(f"/api/v1/jobs/{job.id}")
        assert response.status_code == 200
        job_data = response.json()
        assert job_data["status"] == "pending"

        # Update job
        job_manager.update_job(job.id, status=JobStatus.RUNNING, progress=50)

        # Poll again
        response = integration_client.get(f"/api/v1/jobs/{job.id}")
        job_data = response.json()
        assert job_data["status"] == "running"
        assert job_data["progress"] == 50

    def test_job_not_found(self, integration_client: TestClient):
        """Test getting non-existent job returns 404."""
        response = integration_client.get("/api/v1/jobs/nonexistent-job-id")
        assert response.status_code == 404


class TestHealthCheck:
    """Integration tests for health check endpoint."""

    def test_health_check(self, integration_client: TestClient):
        """Test the health check endpoint."""
        response = integration_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestResultsListIntegration:
    """Integration tests for the results list endpoint."""

    def test_results_list_reflects_completed_submissions_with_results(
        self,
        integration_client: TestClient,
        integration_db: DatabaseManager,
    ):
        """Test that results list only shows completed submissions with results."""
        # Create dataset
        integration_db.execute(
            """
            INSERT INTO datasets (id, name, tier, orbital_regime, status)
            VALUES (1, 'Integration Test Dataset', 'T1', 'LEO', 'available')
            """
        )

        # Create submissions with various statuses
        integration_db.execute(
            """
            INSERT INTO submissions (id, dataset_id, algorithm_name, version, status, created_at, completed_at)
            VALUES
                (1, 1, 'CompletedAlgo', 'v1.0', 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                (2, 1, 'ProcessingAlgo', 'v1.0', 'processing', CURRENT_TIMESTAMP, NULL),
                (3, 1, 'QueuedAlgo', 'v1.0', 'queued', CURRENT_TIMESTAMP, NULL)
            """
        )

        # Only add results for completed submission
        integration_db.execute(
            """
            INSERT INTO submission_results (
                submission_id, true_positives, false_positives, false_negatives,
                precision, recall, f1_score, position_rms_km, velocity_rms_km_s
            ) VALUES (1, 80, 10, 10, 0.889, 0.889, 0.889, 15.0, 0.03)
            """
        )

        # Get results list
        response = integration_client.get("/api/v1/results/")
        assert response.status_code == 200

        results = response.json()
        # Only the completed submission with results should appear
        assert len(results) == 1
        assert results[0]["submission_id"] == "1"
        assert results[0]["algorithm_name"] == "CompletedAlgo"

    def test_results_list_ranking_calculated_correctly(
        self,
        integration_client: TestClient,
        integration_db: DatabaseManager,
    ):
        """Test that ranking is calculated correctly within datasets."""
        # Create two datasets
        integration_db.execute(
            """
            INSERT INTO datasets (id, name, tier, orbital_regime, status)
            VALUES
                (1, 'Dataset A', 'T1', 'LEO', 'available'),
                (2, 'Dataset B', 'T1', 'GEO', 'available')
            """
        )

        # Create submissions
        integration_db.execute(
            """
            INSERT INTO submissions (id, dataset_id, algorithm_name, version, status, created_at, completed_at)
            VALUES
                (1, 1, 'AlgoLow', 'v1.0', 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                (2, 1, 'AlgoHigh', 'v1.0', 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                (3, 1, 'AlgoMid', 'v1.0', 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                (4, 2, 'AlgoOther', 'v1.0', 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        )

        # Create results with different F1 scores
        integration_db.execute(
            """
            INSERT INTO submission_results (
                submission_id, true_positives, false_positives, false_negatives,
                precision, recall, f1_score, position_rms_km, velocity_rms_km_s
            ) VALUES
                (1, 70, 15, 15, 0.824, 0.824, 0.700, 20.0, 0.04),
                (2, 95, 3, 2, 0.969, 0.979, 0.950, 8.0, 0.015),
                (3, 85, 8, 7, 0.914, 0.924, 0.850, 12.0, 0.025),
                (4, 80, 10, 10, 0.889, 0.889, 0.889, 15.0, 0.03)
            """
        )

        # Get results for dataset 1
        response = integration_client.get("/api/v1/results/?dataset_id=1")
        assert response.status_code == 200

        results = response.json()
        assert len(results) == 3

        # Find each algorithm's result and check rank
        results_by_algo = {r["algorithm_name"]: r for r in results}

        # AlgoHigh has highest F1 (0.950) -> rank 1
        assert results_by_algo["AlgoHigh"]["rank"] == 1
        # AlgoMid has mid F1 (0.850) -> rank 2
        assert results_by_algo["AlgoMid"]["rank"] == 2
        # AlgoLow has lowest F1 (0.700) -> rank 3
        assert results_by_algo["AlgoLow"]["rank"] == 3

        # Check that dataset 2's submission has its own rank (rank 1 in its dataset)
        response2 = integration_client.get("/api/v1/results/?dataset_id=2")
        results2 = response2.json()
        assert len(results2) == 1
        assert results2[0]["rank"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
