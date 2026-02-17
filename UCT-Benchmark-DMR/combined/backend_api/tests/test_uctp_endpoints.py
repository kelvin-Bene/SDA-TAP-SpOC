"""
Tests for UCTP Lab API endpoints.

Covers: dashboard stats, runs CRUD, compare, models, connectivity, algorithms.

Run with: uv run pytest backend_api/tests/test_uctp_endpoints.py -v
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from uct_benchmark.database.connection import DatabaseManager


@pytest.fixture(scope="module")
def _module_db():
    """Single database instance for the entire module."""
    db = DatabaseManager(in_memory=True, backend="duckdb")
    db.initialize(force=True)
    yield db
    db.close()


@pytest.fixture()
def client(_module_db):
    """Create a test client with mocked database dependency."""
    import backend_api.database as db_module
    import backend_api.jobs.workers as workers_module
    import backend_api.main as main_module
    from backend_api.database import get_db
    from backend_api.main import app

    orig_init = db_module.init_database
    orig_close = db_module.close_database
    orig_mgr = db_module._db_manager
    orig_shutdown = workers_module.shutdown_executor
    orig_main_init = main_module.init_database
    orig_main_close = main_module.close_database
    orig_main_shutdown = main_module.shutdown_executor

    noop_init = lambda **kw: _module_db
    noop_close = lambda: None
    noop_shutdown = lambda: None

    db_module.init_database = noop_init
    db_module.close_database = noop_close
    db_module._db_manager = _module_db
    main_module.init_database = noop_init
    main_module.close_database = noop_close
    main_module.shutdown_executor = noop_shutdown
    workers_module.shutdown_executor = noop_shutdown
    app.dependency_overrides[get_db] = lambda: _module_db

    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        db_module.init_database = orig_init
        db_module.close_database = orig_close
        db_module._db_manager = orig_mgr
        workers_module.shutdown_executor = orig_shutdown
        main_module.init_database = orig_main_init
        main_module.close_database = orig_main_close
        main_module.shutdown_executor = orig_main_shutdown


@pytest.fixture()
def populated_client(_module_db):
    """Test client with sample datasets pre-inserted."""
    import backend_api.database as db_module
    import backend_api.jobs.workers as workers_module
    import backend_api.main as main_module
    from backend_api.database import get_db
    from backend_api.main import app

    # Insert sample data (idempotent via INSERT OR IGNORE)
    try:
        _module_db.execute(
            """
            INSERT INTO datasets (id, name, code, tier, orbital_regime, status, observation_count, satellite_count, created_at)
            VALUES
                (1, 'LEO Test', 'LEO_T1', 'T1', 'LEO', 'available', 1000, 5, CURRENT_TIMESTAMP),
                (2, 'GEO Test', 'GEO_T2', 'T2', 'GEO', 'available', 500, 3, CURRENT_TIMESTAMP)
            """
        )
    except Exception:
        pass  # Already exists from a prior test

    orig_init = db_module.init_database
    orig_close = db_module.close_database
    orig_mgr = db_module._db_manager
    orig_shutdown = workers_module.shutdown_executor
    orig_main_init = main_module.init_database
    orig_main_close = main_module.close_database
    orig_main_shutdown = main_module.shutdown_executor

    noop_init = lambda **kw: _module_db
    noop_close = lambda: None
    noop_shutdown = lambda: None

    db_module.init_database = noop_init
    db_module.close_database = noop_close
    db_module._db_manager = _module_db
    main_module.init_database = noop_init
    main_module.close_database = noop_close
    main_module.shutdown_executor = noop_shutdown
    workers_module.shutdown_executor = noop_shutdown
    app.dependency_overrides[get_db] = lambda: _module_db

    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        db_module.init_database = orig_init
        db_module.close_database = orig_close
        db_module._db_manager = orig_mgr
        workers_module.shutdown_executor = orig_shutdown
        main_module.init_database = orig_main_init
        main_module.close_database = orig_main_close
        main_module.shutdown_executor = orig_main_shutdown


class TestDashboardStats:
    """Tests for GET /api/v1/uctp/dashboard/stats."""

    def test_dashboard_stats_empty(self, client: TestClient):
        """Dashboard stats with empty DB returns zeros."""
        response = client.get("/api/v1/uctp/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_runs" in data
        assert "completed_runs" in data
        assert "total_models" in data
        assert "api_health_pct" in data
        assert "recent_runs" in data


class TestRunsCRUD:
    """Tests for UCTP run endpoints."""

    def test_list_runs_empty(self, client: TestClient):
        """List runs returns empty list when no runs exist."""
        response = client.get("/api/v1/uctp/runs/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_runs_with_filter(self, client: TestClient):
        """List runs accepts filter parameters."""
        response = client.get("/api/v1/uctp/runs/?status=completed&limit=10&offset=0")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_run_not_found(self, client: TestClient):
        """Get non-existent run returns 404."""
        response = client.get("/api/v1/uctp/runs/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_run_dataset_not_found(self, client: TestClient):
        """Create run with non-existent dataset returns 404."""
        response = client.post(
            "/api/v1/uctp/runs/",
            json={
                "dataset_id": 99999,
                "algorithm_name": "TestAlgo",
                "clustering": {"method": "angular_dbscan", "eps_deg": 0.5, "min_samples": 5},
                "iod": {"method": "gauss", "max_iterations": 100},
                "refinement": {"method": "batch_least_squares", "max_iterations": 50},
            },
        )
        assert response.status_code in (404, 422)

    @patch("backend_api.jobs.uctp_workers.submit_uctp_run")
    def test_create_run_success(self, mock_submit, populated_client: TestClient):
        """Create run with valid data succeeds."""
        mock_job = MagicMock()
        mock_job.id = "test-job-uctp-1"
        mock_submit.return_value = mock_job

        response = populated_client.post(
            "/api/v1/uctp/runs/",
            json={
                "dataset_id": 1,
                "algorithm_name": "TestAlgo",
                "clustering": {"method": "angular_dbscan", "eps_deg": 0.5, "min_samples": 5},
                "iod": {"method": "gauss", "max_iterations": 100},
                "refinement": {"method": "batch_least_squares", "max_iterations": 50},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["dataset_id"] == 1
        assert data["algorithm_name"] == "TestAlgo"
        assert data["status"] == "pending"

    def test_delete_run_not_found(self, client: TestClient):
        """Delete non-existent run returns 404."""
        response = client.delete("/api/v1/uctp/runs/99999")
        assert response.status_code == 404

    def test_get_run_logs_not_found(self, client: TestClient):
        """Get logs for non-existent run returns 404."""
        response = client.get("/api/v1/uctp/runs/99999/logs")
        assert response.status_code == 404


class TestRunComparison:
    """Tests for GET /api/v1/uctp/runs/compare/."""

    def test_compare_needs_at_least_2_ids(self, client: TestClient):
        """Compare with <2 IDs returns 400."""
        response = client.get("/api/v1/uctp/runs/compare/?run_ids=1")
        assert response.status_code == 400
        assert "at least 2" in response.json()["detail"].lower()

    def test_compare_max_10_ids(self, client: TestClient):
        """Compare with >10 IDs returns 400."""
        ids = ",".join(str(i) for i in range(1, 12))
        response = client.get(f"/api/v1/uctp/runs/compare/?run_ids={ids}")
        assert response.status_code == 400
        assert "maximum 10" in response.json()["detail"].lower()

    def test_compare_runs_not_found(self, client: TestClient):
        """Compare with non-existent runs returns 404."""
        response = client.get("/api/v1/uctp/runs/compare/?run_ids=999,998")
        assert response.status_code == 404


class TestModels:
    """Tests for UCTP model endpoints."""

    def test_list_models_empty(self, client: TestClient):
        """List models returns empty list."""
        response = client.get("/api/v1/uctp/models/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_models_with_status_filter(self, client: TestClient):
        """List models accepts status filter."""
        response = client.get("/api/v1/uctp/models/?status=ready")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_model_not_found(self, client: TestClient):
        """Get non-existent model returns 404."""
        response = client.get("/api/v1/uctp/models/99999")
        assert response.status_code == 404

    def test_delete_model_not_found(self, client: TestClient):
        """Delete non-existent model returns 404."""
        response = client.delete("/api/v1/uctp/models/99999")
        assert response.status_code == 404

    @patch("backend_api.jobs.uctp_workers.submit_model_training")
    def test_train_model(self, mock_train, client: TestClient):
        """Train model endpoint creates a new model record."""
        response = client.post(
            "/api/v1/uctp/models/train",
            json={
                "name": "NewModel",
                "model_type": "clustering_nn",
                "description": "Test model",
                "training_dataset_ids": [1, 2],
                "training_config": {"epochs": 10, "learning_rate": 0.01},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "NewModel"
        assert data["status"] == "training"
        assert data["version"] == "v1"

    def test_evaluate_model_not_found(self, client: TestClient):
        """Evaluate non-existent model returns 404."""
        response = client.post("/api/v1/uctp/models/99999/evaluate?dataset_id=1")
        assert response.status_code == 404


class TestConnectivity:
    """Tests for UCTP connectivity endpoints."""

    def test_list_connectivity(self, client: TestClient):
        """List connectivity statuses."""
        response = client.get("/api/v1/uctp/connectivity/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("backend_api.jobs.uctp_workers.run_connectivity_test")
    def test_test_single_connection(self, mock_test, client: TestClient):
        """Test single connection endpoint."""
        mock_test.return_value = MagicMock(
            service_name="space-track",
            status="connected",
            response_time_ms=150.0,
            last_checked="2025-01-01T00:00:00",
            error_message=None,
            metadata={},
        )
        response = client.post(
            "/api/v1/uctp/connectivity/test",
            json={"service_name": "space-track"},
        )
        assert response.status_code == 200

    @patch("backend_api.jobs.uctp_workers.run_all_connectivity_tests")
    def test_test_all_connections(self, mock_test_all, client: TestClient):
        """Test all connections endpoint."""
        mock_test_all.return_value = MagicMock(
            total=3,
            connected=2,
            failed=1,
            results=[],
        )
        response = client.post("/api/v1/uctp/connectivity/test-all")
        assert response.status_code == 200


class TestAlgorithms:
    """Tests for UCTP algorithm endpoints."""

    def test_get_algorithm_options(self, client: TestClient):
        """Get algorithm options returns configuration."""
        response = client.get("/api/v1/uctp/algorithms/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_get_algorithm_options_alias(self, client: TestClient):
        """Algorithm options alias endpoint works."""
        response = client.get("/api/v1/uctp/algorithms/options")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
