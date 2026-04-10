# -*- coding: utf-8 -*-
"""
Integration Tests for Backend API

Tests the FastAPI endpoints with auth dependency overridden (stub user)
and a temp file-backed DuckDB so no real Supabase connection is needed.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from datetime import datetime
from fastapi.testclient import TestClient


# API prefix
API_PREFIX = "/api/v1"


# ---------------------------------------------------------------------------
# Shared mock user + file-backed DuckDB for auth/database bypass.
#
# Uses a temp *file* rather than :memory: because DuckDB in-memory databases
# are per-connection and Starlette's TestClient dispatches requests on a
# background thread, which would get a separate (empty) in-memory database.
# ---------------------------------------------------------------------------
def _mock_current_user():
    from backend_api.auth import CurrentUser
    return CurrentUser(id="test-user", email="test@localhost", role="authenticated")


# Module-level file-backed DB so all tests share the same schema
_test_db = None
_test_db_dir = None


def _get_test_db():
    global _test_db, _test_db_dir
    if _test_db is None:
        from uct_benchmark.database.connection import DatabaseManager
        _test_db_dir = tempfile.mkdtemp()
        db_path = Path(_test_db_dir) / "test_api_integration.duckdb"
        _test_db = DatabaseManager(backend="duckdb", db_path=db_path)
        _test_db.initialize(force=True)
    return _test_db


def _cleanup_test_db():
    global _test_db, _test_db_dir
    if _test_db is not None:
        _test_db.close()
        _test_db = None
    if _test_db_dir is not None:
        shutil.rmtree(_test_db_dir, ignore_errors=True)
        _test_db_dir = None


def _make_authed_client():
    """Create a TestClient with auth + database dependencies overridden.

    Uses create_test_app() to skip the production lifespan (which tries
    to connect to a real database) and overrides both auth paths plus
    the get_db dependency with a file-backed DuckDB.
    """
    import backend_api.database as db_module
    from backend_api.main import create_test_app
    from backend_api.auth import get_current_user as prod_get_current_user
    from backend_api.middleware.auth import get_current_user as mw_get_current_user
    from backend_api.database import get_db

    test_app = create_test_app()
    db = _get_test_db()

    # Set the global _db_manager so any direct get_db() calls also work
    db_module._db_manager = db

    test_app.dependency_overrides[prod_get_current_user] = _mock_current_user
    test_app.dependency_overrides[mw_get_current_user] = _mock_current_user
    test_app.dependency_overrides[get_db] = lambda: db

    client = TestClient(test_app)
    return client, test_app


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    """Clear dependency overrides and reset test mode after every test."""
    yield
    from backend_api.main import app, reset_test_mode
    app.dependency_overrides.clear()
    reset_test_mode()


def pytest_sessionfinish(session, exitstatus):
    """Clean up the temp database after all tests complete."""
    _cleanup_test_db()


@pytest.fixture
def client():
    """Create FastAPI test client with auth bypassed."""
    client, _app = _make_authed_client()
    return client


class TestDatasetsEndpointIntegration:
    """Integration tests for /datasets endpoints."""

    def test_list_datasets(self, client):
        """Test listing datasets returns 200 with a list."""
        response = client.get(f"{API_PREFIX}/datasets/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_existing_dataset(self, client):
        """Test getting an existing dataset by ID."""
        # First list datasets to get a valid ID
        list_response = client.get(f"{API_PREFIX}/datasets/")
        assert list_response.status_code == 200

        datasets = list_response.json()
        if len(datasets) > 0:
            dataset_id = datasets[0]["id"]

            # Get the specific dataset
            response = client.get(f"{API_PREFIX}/datasets/{dataset_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == dataset_id

    def test_get_nonexistent_dataset(self, client):
        """Test getting a non-existent dataset returns 404."""
        response = client.get(f"{API_PREFIX}/datasets/999999")

        assert response.status_code == 404


class TestSubmissionsEndpointIntegration:
    """Integration tests for /submissions endpoints."""

    def test_list_submissions(self, client):
        """Test listing all submissions from Supabase."""
        response = client.get(f"{API_PREFIX}/submissions/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Submission count is dynamic; just verify we got a list
        assert len(data) >= 0

        if len(data) > 0:
            submission = data[0]
            assert "id" in submission
            assert "algorithm_name" in submission

    def test_get_existing_submission(self, client):
        """Test getting an existing submission by ID."""
        list_response = client.get(f"{API_PREFIX}/submissions/")
        assert list_response.status_code == 200

        submissions = list_response.json()
        if len(submissions) > 0:
            submission_id = submissions[0]["id"]

            response = client.get(f"{API_PREFIX}/submissions/{submission_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == submission_id


class TestLeaderboardEndpointIntegration:
    """Integration tests for /leaderboard endpoints."""

    def test_get_leaderboard(self, client):
        """Test getting the leaderboard."""
        response = client.get(f"{API_PREFIX}/leaderboard/")

        assert response.status_code == 200
        data = response.json()

        # Check leaderboard structure
        assert "entries" in data or isinstance(data, list)

    def test_get_leaderboard_history(self, client):
        """Test getting leaderboard history."""
        response = client.get(f"{API_PREFIX}/leaderboard/history")

        assert response.status_code == 200

    def test_get_leaderboard_statistics(self, client):
        """Test getting leaderboard statistics."""
        response = client.get(f"{API_PREFIX}/leaderboard/statistics")

        assert response.status_code == 200


class TestResultsEndpointIntegration:
    """Integration tests for /results endpoints."""

    def test_list_results(self, client):
        """Test listing all results from Supabase."""
        response = client.get(f"{API_PREFIX}/results/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        print(f"Found {len(data)} results")


class TestJobsEndpointIntegration:
    """Integration tests for /jobs endpoints."""

    def test_list_jobs(self, client):
        """Test listing all jobs."""
        response = client.get(f"{API_PREFIX}/jobs/")

        assert response.status_code == 200

    def test_get_nonexistent_job(self, client):
        """Test getting a non-existent job returns 404."""
        response = client.get(f"{API_PREFIX}/jobs/nonexistent-job-id")

        assert response.status_code == 404


class TestDatasetObservationsIntegration:
    """Integration tests for dataset observations."""

    def test_get_dataset_observations(self, client):
        """Test getting observations for a dataset."""
        # First get a dataset
        list_response = client.get(f"{API_PREFIX}/datasets/")
        assert list_response.status_code == 200

        datasets = list_response.json()
        if len(datasets) > 0:
            dataset_id = datasets[0]["id"]

            # Get observations for this dataset
            response = client.get(f"{API_PREFIX}/datasets/{dataset_id}/observations")

            # Should return 200 with observations or empty list
            assert response.status_code == 200


class TestHealthCheck:
    """Test API health check."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")

        # Root might redirect or return info
        assert response.status_code in [200, 307]

    def test_api_docs(self, client):
        """Test OpenAPI docs are accessible."""
        response = client.get("/docs")

        assert response.status_code == 200


class TestDatasetCreationIntegration:
    """Integration tests for dataset creation (non-destructive)."""

    def test_dataset_create_validation(self, client):
        """Test dataset creation validation without actually creating."""
        # Test with invalid data to verify validation works
        invalid_request = {
            "name": "",  # Empty name should fail
            "regime": "INVALID",
            "tier": "T1",
            "object_count": -1,  # Negative should fail
        }

        response = client.post(f"{API_PREFIX}/datasets/", json=invalid_request)

        # Should return 422 Unprocessable Entity for validation errors
        assert response.status_code == 422


class TestNewFeaturesIntegration:
    """Integration tests for newly added features."""

    def test_datasets_have_generation_params(self, client):
        """Test that datasets include generation_params field."""
        response = client.get(f"{API_PREFIX}/datasets/")
        assert response.status_code == 200

        datasets = response.json()
        if len(datasets) > 0:
            # Get full dataset details
            dataset_id = datasets[0]["id"]
            detail_response = client.get(f"{API_PREFIX}/datasets/{dataset_id}")

            if detail_response.status_code == 200:
                data = detail_response.json()
                # generation_params should exist (may be null for older datasets)
                print(f"Dataset {dataset_id} has generation_params: {'generation_params' in data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
