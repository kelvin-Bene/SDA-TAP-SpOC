"""
Shared test fixtures for backend API tests.

Supports both DuckDB (default) and PostgreSQL backends.
Set TEST_DATABASE_BACKEND=postgres and TEST_DATABASE_URL=postgresql://...
to run tests against PostgreSQL.
"""

import json
import os
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from uct_benchmark.database.connection import DatabaseManager

# Global test database instance
_test_db: DatabaseManager = None


def _get_test_db() -> DatabaseManager:
    """Get or create the test database instance."""
    global _test_db
    if _test_db is None:
        _test_db = DatabaseManager(in_memory=True)
        _test_db.initialize()
    return _test_db


def _close_test_db() -> None:
    """Close the test database."""
    global _test_db
    if _test_db is not None:
        _test_db.close()
        _test_db = None


def get_test_backend() -> str:
    """Get the test database backend from environment."""
    return os.getenv("TEST_DATABASE_BACKEND", os.getenv("DATABASE_BACKEND", "duckdb")).lower()


def create_test_db() -> DatabaseManager:
    """
    Create a test database based on environment configuration.

    For DuckDB (default): Creates an in-memory database
    For PostgreSQL: Connects to TEST_DATABASE_URL

    Returns:
        Configured DatabaseManager instance
    """
    backend = get_test_backend()

    if backend in ("postgres", "postgresql", "supabase"):
        test_url = os.getenv("TEST_DATABASE_URL")
        if not test_url:
            pytest.skip(
                "PostgreSQL testing requires TEST_DATABASE_URL environment variable"
            )
        db = DatabaseManager(
            backend="postgres",
            database_url=test_url,
            pool_min=1,
            pool_max=5,
        )
    else:
        # DuckDB in-memory (default)
        db = DatabaseManager(in_memory=True)

    return db


@pytest.fixture
def db() -> Generator[DatabaseManager, None, None]:
    """Create a test database for testing."""
    db = create_test_db()
    db.initialize(force=True)  # Force clean schema for tests
    yield db
    db.close()


@pytest.fixture
def populated_db(db: DatabaseManager) -> DatabaseManager:
    """Create a database with sample datasets and submissions."""
    # Create sample datasets
    db.execute(
        """
        INSERT INTO datasets (id, name, code, tier, orbital_regime, status, observation_count, satellite_count, created_at)
        VALUES
            (1, 'LEO Test Dataset', 'LEO_T1', 'T1', 'LEO', 'available', 1000, 5, CURRENT_TIMESTAMP),
            (2, 'GEO Test Dataset', 'GEO_T2', 'T2', 'GEO', 'available', 500, 3, CURRENT_TIMESTAMP),
            (3, 'Generating Dataset', 'LEO_T1_GEN', 'T1', 'LEO', 'generating', 0, 0, CURRENT_TIMESTAMP)
        """
    )

    # Create sample submissions
    db.execute(
        """
        INSERT INTO submissions (id, dataset_id, algorithm_name, version, status, created_at)
        VALUES
            (1, 1, 'TestAlgo', 'v1.0', 'completed', CURRENT_TIMESTAMP),
            (2, 1, 'TestAlgo', 'v2.0', 'processing', CURRENT_TIMESTAMP),
            (3, 2, 'OtherAlgo', 'v1.0', 'queued', CURRENT_TIMESTAMP)
        """
    )

    # Create sample results for completed submission
    db.execute(
        """
        INSERT INTO submission_results (
            submission_id, true_positives, false_positives, false_negatives,
            precision, recall, f1_score, position_rms_km, velocity_rms_km_s
        ) VALUES (1, 850, 50, 100, 0.944, 0.895, 0.919, 12.5, 0.025)
        """
    )

    # Create sample satellites
    db.execute(
        """
        INSERT INTO satellites (sat_no, name, orbital_regime)
        VALUES
            (25544, 'ISS', 'LEO'),
            (43013, 'STARLINK-1', 'LEO')
        """
    )

    # Create sample observations for dataset 1
    for i in range(20):
        obs_id = f"obs-{i+1}"
        sat_no = 25544 if i % 2 == 0 else 43013
        db.execute(
            """
            INSERT INTO observations (id, sat_no, ob_time, ra, declination)
            VALUES (?, ?, CURRENT_TIMESTAMP, 100.0, 45.0)
            """,
            (obs_id, sat_no),
        )
        # Link observation to dataset 1
        db.execute(
            """
            INSERT INTO dataset_observations (dataset_id, observation_id)
            VALUES (1, ?)
            """,
            (obs_id,),
        )

    # Update observation_count to match actual count
    db.execute(
        """
        UPDATE datasets SET observation_count = 20 WHERE id = 1
        """
    )

    return db


@pytest.fixture
def test_client(db: DatabaseManager) -> Generator[TestClient, None, None]:
    """Create a test client with mocked database dependency."""
    import backend_api.database as db_module
    import backend_api.jobs.workers as workers_module
    from backend_api.database import get_db
    from backend_api.main import app

    def override_get_db():
        return db

    # Patch the database module functions to use in-memory test db
    original_init = db_module.init_database
    original_close = db_module.close_database
    original_db_manager = db_module._db_manager
    original_shutdown = workers_module.shutdown_executor

    def mock_init_database(db_path=None):
        db_module._db_manager = db
        return db

    def mock_close_database():
        db_module._db_manager = None

    def mock_shutdown_executor():
        pass  # No-op for tests

    db_module.init_database = mock_init_database
    db_module.close_database = mock_close_database
    db_module._db_manager = db
    workers_module.shutdown_executor = mock_shutdown_executor

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        db_module.init_database = original_init
        db_module.close_database = original_close
        db_module._db_manager = original_db_manager
        workers_module.shutdown_executor = original_shutdown


@pytest.fixture
def populated_test_client(populated_db: DatabaseManager) -> Generator[TestClient, None, None]:
    """Create a test client with mocked database containing sample data."""
    import backend_api.database as db_module
    import backend_api.jobs.workers as workers_module
    from backend_api.database import get_db
    from backend_api.main import app

    def override_get_db():
        return populated_db

    # Patch the database module functions to use in-memory test db
    original_init = db_module.init_database
    original_close = db_module.close_database
    original_db_manager = db_module._db_manager
    original_shutdown = workers_module.shutdown_executor

    def mock_init_database(db_path=None):
        db_module._db_manager = populated_db
        return populated_db

    def mock_close_database():
        db_module._db_manager = None

    def mock_shutdown_executor():
        pass  # No-op for tests

    db_module.init_database = mock_init_database
    db_module.close_database = mock_close_database
    db_module._db_manager = populated_db
    workers_module.shutdown_executor = mock_shutdown_executor

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        db_module.init_database = original_init
        db_module.close_database = original_close
        db_module._db_manager = original_db_manager
        workers_module.shutdown_executor = original_shutdown


@pytest.fixture
def sample_dataset_create() -> dict:
    """Sample dataset creation payload."""
    return {
        "name": "Test Dataset",
        "regime": "LEO",
        "tier": "T1",
        "object_count": 5,
        "timeframe": 7,
        "timeunit": "days",
        "sensors": ["optical"],
        "coverage": "standard",  # high, standard, low, mixed
        "include_hamr": False,
    }


@pytest.fixture
def sample_submission_file(tmp_path: Path) -> Path:
    """Create a sample submission file for testing."""
    file_path = tmp_path / "submission.json"
    submission_data = {
        "algorithm": "TestAlgo",
        "version": "1.0",
        "predictions": [
            {"observation_id": "obs-1", "track_id": 1, "confidence": 0.95},
            {"observation_id": "obs-2", "track_id": 1, "confidence": 0.90},
            {"observation_id": "obs-3", "track_id": 2, "confidence": 0.85},
        ],
    }
    file_path.write_text(json.dumps(submission_data))
    return file_path


# PostgreSQL-specific fixtures
@pytest.fixture
def postgres_db() -> Generator[DatabaseManager, None, None]:
    """Create a PostgreSQL database for testing (requires TEST_DATABASE_URL)."""
    test_url = os.getenv("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("PostgreSQL testing requires TEST_DATABASE_URL")

    db = DatabaseManager(
        backend="postgres",
        database_url=test_url,
        pool_min=1,
        pool_max=5,
    )
    db.initialize(force=True)
    yield db
    db.close()
