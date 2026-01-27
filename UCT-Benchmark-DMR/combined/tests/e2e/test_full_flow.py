"""
End-to-end tests for the full UCT Benchmark application flow.

These tests verify the complete user workflow from dataset generation
through submission and results viewing.

Run with: uv run pytest tests/e2e/test_full_flow.py -v

Note: These tests require the backend server to be running, or can be
modified to use TestClient for in-process testing.
"""

import json
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend_api.jobs import JobStatus, get_job_manager, init_job_manager
from uct_benchmark.database.connection import DatabaseManager

# Skip all e2e tests - they require a properly configured test environment with
# database initialization happening before the app lifespan starts. The app's
# lifespan creates its own database, overriding the test fixture's database.
# TODO: Refactor e2e tests to use a test-specific app configuration or
# environment variables to control database initialization.
pytestmark = pytest.mark.skip(
    reason="E2E tests require test infrastructure refactoring - "
    "app lifespan initializes separate database from test fixtures"
)


@pytest.fixture(scope="module")
def e2e_db() -> Generator[DatabaseManager, None, None]:
    """Create a fresh database for E2E testing."""
    db = DatabaseManager(in_memory=True)
    db.initialize()
    yield db
    db.close()


@pytest.fixture(scope="module")
def e2e_client(e2e_db: DatabaseManager) -> Generator[TestClient, None, None]:
    """Create a test client for E2E tests."""
    import backend_api.database as db_module
    from backend_api.database import get_db
    from backend_api.main import app

    # Override the global database manager directly to use our test database
    original_db_manager = db_module._db_manager
    db_module._db_manager = e2e_db

    def override_get_db():
        return e2e_db

    app.dependency_overrides[get_db] = override_get_db

    # Initialize job manager
    init_job_manager()

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    # Restore original (don't close e2e_db as it's managed by its own fixture)
    db_module._db_manager = original_db_manager


class TestFullDatasetFlow:
    """E2E tests for the complete dataset generation workflow."""

    @patch("backend_api.jobs.workers.run_dataset_generation")
    def test_complete_dataset_lifecycle(
        self,
        mock_generation: MagicMock,
        e2e_client: TestClient,
        e2e_db: DatabaseManager,
    ):
        """
        Test the complete dataset lifecycle:
        1. Create dataset request
        2. Poll job status until complete
        3. Verify dataset is available
        4. Download dataset
        """
        # Step 1: Create dataset
        create_response = e2e_client.post(
            "/api/v1/datasets/",
            json={
                "name": "E2E Test Dataset",
                "regime": "LEO",
                "tier": "T1",
                "object_count": 5,
                "timeframe": 7,
                "timeunit": "days",
                "sensors": ["optical"],
                "coverage": "standard",
                "include_hamr": False,
            },
        )

        assert create_response.status_code == 200
        dataset = create_response.json()
        dataset_id = dataset["id"]
        job_id = dataset["job_id"]

        assert dataset["status"] == "generating"
        assert job_id is not None

        # Step 2: Simulate job completion
        job_manager = get_job_manager()
        job_manager.update_job(job_id, status=JobStatus.RUNNING, progress=50)

        # Poll job - should show running
        job_response = e2e_client.get(f"/api/v1/jobs/{job_id}")
        assert job_response.json()["status"] == "running"

        # Complete the job
        job_manager.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result={"observation_count": 500, "satellite_count": 5},
        )

        # Update database to reflect completion
        e2e_db.execute(
            """
            UPDATE datasets
            SET status = 'available', observation_count = 500, satellite_count = 5
            WHERE id = ?
            """,
            (int(dataset_id),),
        )

        # Step 3: Verify dataset is available
        get_response = e2e_client.get(f"/api/v1/datasets/{dataset_id}")
        assert get_response.status_code == 200
        updated_dataset = get_response.json()
        assert updated_dataset["status"] == "available"
        assert updated_dataset["observation_count"] == 500

        # Step 4: Download dataset
        download_response = e2e_client.get(f"/api/v1/datasets/{dataset_id}/download")
        assert download_response.status_code == 200
        download_data = download_response.json()
        assert "dataset" in download_data
        assert download_data["dataset"]["name"] == "E2E Test Dataset"


class TestFullSubmissionFlow:
    """E2E tests for the complete submission and evaluation workflow."""

    @patch("backend_api.jobs.workers.run_evaluation_pipeline")
    def test_complete_submission_lifecycle(
        self,
        mock_evaluation: MagicMock,
        e2e_client: TestClient,
        e2e_db: DatabaseManager,
        tmp_path: Path,
    ):
        """
        Test the complete submission lifecycle:
        1. Create dataset (or use existing available one)
        2. Submit algorithm results
        3. Poll evaluation job status
        4. View results
        5. Check leaderboard position
        """
        # Step 1: Ensure we have an available dataset
        e2e_db.execute(
            """
            INSERT INTO datasets (id, name, tier, orbital_regime, status, observation_count, satellite_count, created_at)
            VALUES (100, 'Submission Test Dataset', 'T1', 'LEO', 'available', 1000, 10, CURRENT_TIMESTAMP)
            """
        )

        # Verify dataset exists
        dataset_response = e2e_client.get("/api/v1/datasets/100")
        assert dataset_response.status_code == 200
        assert dataset_response.json()["status"] == "available"

        # Step 2: Create submission file
        submission_data = {
            "algorithm": "E2E-TestAlgorithm",
            "version": "1.0.0",
            "predictions": [
                {"observation_id": f"obs-{i}", "track_id": i % 10, "confidence": 0.9 - (i * 0.01)}
                for i in range(100)
            ],
            "metadata": {
                "runtime_seconds": 45.2,
                "memory_mb": 512,
            },
        }
        submission_file = tmp_path / "e2e_submission.json"
        submission_file.write_text(json.dumps(submission_data))

        # Submit
        with open(submission_file, "rb") as f:
            submit_response = e2e_client.post(
                "/api/v1/submissions/",
                data={
                    "dataset_id": "100",
                    "algorithm_name": "E2E-TestAlgorithm",
                    "version": "v1.0",
                    "description": "End-to-end test submission",
                },
                files={"file": ("submission.json", f, "application/json")},
            )

        assert submit_response.status_code == 200
        submission = submit_response.json()
        submission_id = submission["id"]
        eval_job_id = submission["job_id"]

        assert submission["status"] == "queued"
        assert eval_job_id is not None

        # Step 3: Simulate evaluation
        job_manager = get_job_manager()
        job_manager.update_job(eval_job_id, status=JobStatus.RUNNING, progress=25)

        # Poll - should show running
        job_response = e2e_client.get(f"/api/v1/jobs/{eval_job_id}")
        assert job_response.json()["status"] == "running"

        # Complete evaluation
        job_manager.update_job(
            eval_job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result={
                "f1_score": 0.923,
                "precision": 0.945,
                "recall": 0.902,
            },
        )

        # Update database to reflect completion
        e2e_db.execute(
            """
            UPDATE submissions
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (int(submission_id),),
        )

        e2e_db.execute(
            """
            INSERT INTO submission_results (
                submission_id, true_positives, false_positives, false_negatives,
                precision, recall, f1_score, position_rms_km, velocity_rms_km_s
            ) VALUES (?, 902, 53, 98, 0.945, 0.902, 0.923, 11.5, 0.022)
            """,
            (int(submission_id),),
        )

        # Step 4: View results
        results_response = e2e_client.get(f"/api/v1/results/{submission_id}")
        assert results_response.status_code == 200

        results = results_response.json()
        assert results["f1_score"] == pytest.approx(0.923, rel=0.01)
        assert results["precision"] == pytest.approx(0.945, rel=0.01)
        assert results["recall"] == pytest.approx(0.902, rel=0.01)
        assert results["position_rms_km"] == pytest.approx(11.5, rel=0.1)

        # Step 5: Check leaderboard
        leaderboard_response = e2e_client.get("/api/v1/leaderboard/")
        assert leaderboard_response.status_code == 200

        leaderboard = leaderboard_response.json()
        # Our submission should be on the leaderboard
        algo_entries = [e for e in leaderboard if e["algorithm_name"] == "E2E-TestAlgorithm"]
        assert len(algo_entries) >= 1


class TestUserScenarios:
    """E2E tests for realistic user scenarios."""

    def test_browse_datasets(self, e2e_client: TestClient, e2e_db: DatabaseManager):
        """Test browsing and filtering datasets."""
        # Create multiple datasets for browsing
        e2e_db.execute(
            """
            INSERT INTO datasets (id, name, tier, orbital_regime, status, observation_count, created_at)
            VALUES
                (200, 'Browse LEO T1', 'T1', 'LEO', 'available', 500, CURRENT_TIMESTAMP),
                (201, 'Browse LEO T2', 'T2', 'LEO', 'available', 750, CURRENT_TIMESTAMP),
                (202, 'Browse GEO T1', 'T1', 'GEO', 'available', 300, CURRENT_TIMESTAMP),
                (203, 'Browse MEO T3', 'T3', 'MEO', 'generating', 0, CURRENT_TIMESTAMP)
            """
        )

        # Browse all datasets
        all_response = e2e_client.get("/api/v1/datasets/")
        assert all_response.status_code == 200
        assert len(all_response.json()) >= 4

        # Filter by regime
        leo_response = e2e_client.get("/api/v1/datasets/?regime=LEO")
        leo_datasets = leo_response.json()
        assert all(d["regime"] == "LEO" for d in leo_datasets)

        # Filter by tier
        t1_response = e2e_client.get("/api/v1/datasets/?tier=T1")
        t1_datasets = t1_response.json()
        assert all(d["tier"] == "T1" for d in t1_datasets)

        # Filter by status
        available_response = e2e_client.get("/api/v1/datasets/?status=available")
        available_datasets = available_response.json()
        assert all(d["status"] == "available" for d in available_datasets)

    def test_view_submission_history(self, e2e_client: TestClient, e2e_db: DatabaseManager):
        """Test viewing user's submission history."""
        # Create submission history
        e2e_db.execute(
            """
            INSERT INTO datasets (id, name, tier, orbital_regime, status, created_at)
            VALUES (300, 'History Dataset', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)
            """
        )

        e2e_db.execute(
            """
            INSERT INTO submissions (id, dataset_id, algorithm_name, version, status, created_at)
            VALUES
                (300, 300, 'UserAlgo', 'v1.0', 'completed', '2025-01-01 10:00:00'),
                (301, 300, 'UserAlgo', 'v1.1', 'completed', '2025-01-02 10:00:00'),
                (302, 300, 'UserAlgo', 'v2.0', 'processing', '2025-01-03 10:00:00')
            """
        )

        e2e_db.execute(
            """
            INSERT INTO submission_results (submission_id, f1_score, precision, recall, position_rms_km, velocity_rms_km_s)
            VALUES
                (300, 0.85, 0.88, 0.82, 15.0, 0.03),
                (301, 0.89, 0.91, 0.87, 12.0, 0.025)
            """
        )

        # Get all submissions
        response = e2e_client.get("/api/v1/submissions/")
        assert response.status_code == 200

        submissions = response.json()
        user_submissions = [s for s in submissions if s["algorithm_name"] == "UserAlgo"]
        assert len(user_submissions) >= 3

        # Check completed submissions have scores
        completed = [s for s in user_submissions if s["status"] == "completed"]
        assert all(s.get("score") is not None for s in completed)

    def test_compare_algorithms_on_leaderboard(
        self,
        e2e_client: TestClient,
        e2e_db: DatabaseManager,
    ):
        """Test comparing different algorithms on the leaderboard."""
        # Create competition dataset
        e2e_db.execute(
            """
            INSERT INTO datasets (id, name, tier, orbital_regime, status, created_at)
            VALUES (400, 'Competition Dataset', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)
            """
        )

        # Create competing submissions
        e2e_db.execute(
            """
            INSERT INTO submissions (id, dataset_id, algorithm_name, version, status, created_at)
            VALUES
                (400, 400, 'TeamA-UCT', 'v1.0', 'completed', CURRENT_TIMESTAMP),
                (401, 400, 'TeamB-Tracker', 'v2.1', 'completed', CURRENT_TIMESTAMP),
                (402, 400, 'TeamC-ML', 'v1.0', 'completed', CURRENT_TIMESTAMP)
            """
        )

        e2e_db.execute(
            """
            INSERT INTO submission_results (submission_id, f1_score, precision, recall, position_rms_km, velocity_rms_km_s)
            VALUES
                (400, 0.92, 0.94, 0.90, 10.5, 0.020),
                (401, 0.88, 0.91, 0.85, 14.0, 0.028),
                (402, 0.95, 0.96, 0.94, 8.0, 0.015)
            """
        )

        # Get leaderboard
        response = e2e_client.get("/api/v1/leaderboard/")
        assert response.status_code == 200

        leaderboard = response.json()

        # Find our competing algorithms
        competition_entries = [
            e
            for e in leaderboard
            if e["algorithm_name"] in ("TeamA-UCT", "TeamB-Tracker", "TeamC-ML")
        ]

        # Sort by F1 score to verify ranking
        sorted_entries = sorted(competition_entries, key=lambda x: x["f1_score"], reverse=True)

        # TeamC-ML should be ranked highest with 0.95 F1
        if sorted_entries:
            assert sorted_entries[0]["algorithm_name"] == "TeamC-ML"


class TestErrorHandling:
    """E2E tests for error handling scenarios."""

    def test_submit_to_unavailable_dataset(
        self,
        e2e_client: TestClient,
        e2e_db: DatabaseManager,
        tmp_path: Path,
    ):
        """Test error when submitting to a generating dataset."""
        # Create a generating dataset
        e2e_db.execute(
            """
            INSERT INTO datasets (id, name, tier, orbital_regime, status, created_at)
            VALUES (500, 'Generating Dataset', 'T1', 'LEO', 'generating', CURRENT_TIMESTAMP)
            """
        )

        # Try to submit
        submission_file = tmp_path / "error_submission.json"
        submission_file.write_text('{"predictions": []}')

        with open(submission_file, "rb") as f:
            response = e2e_client.post(
                "/api/v1/submissions/",
                data={
                    "dataset_id": "500",
                    "algorithm_name": "ErrorTest",
                    "version": "v1.0",
                },
                files={"file": ("submission.json", f, "application/json")},
            )

        assert response.status_code == 400
        assert "not available" in response.json()["detail"].lower()

    def test_download_unavailable_dataset(self, e2e_client: TestClient, e2e_db: DatabaseManager):
        """Test error when downloading a generating dataset."""
        e2e_db.execute(
            """
            INSERT INTO datasets (id, name, tier, orbital_regime, status, created_at)
            VALUES (501, 'No Download Dataset', 'T1', 'LEO', 'generating', CURRENT_TIMESTAMP)
            """
        )

        response = e2e_client.get("/api/v1/datasets/501/download")
        assert response.status_code == 400
        assert "not available" in response.json()["detail"].lower()

    def test_access_nonexistent_resources(self, e2e_client: TestClient):
        """Test 404 errors for non-existent resources."""
        # Non-existent dataset
        response = e2e_client.get("/api/v1/datasets/99999")
        assert response.status_code == 404

        # Non-existent submission
        response = e2e_client.get("/api/v1/submissions/99999")
        assert response.status_code == 404

        # Non-existent results
        response = e2e_client.get("/api/v1/results/99999")
        assert response.status_code == 404

        # Non-existent job
        response = e2e_client.get("/api/v1/jobs/nonexistent-id")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
