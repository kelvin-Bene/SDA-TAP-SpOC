"""
Tests for the Leaderboard API router.

Tests the GET /api/v1/leaderboard endpoints for retrieving
ranked submissions and statistics.
"""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from uct_benchmark.database.connection import DatabaseManager

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def db_with_leaderboard_data():
    """Create a database with multiple submissions for leaderboard testing."""
    # Use a temp file instead of in-memory to avoid thread isolation issues
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_leaderboard.duckdb"

    db = DatabaseManager(db_path=db_path)
    db.initialize()

    # Create sample datasets with different regimes and tiers
    db.execute(
        """
        INSERT INTO datasets (id, name, code, tier, orbital_regime, status, observation_count, satellite_count, created_at)
        VALUES
            (1, 'LEO T1 Dataset', 'LEO_T1', 'T1', 'LEO', 'available', 1000, 5, CURRENT_TIMESTAMP),
            (2, 'GEO T2 Dataset', 'GEO_T2', 'T2', 'GEO', 'available', 500, 3, CURRENT_TIMESTAMP),
            (3, 'LEO T2 Dataset', 'LEO_T2', 'T2', 'LEO', 'available', 800, 4, CURRENT_TIMESTAMP)
        """
    )

    # Create submissions with various algorithms and scores
    now = datetime.utcnow()
    week_ago = now - timedelta(days=5)
    month_ago = now - timedelta(days=20)

    db.execute(
        """
        INSERT INTO submissions (id, dataset_id, algorithm_name, version, status, created_at, completed_at)
        VALUES
            (1, 1, 'AlgoA', 'v1.0', 'completed', ?, ?),
            (2, 1, 'AlgoB', 'v1.0', 'completed', ?, ?),
            (3, 1, 'AlgoA', 'v2.0', 'completed', ?, ?),
            (4, 2, 'AlgoC', 'v1.0', 'completed', ?, ?),
            (5, 2, 'AlgoA', 'v1.0', 'completed', ?, ?),
            (6, 3, 'AlgoB', 'v2.0', 'completed', ?, ?),
            (7, 1, 'AlgoD', 'v1.0', 'processing', ?, NULL)
        """,
        (
            now,
            now,  # submission 1
            week_ago,
            week_ago,  # submission 2
            now,
            now,  # submission 3
            month_ago,
            month_ago,  # submission 4
            now,
            now,  # submission 5
            week_ago,
            week_ago,  # submission 6
            now,  # submission 7 (processing)
        ),
    )

    # Create results with varying scores
    db.execute(
        """
        INSERT INTO submission_results (
            submission_id, true_positives, false_positives, false_negatives,
            precision, recall, f1_score, position_rms_km, velocity_rms_km_s
        ) VALUES
            (1, 850, 50, 100, 0.944, 0.895, 0.919, 12.5, 0.025),
            (2, 800, 100, 100, 0.889, 0.889, 0.889, 15.0, 0.030),
            (3, 900, 20, 80, 0.978, 0.918, 0.947, 10.0, 0.020),
            (4, 450, 50, 50, 0.900, 0.900, 0.900, 20.0, 0.040),
            (5, 480, 20, 50, 0.960, 0.906, 0.932, 18.0, 0.035),
            (6, 750, 50, 100, 0.938, 0.882, 0.909, 14.0, 0.028)
        """
    )

    yield db, temp_dir

    # Cleanup
    db.close()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client_with_leaderboard(db_with_leaderboard_data) -> TestClient:
    """Create a test client with leaderboard data."""
    db, temp_dir = db_with_leaderboard_data

    import backend_api.database as db_module

    original_db = db_module._db_manager
    db_module._db_manager = db

    from backend_api.main import app

    with patch("backend_api.main.init_database", return_value=db):
        with patch("backend_api.main.close_database"):
            with patch("backend_api.main.init_job_manager", return_value=MagicMock()):
                with patch("backend_api.main.shutdown_executor"):
                    with TestClient(app) as client:
                        yield client

    db_module._db_manager = original_db


@pytest.fixture
def empty_db():
    """Create an empty database for testing edge cases."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_empty.duckdb"

    db = DatabaseManager(db_path=db_path)
    db.initialize()

    yield db, temp_dir

    db.close()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client_empty(empty_db) -> TestClient:
    """Create a test client with empty database."""
    db, temp_dir = empty_db

    import backend_api.database as db_module

    original_db = db_module._db_manager
    db_module._db_manager = db

    from backend_api.main import app

    with patch("backend_api.main.init_database", return_value=db):
        with patch("backend_api.main.close_database"):
            with patch("backend_api.main.init_job_manager", return_value=MagicMock()):
                with patch("backend_api.main.shutdown_executor"):
                    with TestClient(app) as client:
                        yield client

    db_module._db_manager = original_db


# =============================================================================
# GET /api/v1/leaderboard/ TESTS
# =============================================================================


class TestGetLeaderboard:
    """Tests for GET /api/v1/leaderboard/."""

    def test_get_leaderboard_all(self, client_with_leaderboard):
        """Test getting full leaderboard without filters."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/")

        assert response.status_code == 200
        data = response.json()

        assert "entries" in data
        assert "total_entries" in data
        assert "last_updated" in data

        # Should have 6 completed submissions with results
        assert data["total_entries"] == 6
        assert len(data["entries"]) == 6

    def test_get_leaderboard_ranked_by_f1(self, client_with_leaderboard):
        """Test that leaderboard is ranked by F1 score descending."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/")

        assert response.status_code == 200
        entries = response.json()["entries"]

        # Check ranking order (highest F1 first)
        f1_scores = [e["f1_score"] for e in entries]
        assert f1_scores == sorted(f1_scores, reverse=True)

        # First entry should be AlgoA v2.0 with F1=0.947
        assert entries[0]["rank"] == 1
        assert entries[0]["f1_score"] == pytest.approx(0.947, rel=1e-3)

    def test_get_leaderboard_filter_by_dataset(self, client_with_leaderboard):
        """Test filtering leaderboard by dataset ID."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/?dataset_id=1")

        assert response.status_code == 200
        data = response.json()

        # Dataset 1 has 3 completed submissions
        assert data["total_entries"] == 3
        assert data["dataset_id"] == "1"

    def test_get_leaderboard_filter_by_regime(self, client_with_leaderboard):
        """Test filtering leaderboard by orbital regime."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/?regime=LEO")

        assert response.status_code == 200
        data = response.json()

        # LEO datasets (1 and 3) have 4 submissions total
        assert data["total_entries"] == 4

    def test_get_leaderboard_filter_by_tier(self, client_with_leaderboard):
        """Test filtering leaderboard by data tier."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/?tier=T1")

        assert response.status_code == 200
        data = response.json()

        # Only dataset 1 is T1, with 3 submissions
        assert data["total_entries"] == 3

    def test_get_leaderboard_combined_filters(self, client_with_leaderboard):
        """Test combining multiple filters."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/?regime=LEO&tier=T2")

        assert response.status_code == 200
        data = response.json()

        # Only dataset 3 is LEO + T2, with 1 submission
        assert data["total_entries"] == 1

    def test_get_leaderboard_limit(self, client_with_leaderboard):
        """Test limiting number of entries returned."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/?limit=3")

        assert response.status_code == 200
        data = response.json()

        # Should return only top 3
        assert len(data["entries"]) == 3
        assert data["entries"][0]["rank"] == 1
        assert data["entries"][2]["rank"] == 3

    def test_get_leaderboard_empty(self, client_empty):
        """Test leaderboard with no data."""
        response = client_empty.get("/api/v1/leaderboard/")

        assert response.status_code == 200
        data = response.json()

        assert data["total_entries"] == 0
        assert data["entries"] == []

    def test_get_leaderboard_entry_fields(self, client_with_leaderboard):
        """Test that leaderboard entries contain expected fields."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/")

        assert response.status_code == 200
        entry = response.json()["entries"][0]

        assert "rank" in entry
        assert "algorithm_name" in entry
        assert "version" in entry
        assert "f1_score" in entry
        assert "precision" in entry
        assert "recall" in entry
        assert "position_rms_km" in entry
        assert "submission_id" in entry
        assert "submitted_at" in entry


# =============================================================================
# GET /api/v1/leaderboard/history TESTS
# =============================================================================


class TestGetLeaderboardHistory:
    """Tests for GET /api/v1/leaderboard/history."""

    def test_get_history_default(self, client_with_leaderboard):
        """Test getting history with default parameters."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/history")

        assert response.status_code == 200
        data = response.json()

        assert "history" in data
        assert "period_days" in data
        assert data["period_days"] == 30  # Default

    def test_get_history_custom_days(self, client_with_leaderboard):
        """Test getting history with custom day range."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/history?days=7")

        assert response.status_code == 200
        data = response.json()

        assert data["period_days"] == 7

    def test_get_history_filter_by_dataset(self, client_with_leaderboard):
        """Test filtering history by dataset."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/history?dataset_id=1")

        assert response.status_code == 200
        data = response.json()

        assert data["dataset_id"] == "1"

    def test_get_history_structure(self, client_with_leaderboard):
        """Test that history entries have expected structure."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/history")

        assert response.status_code == 200
        history = response.json()["history"]

        if len(history) > 0:
            entry = history[0]
            assert "date" in entry
            assert "algorithm_name" in entry
            assert "best_f1" in entry


# =============================================================================
# GET /api/v1/leaderboard/statistics TESTS
# =============================================================================


class TestGetLeaderboardStatistics:
    """Tests for GET /api/v1/leaderboard/statistics."""

    def test_get_statistics_all(self, client_with_leaderboard):
        """Test getting aggregate statistics."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/statistics")

        assert response.status_code == 200
        data = response.json()

        assert "total_submissions" in data
        assert "unique_algorithms" in data
        assert "average_score" in data
        assert "best_score" in data
        assert "worst_score" in data
        assert "submission_trend" in data

    def test_get_statistics_values(self, client_with_leaderboard):
        """Test that statistics values are correct."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/statistics")

        assert response.status_code == 200
        data = response.json()

        # 6 completed submissions
        assert data["total_submissions"] == 6

        # 4 unique algorithms (AlgoA, AlgoB, AlgoC, AlgoD but AlgoD has no results)
        assert data["unique_algorithms"] >= 3

        # Best F1 is 0.947
        assert data["best_score"] == pytest.approx(0.947, rel=1e-2)

        # Worst F1 is 0.889
        assert data["worst_score"] == pytest.approx(0.889, rel=1e-2)

    def test_get_statistics_filter_by_dataset(self, client_with_leaderboard):
        """Test filtering statistics by dataset."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/statistics?dataset_id=1")

        assert response.status_code == 200
        data = response.json()

        assert data["dataset_id"] == "1"
        # Dataset 1 has 3 submissions
        assert data["total_submissions"] == 3

    def test_get_statistics_empty(self, client_empty):
        """Test statistics with no data."""
        response = client_empty.get("/api/v1/leaderboard/statistics")

        assert response.status_code == 200
        data = response.json()

        assert data["total_submissions"] == 0
        assert data["unique_algorithms"] == 0
        assert data["average_score"] == 0
        assert data["submission_trend"] == "stable"

    def test_get_statistics_trend(self, client_with_leaderboard):
        """Test that trend is calculated."""
        response = client_with_leaderboard.get("/api/v1/leaderboard/statistics")

        assert response.status_code == 200
        data = response.json()

        # Trend should be one of the expected values
        assert data["submission_trend"] in ["increasing", "decreasing", "stable"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
