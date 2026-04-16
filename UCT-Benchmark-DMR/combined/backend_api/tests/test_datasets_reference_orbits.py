"""Tests for GET /api/v1/datasets/{id}/reference-orbits.

Verifies owner-or-admin gating (Apr 9 answer-key separation), 404 on missing
datasets, and envelope shape on success. Propagation itself is mocked so tests
don't depend on Orekit / JVM startup.

Run with: uv run pytest backend_api/tests/test_datasets_reference_orbits.py -v
"""

from __future__ import annotations

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend_api.auth import CurrentUser, get_current_user as prod_get_current_user
from backend_api.database import get_db
from backend_api.main import create_test_app, reset_test_mode
from backend_api.middleware.auth import get_current_user as mw_get_current_user
from backend_api.services.orbit_propagation import SatelliteTrack
from uct_benchmark.database.connection import DatabaseManager

OWNER_USER_ID = "owner-user-id"
OTHER_USER_ID = "other-user-id"
ADMIN_USER_ID = "admin-user-id"


def _make_user(user_id: str, role: str = "user") -> CurrentUser:
    return CurrentUser(id=user_id, email=f"{user_id}@example.com", role=role)


def _seed_dataset(db, dataset_id: int, owner_id: str) -> None:
    db.execute(
        """
        INSERT INTO datasets
            (id, name, code, tier, orbital_regime, status, observation_count, satellite_count, user_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (dataset_id, f"Test Dataset {dataset_id}", f"CODE{dataset_id}", "T1", "LEO", "available", 10, 2, owner_id),
    )


def _fake_tracks() -> list[SatelliteTrack]:
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    t1 = datetime(2026, 1, 1, 1, tzinfo=timezone.utc).isoformat()
    return [
        SatelliteTrack(
            id="90001",
            name="SAT-90001",
            regime="LEO",
            positions=[
                {"time": t0, "x": 7000.0, "y": 0.0, "z": 0.0},
                {"time": t1, "x": 0.0, "y": 7000.0, "z": 0.0},
            ],
        )
    ]


@pytest.fixture
def db() -> Generator[DatabaseManager, None, None]:
    # Temp file instead of :memory: — DuckDB in-memory DBs are per-thread,
    # which breaks TestClient (requests run in a separate thread). Pattern
    # matches backend_api/tests/test_results.py:32.
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_ref_orbits.duckdb"
    db_inst = DatabaseManager(backend="duckdb", db_path=db_path)
    db_inst.initialize(force=True)
    yield db_inst
    db_inst.close()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client_as(db: DatabaseManager):
    """Yield a builder that returns a TestClient authenticated as a given user.

    Uses `create_test_app()` so lifespan startup (which would otherwise try to
    connect to Supabase with missing psycopg2) is skipped. The TestClient is
    instantiated without `with` — no lifespan trigger — and the endpoint's
    `db` dependency is overridden to point at the in-memory DuckDB fixture.
    """
    app = create_test_app()
    app.dependency_overrides[get_db] = lambda: db

    def _build(user: CurrentUser) -> TestClient:
        app.dependency_overrides[prod_get_current_user] = lambda: user
        app.dependency_overrides[mw_get_current_user] = lambda: user
        return TestClient(app, raise_server_exceptions=True)

    yield _build

    app.dependency_overrides.pop(prod_get_current_user, None)
    app.dependency_overrides.pop(mw_get_current_user, None)
    app.dependency_overrides.pop(get_db, None)
    reset_test_mode()


class TestReferenceOrbitsEndpoint:
    def test_owner_200(self, db, client_as):
        _seed_dataset(db, dataset_id=1, owner_id=OWNER_USER_ID)
        client = client_as(_make_user(OWNER_USER_ID))

        with patch(
            "backend_api.services.orbit_propagation.propagate_reference_orbits",
            return_value=_fake_tracks(),
        ):
            response = client.get("/api/v1/datasets/1/reference-orbits")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["dataset_id"] == "1"
        assert len(body["satellites"]) == 1
        sat = body["satellites"][0]
        assert sat["id"] == "90001"
        assert sat["regime"] == "LEO"
        assert len(sat["positions"]) == 2

    def test_non_owner_403(self, db, client_as):
        _seed_dataset(db, dataset_id=2, owner_id=OWNER_USER_ID)
        client = client_as(_make_user(OTHER_USER_ID))

        response = client.get("/api/v1/datasets/2/reference-orbits")

        assert response.status_code == 403, response.text
        assert "answer key" in response.json()["detail"].lower()

    def test_admin_200_even_if_not_owner(self, db, client_as):
        _seed_dataset(db, dataset_id=3, owner_id=OWNER_USER_ID)
        client = client_as(_make_user(ADMIN_USER_ID, role="admin"))

        with patch(
            "backend_api.services.orbit_propagation.propagate_reference_orbits",
            return_value=_fake_tracks(),
        ):
            response = client.get("/api/v1/datasets/3/reference-orbits")

        assert response.status_code == 200, response.text

    def test_missing_dataset_404(self, db, client_as):
        client = client_as(_make_user(OWNER_USER_ID))
        response = client.get("/api/v1/datasets/99999/reference-orbits")
        assert response.status_code == 404, response.text

    def test_max_samples_validation(self, db, client_as):
        _seed_dataset(db, dataset_id=4, owner_id=OWNER_USER_ID)
        client = client_as(_make_user(OWNER_USER_ID))

        response = client.get("/api/v1/datasets/4/reference-orbits?max_samples=0")
        assert response.status_code == 400, response.text

        response = client.get("/api/v1/datasets/4/reference-orbits?max_samples=50000")
        assert response.status_code == 400, response.text

    def test_empty_references_returns_empty_list(self, db, client_as):
        """Owner is authorized; if no state vectors exist yet (e.g., still generating)
        the endpoint returns empty satellites rather than error."""
        _seed_dataset(db, dataset_id=5, owner_id=OWNER_USER_ID)
        client = client_as(_make_user(OWNER_USER_ID))

        with patch(
            "backend_api.services.orbit_propagation.propagate_reference_orbits",
            return_value=[],
        ):
            response = client.get("/api/v1/datasets/5/reference-orbits")

        assert response.status_code == 200, response.text
        assert response.json()["satellites"] == []
