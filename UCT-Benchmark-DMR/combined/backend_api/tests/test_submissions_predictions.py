"""Tests for GET /api/v1/submissions/{id}/predictions.

Verifies RLS (user sees only own submissions), 404 for missing submissions,
410 for submissions whose file was removed, and the include=reference
overlay. Propagation is mocked.

Run with: uv run pytest backend_api/tests/test_submissions_predictions.py -v
"""

from __future__ import annotations

import json
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


def _make_user(user_id: str, role: str = "user") -> CurrentUser:
    return CurrentUser(id=user_id, email=f"{user_id}@example.com", role=role)


def _seed(db: DatabaseManager, workdir: Path) -> dict[str, Path]:
    db.execute(
        """
        INSERT INTO datasets
            (id, name, code, tier, orbital_regime, status, observation_count, satellite_count, user_id, created_at)
        VALUES (10, 'DS-10', 'C10', 'T1', 'LEO', 'available', 10, 2, ?, CURRENT_TIMESTAMP)
        """,
        (OWNER_USER_ID,),
    )

    uctp_path = workdir / "uctp.json"
    uctp_path.write_text(
        json.dumps(
            [
                {
                    "idStateVector": "SAT-1",
                    "epoch": "2026-01-01T00:00:00",
                    "xpos": 7000.0, "ypos": 0.0, "zpos": 0.0,
                    "xvel": 0.0, "yvel": 7.5, "zvel": 0.0,
                    "sourcedData": ["obs-1"],
                    "referenceFrame": "J2000",
                }
            ]
        )
    )

    db.execute(
        """
        INSERT INTO submissions
            (id, dataset_id, algorithm_name, version, status, user_id, file_path, created_at)
        VALUES (100, 10, 'Algo', '1.0', 'completed', ?, ?, CURRENT_TIMESTAMP)
        """,
        (OWNER_USER_ID, str(uctp_path)),
    )

    db.execute(
        """
        INSERT INTO submissions
            (id, dataset_id, algorithm_name, version, status, user_id, file_path, created_at)
        VALUES (101, 10, 'Algo', '1.0', 'queued', ?, NULL, CURRENT_TIMESTAMP)
        """,
        (OWNER_USER_ID,),
    )

    missing_path = workdir / "missing.json"
    db.execute(
        """
        INSERT INTO submissions
            (id, dataset_id, algorithm_name, version, status, user_id, file_path, created_at)
        VALUES (102, 10, 'Algo', '1.0', 'completed', ?, ?, CURRENT_TIMESTAMP)
        """,
        (OWNER_USER_ID, str(missing_path)),
    )

    return {"uctp": uctp_path, "missing": missing_path}


def _fake_tracks() -> list[SatelliteTrack]:
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    return [
        SatelliteTrack(
            id="SAT-1",
            name="SAT-SAT-1",
            regime="LEO",
            positions=[{"time": t0, "x": 7000.0, "y": 0.0, "z": 0.0}],
        )
    ]


@pytest.fixture
def workdir() -> Generator[Path, None, None]:
    tmp = Path(tempfile.mkdtemp())
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def db(workdir: Path) -> Generator[DatabaseManager, None, None]:
    db_path = workdir / "test.duckdb"
    db_inst = DatabaseManager(backend="duckdb", db_path=db_path)
    db_inst.initialize(force=True)
    _seed(db_inst, workdir)
    yield db_inst
    db_inst.close()


@pytest.fixture
def client_as(db: DatabaseManager):
    app = create_test_app()
    app.dependency_overrides[get_db] = lambda: db

    def _build(user: CurrentUser) -> TestClient:
        app.dependency_overrides[prod_get_current_user] = lambda: user
        app.dependency_overrides[mw_get_current_user] = lambda: user
        return TestClient(app)

    yield _build
    app.dependency_overrides.pop(prod_get_current_user, None)
    app.dependency_overrides.pop(mw_get_current_user, None)
    app.dependency_overrides.pop(get_db, None)
    reset_test_mode()


class TestSubmissionPredictionsEndpoint:
    def test_owner_200(self, client_as):
        client = client_as(_make_user(OWNER_USER_ID))
        with patch(
            "backend_api.services.orbit_propagation.propagate_predictions",
            return_value=_fake_tracks(),
        ):
            response = client.get("/api/v1/submissions/100/predictions")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["submission_id"] == "100"
        assert len(body["predicted"]) == 1
        assert body["predicted"][0]["id"] == "SAT-1"
        assert body["reference"] is None

    def test_non_owner_404(self, client_as):
        """Non-owners get 404 (not 403) to avoid leaking submission existence."""
        client = client_as(_make_user(OTHER_USER_ID))
        response = client.get("/api/v1/submissions/100/predictions")
        assert response.status_code == 404, response.text

    def test_no_uctp_file_404(self, client_as):
        client = client_as(_make_user(OWNER_USER_ID))
        response = client.get("/api/v1/submissions/101/predictions")
        assert response.status_code == 404, response.text
        assert "no uctp" in response.json()["detail"].lower()

    def test_missing_file_on_disk_410(self, client_as):
        client = client_as(_make_user(OWNER_USER_ID))
        response = client.get("/api/v1/submissions/102/predictions")
        assert response.status_code == 410, response.text

    def test_include_reference(self, client_as):
        client = client_as(_make_user(OWNER_USER_ID))
        with patch(
            "backend_api.services.orbit_propagation.propagate_predictions",
            return_value=_fake_tracks(),
        ), patch(
            "backend_api.services.orbit_propagation.propagate_reference_orbits",
            return_value=_fake_tracks(),
        ):
            response = client.get(
                "/api/v1/submissions/100/predictions?include=reference"
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["reference"] is not None
        assert len(body["reference"]) == 1

    def test_max_samples_validation(self, client_as):
        client = client_as(_make_user(OWNER_USER_ID))
        response = client.get("/api/v1/submissions/100/predictions?max_samples=0")
        assert response.status_code == 400, response.text
