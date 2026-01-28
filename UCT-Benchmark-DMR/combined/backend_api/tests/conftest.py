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

import pytest
from fastapi.testclient import TestClient

from uct_benchmark.database.connection import DatabaseManager


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

    return db


@pytest.fixture
def test_client(db: DatabaseManager) -> Generator[TestClient, None, None]:
    """Create a test client with mocked database dependency."""
    from backend_api.database import get_db
    from backend_api.main import app

    def override_get_db():
        return db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def populated_test_client(populated_db: DatabaseManager) -> Generator[TestClient, None, None]:
    """Create a test client with mocked database containing sample data."""
    from backend_api.database import get_db
    from backend_api.main import app

    def override_get_db():
        return populated_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


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
        "coverage": 0.8,
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
