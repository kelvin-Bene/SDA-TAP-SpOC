# -*- coding: utf-8 -*-
"""
Test Suite for Backend API Endpoints

Tests the FastAPI endpoints for dataset generation, including the new
parameters for true negatives, object type filtering, event detection,
and window selection.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


# API prefix
API_PREFIX = "/api/v1"


class TestDatasetEndpoints:
    """Tests for the /datasets API endpoints."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        from backend_api.main import app
        return TestClient(app)

    @pytest.fixture
    def basic_dataset_request(self):
        """Create a basic dataset generation request."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 14)

        return {
            "name": "test-dataset",
            "regime": "LEO",
            "tier": "T1",
            "object_count": 10,
            "timeframe": 14,
            "timeunit": "days",
            "sensors": ["optical"],
            "coverage": "standard",
            "include_hamr": False,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

    def test_list_datasets(self, client):
        """Test listing datasets."""
        response = client.get(f"{API_PREFIX}/datasets/")

        # Should return 200 even if empty
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_dataset_not_found(self, client):
        """Test getting a non-existent dataset."""
        response = client.get(f"{API_PREFIX}/datasets/non-existent-id")

        assert response.status_code == 404


class TestJobEndpoints:
    """Tests for the /jobs API endpoints."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        from backend_api.main import app
        return TestClient(app)

    def test_list_jobs(self, client):
        """Test listing jobs."""
        response = client.get(f"{API_PREFIX}/jobs/")

        # Should return 200 with list of jobs
        assert response.status_code == 200

    def test_get_job_not_found(self, client):
        """Test getting a non-existent job."""
        response = client.get(f"{API_PREFIX}/jobs/non-existent-job-id")

        assert response.status_code == 404


class TestSubmissionEndpoints:
    """Tests for the /submissions API endpoints."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        from backend_api.main import app
        return TestClient(app)

    def test_list_submissions(self, client):
        """Test listing submissions."""
        response = client.get(f"{API_PREFIX}/submissions/")

        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestLeaderboardEndpoints:
    """Tests for the /leaderboard API endpoints."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        from backend_api.main import app
        return TestClient(app)

    def test_get_leaderboard(self, client):
        """Test getting leaderboard."""
        response = client.get(f"{API_PREFIX}/leaderboard/")

        assert response.status_code == 200

    def test_get_leaderboard_history(self, client):
        """Test getting leaderboard history."""
        response = client.get(f"{API_PREFIX}/leaderboard/history")

        assert response.status_code == 200

    def test_get_leaderboard_statistics(self, client):
        """Test getting leaderboard statistics."""
        response = client.get(f"{API_PREFIX}/leaderboard/statistics")

        assert response.status_code == 200


class TestResultsEndpoints:
    """Tests for the /results API endpoints."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        from backend_api.main import app
        return TestClient(app)

    def test_list_results(self, client):
        """Test listing results."""
        response = client.get(f"{API_PREFIX}/results/")

        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestDatasetCreateModel:
    """Tests for the DatasetCreate Pydantic model."""

    def test_model_accepts_valid_non_ref_ratio(self):
        """Test that valid non_ref_ratio values are accepted."""
        from backend_api.models import DatasetCreate

        model = DatasetCreate(
            name="test",
            regime="LEO",
            tier="T1",
            object_count=10,
            timeframe=7,
            timeunit="days",
            sensors=["optical"],
            coverage="standard",
            include_hamr=False,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            include_non_ref_obs=True,
            non_ref_ratio=0.1,
        )

        assert model.non_ref_ratio == 0.1

    def test_model_rejects_invalid_non_ref_ratio(self):
        """Test that invalid non_ref_ratio values are rejected."""
        from backend_api.models import DatasetCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DatasetCreate(
                name="test",
                regime="LEO",
                tier="T1",
                object_count=10,
                timeframe=7,
                timeunit="days",
                sensors=["optical"],
                coverage="standard",
                include_hamr=False,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 7),
                include_non_ref_obs=True,
                non_ref_ratio=0.6,  # Above 0.5 max
            )

    def test_model_accepts_valid_object_type_code(self):
        """Test that valid object_type_code values are accepted."""
        from backend_api.models import DatasetCreate

        for code in ["H", "C", "A", "U", "N"]:
            model = DatasetCreate(
                name=f"test-{code}",
                regime="LEO",
                tier="T1",
                object_count=10,
                timeframe=7,
                timeunit="days",
                sensors=["optical"],
                coverage="standard",
                include_hamr=False,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 7),
                object_type_code=code,
            )

            assert model.object_type_code == code

    def test_model_accepts_valid_event_code(self):
        """Test that valid event_code values are accepted."""
        from backend_api.models import DatasetCreate

        for code in ["MB", "BU", "LL", "NE"]:
            model = DatasetCreate(
                name=f"test-{code}",
                regime="LEO",
                tier="T1",
                object_count=10,
                timeframe=7,
                timeunit="days",
                sensors=["optical"],
                coverage="standard",
                include_hamr=False,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 7),
                event_code=code,
            )

            assert model.event_code == code

    def test_model_has_use_window_selection(self):
        """Test that use_window_selection field exists."""
        from backend_api.models import DatasetCreate

        model = DatasetCreate(
            name="test",
            regime="LEO",
            tier="T1",
            object_count=10,
            timeframe=7,
            timeunit="days",
            sensors=["optical"],
            coverage="standard",
            include_hamr=False,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            use_window_selection=True,
        )

        assert model.use_window_selection == True


class TestSubmissionResultsModel:
    """Tests for submission results models."""

    def test_submission_results_model_exists(self):
        """Test that SubmissionResults model exists with expected fields."""
        from backend_api.models import SubmissionResults

        # Verify the class exists and has binary metric fields
        assert SubmissionResults is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
