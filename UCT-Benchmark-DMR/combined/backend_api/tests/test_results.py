"""
Tests for the Results API router.

Tests the GET /api/v1/results endpoints for retrieving
submission evaluation results.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from uct_benchmark.database.connection import DatabaseManager

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def db_with_results():
    """Create a database with submissions and results for testing."""
    # Use a temp file instead of in-memory to avoid thread isolation issues
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_results.duckdb"

    db = DatabaseManager(db_path=db_path)
    db.initialize()

    # Create sample dataset
    db.execute(
        """
        INSERT INTO datasets (id, name, code, tier, orbital_regime, status, observation_count, satellite_count, created_at)
        VALUES (1, 'Test Dataset', 'TEST_T1', 'T1', 'LEO', 'available', 1000, 5, CURRENT_TIMESTAMP)
        """
    )

    # Create submissions with various statuses
    db.execute(
        """
        INSERT INTO submissions (id, dataset_id, algorithm_name, version, status, created_at, completed_at)
        VALUES
            (1, 1, 'AlgoA', 'v1.0', 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            (2, 1, 'AlgoB', 'v1.0', 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            (3, 1, 'AlgoC', 'v1.0', 'processing', CURRENT_TIMESTAMP, NULL),
            (4, 1, 'AlgoA', 'v2.0', 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
    )

    # Create results with different scores for ranking tests
    raw_results_1 = json.dumps(
        {
            "per_satellite": [
                {
                    "satellite_id": "25544",
                    "status": "TP",
                    "observations_used": 100,
                    "total_observations": 120,
                    "position_error_km": 5.2,
                },
                {
                    "satellite_id": "25545",
                    "status": "TP",
                    "observations_used": 80,
                    "total_observations": 100,
                    "position_error_km": 3.1,
                },
            ],
            "per_track": [{"track_id": 1, "match": True}],
            "temporal_breakdown": [{"hour": 0, "accuracy": 0.95}],
            "orbit_plots": [{"x": 1, "y": 2}],
            "error_distribution": [0.1, 0.2, 0.3],
            "temporal_analysis": [{"time": "2024-01-01", "error": 0.1}],
        }
    )

    raw_results_2 = json.dumps(
        {
            "per_satellite": [
                {
                    "satellite_id": "25544",
                    "status": "TP",
                    "observations_used": 90,
                    "total_observations": 100,
                },
            ],
        }
    )

    db.execute(
        """
        INSERT INTO submission_results (
            submission_id, true_positives, false_positives, false_negatives,
            precision, recall, f1_score, position_rms_km, velocity_rms_km_s,
            mahalanobis_distance, ra_residual_rms_arcsec, dec_residual_rms_arcsec,
            raw_results, processing_time_seconds
        ) VALUES
            (1, 850, 50, 100, 0.944, 0.895, 0.919, 12.5, 0.025, 1.2, 0.5, 0.6, ?, 45.5),
            (2, 800, 100, 100, 0.889, 0.889, 0.889, 15.0, 0.030, 1.5, 0.7, 0.8, ?, 30.0),
            (4, 900, 20, 80, 0.978, 0.918, 0.947, 10.0, 0.020, 1.0, 0.4, 0.5, NULL, 60.0)
        """,
        (raw_results_1, raw_results_2),
    )

    yield db

    # Cleanup
    db.close()
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client_with_results(db_with_results: DatabaseManager) -> TestClient:
    """Create a test client with results data."""
    import backend_api.database as db_module

    # Store original value
    original_db = db_module._db_manager

    # Set our test database as the global singleton
    db_module._db_manager = db_with_results

    # Import app after setting up the database
    from backend_api.main import app

    # Mock the init/close functions to prevent lifespan from changing our db
    with patch("backend_api.main.init_database", return_value=db_with_results):
        with patch("backend_api.main.close_database"):
            with patch("backend_api.main.init_job_manager", return_value=MagicMock()):
                with patch("backend_api.main.shutdown_executor"):
                    with TestClient(app) as client:
                        yield client

    # Restore original
    db_module._db_manager = original_db


# =============================================================================
# GET /api/v1/results/{submission_id} TESTS
# =============================================================================


class TestGetResults:
    """Tests for GET /api/v1/results/{submission_id}."""

    def test_get_results_success(self, client_with_results):
        """Test successful retrieval of submission results."""
        response = client_with_results.get("/api/v1/results/1")

        assert response.status_code == 200
        data = response.json()

        assert data["submission_id"] == "1"
        assert data["dataset_id"] == "1"
        assert data["algorithm_name"] == "AlgoA"
        assert data["true_positives"] == 850
        assert data["false_positives"] == 50
        assert data["false_negatives"] == 100
        assert data["precision"] == pytest.approx(0.944, rel=1e-3)
        assert data["recall"] == pytest.approx(0.895, rel=1e-3)
        assert data["f1_score"] == pytest.approx(0.919, rel=1e-3)
        assert data["position_rms_km"] == pytest.approx(12.5, rel=1e-3)
        assert data["velocity_rms_km_s"] == pytest.approx(0.025, rel=1e-3)

    def test_get_results_with_satellite_breakdown(self, client_with_results):
        """Test that satellite results are parsed correctly."""
        response = client_with_results.get("/api/v1/results/1")

        assert response.status_code == 200
        data = response.json()

        # Check satellite results are parsed
        assert "satellite_results" in data
        assert len(data["satellite_results"]) == 2

        sat_1 = data["satellite_results"][0]
        assert sat_1["satellite_id"] == "25544"
        assert sat_1["status"] == "TP"
        assert sat_1["observations_used"] == 100

    def test_get_results_not_found(self, client_with_results):
        """Test 404 for non-existent submission."""
        response = client_with_results.get("/api/v1/results/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_results_no_results_yet(self, client_with_results):
        """Test getting results for submission still processing (no results)."""
        response = client_with_results.get("/api/v1/results/3")

        assert response.status_code == 200
        data = response.json()

        # Should return submission info with zero/null metrics
        assert data["submission_id"] == "3"
        assert data["true_positives"] == 0
        assert data["f1_score"] == 0.0

    def test_get_results_ranking(self, client_with_results):
        """Test that rank is calculated correctly."""
        # AlgoA v2.0 (submission 4) has highest F1 score (0.947)
        response = client_with_results.get("/api/v1/results/4")
        assert response.status_code == 200
        data = response.json()
        assert data["rank"] == 1

        # AlgoA v1.0 (submission 1) has second highest F1 score (0.919)
        response = client_with_results.get("/api/v1/results/1")
        assert response.status_code == 200
        data = response.json()
        assert data["rank"] == 2

    def test_get_results_with_optional_metrics(self, client_with_results):
        """Test that optional metrics are returned when present."""
        response = client_with_results.get("/api/v1/results/1")

        assert response.status_code == 200
        data = response.json()

        # Check optional metrics
        assert data["mahalanobis_distance"] == pytest.approx(1.2, rel=1e-2)
        assert data["ra_residual_rms_arcsec"] == pytest.approx(0.5, rel=1e-2)
        assert data["dec_residual_rms_arcsec"] == pytest.approx(0.6, rel=1e-2)
        assert data["processing_time_seconds"] == pytest.approx(45.5, rel=1e-2)


# =============================================================================
# GET /api/v1/results/{submission_id}/metrics TESTS
# =============================================================================


class TestGetDetailedMetrics:
    """Tests for GET /api/v1/results/{submission_id}/metrics."""

    def test_get_detailed_metrics_success(self, client_with_results):
        """Test successful retrieval of detailed metrics."""
        response = client_with_results.get("/api/v1/results/1/metrics")

        assert response.status_code == 200
        data = response.json()

        assert data["submission_id"] == "1"
        assert "per_satellite_metrics" in data
        assert "per_track_metrics" in data
        assert "temporal_breakdown" in data

    def test_get_detailed_metrics_with_data(self, client_with_results):
        """Test that detailed metrics contain expected data."""
        response = client_with_results.get("/api/v1/results/1/metrics")

        assert response.status_code == 200
        data = response.json()

        # Check per-satellite metrics
        assert len(data["per_satellite_metrics"]) == 2
        assert data["per_satellite_metrics"][0]["satellite_id"] == "25544"

        # Check per-track metrics
        assert len(data["per_track_metrics"]) == 1

        # Check temporal breakdown
        assert len(data["temporal_breakdown"]) == 1

    def test_get_detailed_metrics_not_found(self, client_with_results):
        """Test 404 for non-existent submission."""
        response = client_with_results.get("/api/v1/results/999/metrics")

        assert response.status_code == 404

    def test_get_detailed_metrics_empty_results(self, client_with_results):
        """Test metrics for submission without detailed raw results."""
        response = client_with_results.get("/api/v1/results/3/metrics")

        assert response.status_code == 200
        data = response.json()

        # Should return empty arrays
        assert data["per_satellite_metrics"] == []
        assert data["per_track_metrics"] == []


# =============================================================================
# GET /api/v1/results/{submission_id}/visualization TESTS
# =============================================================================


class TestGetVisualizationData:
    """Tests for GET /api/v1/results/{submission_id}/visualization."""

    def test_get_visualization_data_success(self, client_with_results):
        """Test successful retrieval of visualization data."""
        response = client_with_results.get("/api/v1/results/1/visualization")

        assert response.status_code == 200
        data = response.json()

        assert data["submission_id"] == "1"
        assert "orbit_plots" in data
        assert "error_distribution" in data
        assert "temporal_analysis" in data

    def test_get_visualization_data_with_content(self, client_with_results):
        """Test that visualization data contains expected content."""
        response = client_with_results.get("/api/v1/results/1/visualization")

        assert response.status_code == 200
        data = response.json()

        # Check orbit plots
        assert len(data["orbit_plots"]) == 1

        # Check error distribution
        assert len(data["error_distribution"]) == 3

        # Check temporal analysis
        assert len(data["temporal_analysis"]) == 1

    def test_get_visualization_data_not_found(self, client_with_results):
        """Test 404 for non-existent submission."""
        response = client_with_results.get("/api/v1/results/999/visualization")

        assert response.status_code == 404

    def test_get_visualization_data_empty(self, client_with_results):
        """Test visualization for submission without viz data."""
        response = client_with_results.get("/api/v1/results/3/visualization")

        assert response.status_code == 200
        data = response.json()

        assert data["orbit_plots"] == []
        assert data["error_distribution"] == []


# =============================================================================
# GET /api/v1/results/{submission_id}/export TESTS
# =============================================================================


class TestExportResults:
    """Tests for GET /api/v1/results/{submission_id}/export."""

    def test_export_results_json(self, client_with_results):
        """Test exporting results as JSON."""
        response = client_with_results.get("/api/v1/results/1/export?format=json")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert "attachment" in response.headers.get("content-disposition", "")

        data = response.json()
        assert "algorithm_name" in data

    def test_export_results_csv(self, client_with_results):
        """Test exporting results as CSV."""
        response = client_with_results.get("/api/v1/results/1/export?format=csv")

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers.get("content-disposition", "")

        # Check CSV content
        content = response.text
        assert "algorithm_name" in content

    def test_export_results_invalid_format(self, client_with_results):
        """Test error for unsupported export format."""
        response = client_with_results.get("/api/v1/results/1/export?format=xml")

        assert response.status_code == 400
        assert "unsupported format" in response.json()["detail"].lower()

    def test_export_results_not_found(self, client_with_results):
        """Test 404 for non-existent submission."""
        response = client_with_results.get("/api/v1/results/999/export")

        assert response.status_code == 404

    def test_export_results_default_format(self, client_with_results):
        """Test that default format is JSON."""
        response = client_with_results.get("/api/v1/results/1/export")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]


# =============================================================================
# GET /api/v1/results/ TESTS (LIST ENDPOINT)
# =============================================================================


@pytest.fixture
def db_empty():
    """Create an empty database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_empty.duckdb"

    db = DatabaseManager(db_path=db_path)
    db.initialize()

    yield db

    db.close()
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client_empty(db_empty: DatabaseManager) -> TestClient:
    """Create a test client with empty database."""
    import backend_api.database as db_module

    original_db = db_module._db_manager
    db_module._db_manager = db_empty

    from backend_api.main import app

    with patch("backend_api.main.init_database", return_value=db_empty):
        with patch("backend_api.main.close_database"):
            with patch("backend_api.main.init_job_manager", return_value=MagicMock()):
                with patch("backend_api.main.shutdown_executor"):
                    with TestClient(app) as client:
                        yield client

    db_module._db_manager = original_db


@pytest.fixture
def db_with_multiple_datasets():
    """Create a database with multiple datasets and results for filtering tests."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_multi.duckdb"

    db = DatabaseManager(db_path=db_path)
    db.initialize()

    # Create multiple datasets
    db.execute(
        """
        INSERT INTO datasets (id, name, code, tier, orbital_regime, status, observation_count, satellite_count, created_at)
        VALUES
            (1, 'LEO Dataset', 'LEO_T1', 'T1', 'LEO', 'available', 1000, 5, CURRENT_TIMESTAMP),
            (2, 'GEO Dataset', 'GEO_T1', 'T1', 'GEO', 'available', 500, 3, CURRENT_TIMESTAMP)
        """
    )

    # Create submissions across datasets with various statuses
    db.execute(
        """
        INSERT INTO submissions (id, dataset_id, algorithm_name, version, status, created_at, completed_at)
        VALUES
            (1, 1, 'AlphaAlgo', 'v1.0', 'completed', '2024-01-01 10:00:00', '2024-01-01 11:00:00'),
            (2, 1, 'BetaAlgo', 'v1.0', 'completed', '2024-01-02 10:00:00', '2024-01-02 11:00:00'),
            (3, 1, 'AlphaAlgo', 'v2.0', 'completed', '2024-01-03 10:00:00', '2024-01-03 11:00:00'),
            (4, 2, 'GammaAlgo', 'v1.0', 'completed', '2024-01-04 10:00:00', '2024-01-04 11:00:00'),
            (5, 1, 'DeltaAlgo', 'v1.0', 'processing', '2024-01-05 10:00:00', NULL),
            (6, 1, 'FailedAlgo', 'v1.0', 'failed', '2024-01-06 10:00:00', '2024-01-06 11:00:00')
        """
    )

    # Create results (only for completed submissions with actual results)
    db.execute(
        """
        INSERT INTO submission_results (
            submission_id, true_positives, false_positives, false_negatives,
            precision, recall, f1_score, position_rms_km, velocity_rms_km_s
        ) VALUES
            (1, 800, 100, 100, 0.889, 0.889, 0.889, 15.0, 0.030),
            (2, 850, 50, 100, 0.944, 0.895, 0.919, 12.5, 0.025),
            (3, 900, 20, 80, 0.978, 0.918, 0.947, 10.0, 0.020),
            (4, 700, 150, 150, 0.824, 0.824, 0.824, 20.0, 0.040)
        """
    )

    yield db

    db.close()
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client_with_multiple_datasets(db_with_multiple_datasets: DatabaseManager) -> TestClient:
    """Create a test client with multiple datasets."""
    import backend_api.database as db_module

    original_db = db_module._db_manager
    db_module._db_manager = db_with_multiple_datasets

    from backend_api.main import app

    with patch("backend_api.main.init_database", return_value=db_with_multiple_datasets):
        with patch("backend_api.main.close_database"):
            with patch("backend_api.main.init_job_manager", return_value=MagicMock()):
                with patch("backend_api.main.shutdown_executor"):
                    with TestClient(app) as client:
                        yield client

    db_module._db_manager = original_db


class TestListResults:
    """Tests for GET /api/v1/results/ (list endpoint)."""

    def test_list_results_empty_database(self, client_empty):
        """Test that empty database returns empty list."""
        response = client_empty.get("/api/v1/results/")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_results_returns_all(self, client_with_multiple_datasets):
        """Test that list endpoint returns all results with correct fields."""
        response = client_with_multiple_datasets.get("/api/v1/results/")

        assert response.status_code == 200
        data = response.json()

        # Should return 4 results (only submissions with results in submission_results)
        assert len(data) == 4

        # Check that all required fields are present
        for result in data:
            assert "submission_id" in result
            assert "dataset_id" in result
            assert "algorithm_name" in result
            assert "version" in result
            assert "status" in result
            assert "f1_score" in result
            assert "precision" in result
            assert "recall" in result
            assert "position_rms_km" in result
            assert "rank" in result

    def test_list_results_filter_by_dataset_id(self, client_with_multiple_datasets):
        """Test filtering by dataset_id."""
        response = client_with_multiple_datasets.get("/api/v1/results/?dataset_id=1")

        assert response.status_code == 200
        data = response.json()

        # Dataset 1 has 3 submissions with results
        assert len(data) == 3
        for result in data:
            assert result["dataset_id"] == "1"

    def test_list_results_filter_by_status(self, client_with_multiple_datasets):
        """Test filtering by status."""
        response = client_with_multiple_datasets.get("/api/v1/results/?status=completed")

        assert response.status_code == 200
        data = response.json()

        # All returned results should be completed
        for result in data:
            assert result["status"] == "completed"

    def test_list_results_filter_by_algorithm_name(self, client_with_multiple_datasets):
        """Test filtering by algorithm_name (case-insensitive)."""
        # Test with lowercase
        response = client_with_multiple_datasets.get("/api/v1/results/?algorithm_name=alpha")

        assert response.status_code == 200
        data = response.json()

        # Should find AlphaAlgo v1.0 and v2.0
        assert len(data) == 2
        for result in data:
            assert "alpha" in result["algorithm_name"].lower()

    def test_list_results_pagination_limit(self, client_with_multiple_datasets):
        """Test pagination with limit."""
        response = client_with_multiple_datasets.get("/api/v1/results/?limit=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2

    def test_list_results_pagination_offset(self, client_with_multiple_datasets):
        """Test pagination with offset."""
        # Get all results first
        all_response = client_with_multiple_datasets.get("/api/v1/results/")
        all_data = all_response.json()

        # Get with offset
        response = client_with_multiple_datasets.get("/api/v1/results/?offset=2")
        data = response.json()

        # Should skip first 2
        assert len(data) == len(all_data) - 2

    def test_list_results_combined_filters(self, client_with_multiple_datasets):
        """Test combining multiple filters."""
        response = client_with_multiple_datasets.get(
            "/api/v1/results/?dataset_id=1&algorithm_name=alpha&limit=10"
        )

        assert response.status_code == 200
        data = response.json()

        # Should find AlphaAlgo submissions in dataset 1
        assert len(data) == 2
        for result in data:
            assert result["dataset_id"] == "1"
            assert "alpha" in result["algorithm_name"].lower()

    def test_list_results_includes_rank(self, client_with_multiple_datasets):
        """Test that results include rank within dataset."""
        response = client_with_multiple_datasets.get("/api/v1/results/?dataset_id=1")

        assert response.status_code == 200
        data = response.json()

        # Check ranks are assigned
        ranks = [r["rank"] for r in data]
        assert all(r is not None for r in ranks)

        # Find the highest F1 score entry - should have rank 1
        highest_f1 = max(data, key=lambda x: x["f1_score"])
        assert highest_f1["rank"] == 1

    def test_list_results_excludes_submissions_without_results(self, client_with_multiple_datasets):
        """Test that submissions without results are not returned."""
        response = client_with_multiple_datasets.get("/api/v1/results/")

        assert response.status_code == 200
        data = response.json()

        # Submission 5 (processing) and 6 (failed) should not appear
        submission_ids = [r["submission_id"] for r in data]
        assert "5" not in submission_ids
        assert "6" not in submission_ids

    def test_list_results_includes_dataset_name(self, client_with_multiple_datasets):
        """Test that results include dataset_name from join."""
        response = client_with_multiple_datasets.get("/api/v1/results/")

        assert response.status_code == 200
        data = response.json()

        # Check dataset names are present
        for result in data:
            assert result["dataset_name"] is not None
            assert result["dataset_name"] in ["LEO Dataset", "GEO Dataset"]


class TestListResultsEdgeCases:
    """Edge case tests for GET /api/v1/results/."""

    def test_list_results_nonexistent_dataset_id(self, client_with_multiple_datasets):
        """Test filtering by non-existent dataset_id returns empty list."""
        response = client_with_multiple_datasets.get("/api/v1/results/?dataset_id=999")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_results_invalid_status(self, client_with_multiple_datasets):
        """Test filtering by invalid status returns empty list."""
        response = client_with_multiple_datasets.get("/api/v1/results/?status=invalid_status")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_results_special_characters_in_algorithm_name(self, client_with_multiple_datasets):
        """Test filtering with special characters in algorithm_name."""
        # This shouldn't match anything but also shouldn't error
        response = client_with_multiple_datasets.get("/api/v1/results/?algorithm_name=%25%27")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_results_offset_beyond_data(self, client_with_multiple_datasets):
        """Test offset beyond available data returns empty list."""
        response = client_with_multiple_datasets.get("/api/v1/results/?offset=1000")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_results_zero_limit(self, client_with_multiple_datasets):
        """Test limit=0 returns empty list."""
        response = client_with_multiple_datasets.get("/api/v1/results/?limit=0")

        assert response.status_code == 200
        data = response.json()
        assert data == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
