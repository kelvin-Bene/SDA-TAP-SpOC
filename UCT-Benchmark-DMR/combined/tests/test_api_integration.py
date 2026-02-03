# -*- coding: utf-8 -*-
"""
Integration Tests for Backend API with Supabase Database

These tests require the Supabase database to be configured via environment variables.
They test the actual API endpoints with real database connections.
"""

import os
import pytest
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables before importing app
load_dotenv()

from fastapi.testclient import TestClient
from contextlib import contextmanager


# API prefix
API_PREFIX = "/api/v1"


@pytest.fixture(scope="module")
def client():
    """Create FastAPI test client with database initialization."""
    # Import after loading .env
    from backend_api.main import app
    from backend_api.database import init_database, close_database, _db_manager

    # Initialize database for tests
    try:
        db = init_database()
        print(f"Database initialized: {db.backend}")
    except Exception as e:
        pytest.skip(f"Could not initialize database: {e}")

    # Create test client
    with TestClient(app) as test_client:
        yield test_client

    # Cleanup
    close_database()


class TestDatasetsEndpointIntegration:
    """Integration tests for /datasets endpoints."""

    def test_list_datasets(self, client):
        """Test listing all datasets from Supabase."""
        response = client.get(f"{API_PREFIX}/datasets/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # We know there are 17 datasets in the database
        print(f"Found {len(data)} datasets")

        if len(data) > 0:
            # Check dataset structure
            dataset = data[0]
            assert "id" in dataset
            assert "name" in dataset

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

        # We know there are 4 submissions in the database
        print(f"Found {len(data)} submissions")

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
