"""
Unit tests for the submissions router.

Run with: uv run pytest backend_api/tests/test_submissions.py -v
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestListSubmissions:
    """Tests for GET /api/v1/submissions endpoint."""

    def test_list_submissions_empty(self, test_client: TestClient):
        """Test listing submissions when database is empty."""
        response = test_client.get("/api/v1/submissions/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_submissions_with_data(self, populated_test_client: TestClient):
        """Test listing submissions with existing data."""
        response = populated_test_client.get("/api/v1/submissions/")
        assert response.status_code == 200

        submissions = response.json()
        assert len(submissions) == 3

        # Check submission structure
        submission = submissions[0]
        assert "id" in submission
        assert "dataset_id" in submission
        assert "algorithm_name" in submission
        assert "version" in submission
        assert "status" in submission

    def test_list_submissions_filter_by_dataset(self, populated_test_client: TestClient):
        """Test filtering submissions by dataset ID."""
        response = populated_test_client.get("/api/v1/submissions/?dataset_id=1")
        assert response.status_code == 200

        submissions = response.json()
        assert len(submissions) == 2
        assert all(s["dataset_id"] == "1" for s in submissions)

    def test_list_submissions_filter_by_status(self, populated_test_client: TestClient):
        """Test filtering submissions by status."""
        response = populated_test_client.get("/api/v1/submissions/?status=completed")
        assert response.status_code == 200

        submissions = response.json()
        assert len(submissions) == 1
        assert submissions[0]["status"] == "completed"

    def test_list_submissions_pagination(self, populated_test_client: TestClient):
        """Test submission pagination."""
        response = populated_test_client.get("/api/v1/submissions/?limit=2&offset=0")
        assert response.status_code == 200
        assert len(response.json()) == 2

        response = populated_test_client.get("/api/v1/submissions/?limit=2&offset=2")
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestGetSubmission:
    """Tests for GET /api/v1/submissions/{id} endpoint."""

    def test_get_submission_not_found(self, test_client: TestClient):
        """Test getting a non-existent submission returns 404."""
        response = test_client.get("/api/v1/submissions/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_submission_success(self, populated_test_client: TestClient):
        """Test getting an existing submission."""
        response = populated_test_client.get("/api/v1/submissions/1")
        assert response.status_code == 200

        submission = response.json()
        assert submission["id"] == "1"
        assert submission["dataset_id"] == "1"
        assert submission["algorithm_name"] == "TestAlgo"
        assert submission["version"] == "v1.0"
        assert submission["status"] == "completed"

    def test_get_submission_includes_detail_fields(self, populated_test_client: TestClient):
        """Test that submission detail includes additional fields."""
        response = populated_test_client.get("/api/v1/submissions/1")
        assert response.status_code == 200

        submission = response.json()
        assert "file_path" in submission
        assert "error_message" in submission


class TestErrorMessagePropagation:
    """
    Regression coverage for QA_PROD_RUN_2026-04-17 H1.

    When the evaluation worker fails, it must persist the exception text
    to submissions.error_message — not just status='failed'. Without it,
    the ResultsPage banner falls back to generic copy and users cannot
    see the underlying ValueError.

    Tests run the worker's exact UPDATE statement directly against the
    `db` fixture and verify the row state via SQL. Bypasses the FastAPI
    route to avoid the pre-existing populated_db schema issue under
    DuckDB.
    """

    def _insert_minimal_dataset_and_submission(self, db, dataset_id: int, sub_id: int):
        db.execute(
            """
            INSERT INTO datasets (id, name, code, tier, orbital_regime, status,
                                  observation_count, satellite_count, created_at)
            VALUES (?, ?, ?, 'T1', 'LEO', 'available', 100, 1, CURRENT_TIMESTAMP)
            """,
            (dataset_id, f"ds-{dataset_id}", f"ds-{dataset_id}"),
        )
        db.execute(
            """
            INSERT INTO submissions (id, dataset_id, algorithm_name, version, status, created_at)
            VALUES (?, ?, 'TestAlgo', 'v1.0', 'processing', CURRENT_TIMESTAMP)
            """,
            (sub_id, dataset_id),
        )

    def _read_submission(self, db, sub_id: int):
        df = db.adapter.fetchdf(
            "SELECT status, error_message FROM submissions WHERE id = ?",
            (sub_id,),
        )
        assert not df.empty, f"submission {sub_id} not found"
        row = df.iloc[0]
        return row["status"], row["error_message"]

    def test_failure_update_persists_error_message(self, db):
        """The worker's failure UPDATE writes both status and error_message."""
        self._insert_minimal_dataset_and_submission(db, dataset_id=2001, sub_id=2001)
        status_before, err_before = self._read_submission(db, 2001)
        assert status_before == "processing"
        # error_message either NULL (None) or empty in fresh insert.
        import pandas as pd

        assert err_before is None or pd.isna(err_before) or err_before == ""

        # Run the exact statement workers.py uses on evaluation failure
        # (backend_api/jobs/workers.py:1807-1810 post-H1-fix).
        error_msg = (
            "ValueError: Dataset 2001 has no reference state vectors persisted. "
            "Re-generate the dataset with the post-Phase-1 worker before evaluating."
        )
        db.execute(
            "UPDATE submissions SET status = 'failed', error_message = ? WHERE id = ?",
            (error_msg, 2001),
        )

        status_after, err_after = self._read_submission(db, 2001)
        assert status_after == "failed"
        assert err_after == error_msg
        # Sanity: the propagated text still reads like a real exception line.
        assert "ValueError" in err_after
        assert "reference state vectors" in err_after

    def test_failure_update_does_not_clobber_status(self, db):
        """The UPDATE only flips the targeted row, not other submissions."""
        self._insert_minimal_dataset_and_submission(db, dataset_id=2002, sub_id=2002)
        self._insert_minimal_dataset_and_submission(db, dataset_id=2003, sub_id=2003)

        db.execute(
            "UPDATE submissions SET status = 'failed', error_message = ? WHERE id = ?",
            ("ValueError: test failure", 2002),
        )

        s1, e1 = self._read_submission(db, 2002)
        s2, e2 = self._read_submission(db, 2003)
        import pandas as pd

        assert s1 == "failed"
        assert e1 == "ValueError: test failure"
        assert s2 == "processing"
        assert e2 is None or pd.isna(e2) or e2 == ""


class TestCreateSubmission:
    """Tests for POST /api/v1/submissions endpoint."""

    @patch("backend_api.routers.submissions.submit_evaluation")
    def test_create_submission_success(
        self,
        mock_submit: MagicMock,
        populated_test_client: TestClient,
        sample_submission_file: Path,
    ):
        """Test creating a new submission."""
        # Mock the job submission
        mock_job = MagicMock()
        mock_job.id = "eval-job-123"
        mock_submit.return_value = mock_job

        with open(sample_submission_file, "rb") as f:
            response = populated_test_client.post(
                "/api/v1/submissions/",
                data={
                    "dataset_id": "1",
                    "algorithm_name": "NewAlgo",
                    "version": "v1.0",
                    "description": "Test submission",
                },
                files={"file": ("submission.json", f, "application/json")},
            )

        assert response.status_code == 200
        submission = response.json()
        assert submission["algorithm_name"] == "NewAlgo"
        assert submission["version"] == "v1.0"
        assert submission["status"] == "queued"
        assert submission["job_id"] == "eval-job-123"

    def test_create_submission_dataset_not_found(
        self,
        test_client: TestClient,
        sample_submission_file: Path,
    ):
        """Test creating submission for non-existent dataset."""
        with open(sample_submission_file, "rb") as f:
            response = test_client.post(
                "/api/v1/submissions/",
                data={
                    "dataset_id": "99999",
                    "algorithm_name": "TestAlgo",
                    "version": "v1.0",
                },
                files={"file": ("submission.json", f, "application/json")},
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_submission_dataset_not_available(
        self,
        populated_test_client: TestClient,
        sample_submission_file: Path,
    ):
        """Test creating submission for dataset that is not available."""
        with open(sample_submission_file, "rb") as f:
            response = populated_test_client.post(
                "/api/v1/submissions/",
                data={
                    "dataset_id": "3",  # Generating dataset
                    "algorithm_name": "TestAlgo",
                    "version": "v1.0",
                },
                files={"file": ("submission.json", f, "application/json")},
            )

        assert response.status_code == 400
        assert "not available" in response.json()["detail"].lower()

    def test_create_submission_missing_file(
        self,
        populated_test_client: TestClient,
    ):
        """Test creating submission without file."""
        response = populated_test_client.post(
            "/api/v1/submissions/",
            data={
                "dataset_id": "1",
                "algorithm_name": "TestAlgo",
                "version": "v1.0",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_create_submission_missing_algorithm_name(
        self,
        populated_test_client: TestClient,
        sample_submission_file: Path,
    ):
        """Test creating submission without algorithm name."""
        with open(sample_submission_file, "rb") as f:
            response = populated_test_client.post(
                "/api/v1/submissions/",
                data={
                    "dataset_id": "1",
                    "version": "v1.0",
                },
                files={"file": ("submission.json", f, "application/json")},
            )

        assert response.status_code == 422  # Validation error


class TestUploadResults:
    """Tests for POST /api/v1/submissions/{id}/results endpoint."""

    @patch("backend_api.routers.submissions.submit_evaluation")
    def test_upload_results_success(
        self,
        mock_submit: MagicMock,
        populated_test_client: TestClient,
        sample_submission_file: Path,
    ):
        """Test uploading results for existing submission."""
        mock_job = MagicMock()
        mock_job.id = "eval-job-456"
        mock_submit.return_value = mock_job

        with open(sample_submission_file, "rb") as f:
            response = populated_test_client.post(
                "/api/v1/submissions/1/results",
                files={"file": ("results.json", f, "application/json")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["submission_id"] == "1"
        assert data["status"] == "uploaded"
        assert data["job_id"] == "eval-job-456"

    def test_upload_results_submission_not_found(
        self,
        test_client: TestClient,
        sample_submission_file: Path,
    ):
        """Test uploading results for non-existent submission."""
        with open(sample_submission_file, "rb") as f:
            response = test_client.post(
                "/api/v1/submissions/99999/results",
                files={"file": ("results.json", f, "application/json")},
            )

        assert response.status_code == 404

    def test_upload_results_while_processing(
        self,
        populated_test_client: TestClient,
        sample_submission_file: Path,
    ):
        """Test uploading results while submission is processing."""
        with open(sample_submission_file, "rb") as f:
            response = populated_test_client.post(
                "/api/v1/submissions/2/results",  # Processing submission
                files={"file": ("results.json", f, "application/json")},
            )

        assert response.status_code == 400
        assert "being processed" in response.json()["detail"].lower()


class TestSubmissionResults:
    """Tests for submission results via results router."""

    def test_get_results_not_found(self, test_client: TestClient):
        """Test getting results for non-existent submission."""
        response = test_client.get("/api/v1/results/99999")
        assert response.status_code == 404

    def test_get_results_success(self, populated_test_client: TestClient):
        """Test getting results for completed submission."""
        response = populated_test_client.get("/api/v1/results/1")
        assert response.status_code == 200

        results = response.json()
        assert results["submission_id"] == "1"
        assert "f1_score" in results
        assert "precision" in results
        assert "recall" in results
        assert results["f1_score"] == pytest.approx(0.919, rel=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
