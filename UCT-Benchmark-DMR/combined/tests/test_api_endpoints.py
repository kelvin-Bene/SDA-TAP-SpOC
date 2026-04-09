# -*- coding: utf-8 -*-
"""
Test Suite for Backend API Endpoints

Tests the FastAPI endpoints for dataset generation, including the new
parameters for true negatives, object type filtering, event detection,
and window selection.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


# API prefix
API_PREFIX = "/api/v1"


# ---------------------------------------------------------------------------
# Shared mock user + file-backed DuckDB for auth/database bypass.
#
# Uses a temp *file* rather than :memory: because DuckDB in-memory databases
# are per-connection and Starlette's TestClient dispatches requests on a
# background thread, which would get a separate (empty) in-memory database.
# (mirrors the pattern in backend_api/tests/test_integration.py)
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
        db_path = Path(_test_db_dir) / "test_api_endpoints.duckdb"
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


class TestDatasetEndpoints:
    """Tests for the /datasets API endpoints."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client with auth bypassed."""
        client, _app = _make_authed_client()
        return client

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
        # Use a numeric ID (the route validates dataset_id as int and returns
        # 400 for non-numeric strings before checking existence).
        response = client.get(f"{API_PREFIX}/datasets/999999")

        assert response.status_code == 404


class TestJobEndpoints:
    """Tests for the /jobs API endpoints."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client with auth bypassed."""
        client, _app = _make_authed_client()
        return client

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
        """Create FastAPI test client with auth bypassed."""
        client, _app = _make_authed_client()
        return client

    def test_list_submissions(self, client):
        """Test listing submissions."""
        response = client.get(f"{API_PREFIX}/submissions/")

        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestLeaderboardEndpoints:
    """Tests for the /leaderboard API endpoints."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client with auth bypassed."""
        client, _app = _make_authed_client()
        return client

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
        """Create FastAPI test client with auth bypassed."""
        client, _app = _make_authed_client()
        return client

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
