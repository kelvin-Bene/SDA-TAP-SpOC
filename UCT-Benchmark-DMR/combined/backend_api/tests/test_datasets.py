"""
Unit tests for the datasets router.

Run with: uv run pytest backend_api/tests/test_datasets.py -v
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestListDatasets:
    """Tests for GET /api/v1/datasets endpoint."""

    def test_list_datasets_empty(self, test_client: TestClient):
        """Test listing datasets when database is empty."""
        response = test_client.get("/api/v1/datasets/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_datasets_with_data(self, populated_test_client: TestClient):
        """Test listing datasets with existing data."""
        response = populated_test_client.get("/api/v1/datasets/")
        assert response.status_code == 200

        datasets = response.json()
        assert len(datasets) == 3

        # Check dataset structure
        dataset = datasets[0]
        assert "id" in dataset
        assert "name" in dataset
        assert "regime" in dataset
        assert "tier" in dataset
        assert "status" in dataset

    def test_list_datasets_filter_by_regime(self, populated_test_client: TestClient):
        """Test filtering datasets by orbital regime."""
        response = populated_test_client.get("/api/v1/datasets/?regime=LEO")
        assert response.status_code == 200

        datasets = response.json()
        assert len(datasets) == 2
        assert all(d["regime"] == "LEO" for d in datasets)

    def test_list_datasets_filter_by_tier(self, populated_test_client: TestClient):
        """Test filtering datasets by complexity tier."""
        response = populated_test_client.get("/api/v1/datasets/?tier=T1")
        assert response.status_code == 200

        datasets = response.json()
        assert len(datasets) == 2
        assert all(d["tier"] == "T1" for d in datasets)

    def test_list_datasets_filter_by_status(self, populated_test_client: TestClient):
        """Test filtering datasets by status."""
        response = populated_test_client.get("/api/v1/datasets/?status=available")
        assert response.status_code == 200

        datasets = response.json()
        assert len(datasets) == 2
        assert all(d["status"] == "available" for d in datasets)

    def test_list_datasets_pagination(self, populated_test_client: TestClient):
        """Test dataset pagination."""
        # First page
        response = populated_test_client.get("/api/v1/datasets/?limit=2&offset=0")
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Second page
        response = populated_test_client.get("/api/v1/datasets/?limit=2&offset=2")
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestGetDataset:
    """Tests for GET /api/v1/datasets/{id} endpoint."""

    def test_get_dataset_not_found(self, test_client: TestClient):
        """Test getting a non-existent dataset returns 404."""
        response = test_client.get("/api/v1/datasets/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_dataset_success(self, populated_test_client: TestClient):
        """Test getting an existing dataset."""
        response = populated_test_client.get("/api/v1/datasets/1")
        assert response.status_code == 200

        dataset = response.json()
        assert dataset["id"] == "1"
        assert dataset["name"] == "LEO Test Dataset"
        assert dataset["regime"] == "LEO"
        assert dataset["tier"] == "T1"
        assert dataset["status"] == "available"
        assert dataset["observation_count"] == 1000
        assert dataset["satellite_count"] == 5

    def test_get_dataset_includes_detail_fields(self, populated_test_client: TestClient):
        """Test that dataset detail includes additional fields."""
        response = populated_test_client.get("/api/v1/datasets/1")
        assert response.status_code == 200

        dataset = response.json()
        # Detail fields should be present
        assert "satellites" in dataset
        assert "parameters" in dataset


class TestHasReferenceOrbits:
    """
    Regression coverage for QA_PROD_RUN_2026-04-17 C1.

    The /datasets list + detail responses expose `has_reference_orbits`
    via an EXISTS subquery on dataset_references. The frontend gates the
    Submit dropdown on this — if the subquery ever broke, users could
    again submit against datasets that fail evaluation with "no reference
    state vectors persisted".

    Tests run the subquery directly against the `db` fixture rather than
    going through FastAPI TestClient. The TestClient route gets blocked
    by an unrelated pre-existing schema issue with the populated_db
    fixture under DuckDB.
    """

    def _insert_dataset(self, db, dataset_id: int, name: str):
        db.execute(
            """
            INSERT INTO datasets (id, name, code, tier, orbital_regime, status,
                                  observation_count, satellite_count, created_at)
            VALUES (?, ?, ?, 'T1', 'LEO', 'available', 100, 1, CURRENT_TIMESTAMP)
            """,
            (dataset_id, name, name),
        )

    def _insert_reference(self, db, dataset_id: int, sat_no: int):
        db.execute(
            """
            INSERT INTO dataset_references
                (dataset_id, sat_no, state_vector_id, element_set_id, grouped_obs_ids)
            VALUES (?, ?, NULL, NULL, NULL)
            """,
            (dataset_id, sat_no),
        )

    def _has_reference_orbits(self, db, dataset_id: int) -> bool:
        """Run the production EXISTS subquery and return its bool."""
        df = db.adapter.fetchdf(
            """
            SELECT EXISTS(
                SELECT 1 FROM dataset_references r WHERE r.dataset_id = datasets.id
            ) AS has_reference_orbits
            FROM datasets WHERE id = ?
            """,
            (dataset_id,),
        )
        assert not df.empty, f"dataset {dataset_id} not found"
        return bool(df.iloc[0]["has_reference_orbits"])

    def test_subquery_returns_false_without_refs(self, db):
        """A dataset with zero dataset_references rows resolves to False."""
        self._insert_dataset(db, 1001, "no-refs-dataset")
        assert self._has_reference_orbits(db, 1001) is False

    def test_subquery_returns_true_when_refs_exist(self, db):
        """A dataset with at least one dataset_references row resolves to True."""
        self._insert_dataset(db, 1002, "with-refs-dataset")
        self._insert_reference(db, 1002, sat_no=42)
        assert self._has_reference_orbits(db, 1002) is True

    def test_subquery_isolates_per_dataset(self, db):
        """Inserting refs for dataset A does not flip has_reference_orbits for B."""
        self._insert_dataset(db, 1003, "ds-a")
        self._insert_dataset(db, 1004, "ds-b")
        self._insert_reference(db, 1003, sat_no=7)
        # Only ds-a should report True.
        assert self._has_reference_orbits(db, 1003) is True
        assert self._has_reference_orbits(db, 1004) is False

    def test_pydantic_model_includes_field(self):
        """DatasetSummary serializes has_reference_orbits with a default of False."""
        from backend_api.models import DatasetSummary

        # Default-constructed model must default the field to False.
        ds = DatasetSummary(
            id="1",
            name="x",
            regime="LEO",
            tier="T1",
            status="available",
            created_at=__import__("datetime").datetime.now(),
        )
        dumped = ds.model_dump()
        assert "has_reference_orbits" in dumped
        assert dumped["has_reference_orbits"] is False

        # Explicit True must round-trip.
        ds2 = DatasetSummary(
            id="2",
            name="y",
            regime="LEO",
            tier="T1",
            status="available",
            created_at=__import__("datetime").datetime.now(),
            has_reference_orbits=True,
        )
        assert ds2.model_dump()["has_reference_orbits"] is True


class TestCreateDataset:
    """Tests for POST /api/v1/datasets endpoint."""

    @patch("backend_api.routers.datasets.submit_dataset_generation")
    def test_create_dataset_success(
        self,
        mock_submit: MagicMock,
        test_client: TestClient,
        sample_dataset_create: dict,
    ):
        """Test creating a new dataset."""
        # Mock the job submission
        mock_job = MagicMock()
        mock_job.id = "test-job-123"
        mock_submit.return_value = mock_job

        response = test_client.post(
            "/api/v1/datasets/",
            json=sample_dataset_create,
        )

        assert response.status_code == 200
        dataset = response.json()
        assert dataset["name"] == sample_dataset_create["name"]
        assert dataset["status"] == "generating"
        assert dataset["job_id"] == "test-job-123"

    def test_create_dataset_invalid_regime(self, test_client: TestClient):
        """Test creating a dataset with invalid regime."""
        response = test_client.post(
            "/api/v1/datasets/",
            json={
                "name": "Test",
                "regime": "INVALID",
                "tier": "T1",
                "object_count": 5,
                "timeframe": 7,
                "timeunit": "days",
                "sensors": ["optical"],
            },
        )
        assert response.status_code == 422  # Validation error

    def test_create_dataset_invalid_tier(self, test_client: TestClient):
        """Test creating a dataset with invalid tier."""
        response = test_client.post(
            "/api/v1/datasets/",
            json={
                "name": "Test",
                "regime": "LEO",
                "tier": "T99",
                "object_count": 5,
                "timeframe": 7,
                "timeunit": "days",
                "sensors": ["optical"],
            },
        )
        assert response.status_code == 422  # Validation error

    def test_create_dataset_missing_required_fields(self, test_client: TestClient):
        """Test creating a dataset with missing required fields."""
        response = test_client.post(
            "/api/v1/datasets/",
            json={"name": "Test"},
        )
        assert response.status_code == 422  # Validation error

    def test_create_dataset_timeframe_exceeds_max(self, test_client: TestClient):
        """Test creating a dataset with timeframe > 90 days fails validation."""
        response = test_client.post(
            "/api/v1/datasets/",
            json={
                "name": "Test",
                "regime": "LEO",
                "tier": "T1",
                "object_count": 5,
                "timeframe": 91,  # Exceeds max of 90
                "timeunit": "days",
                "sensors": ["optical"],
            },
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        # Pydantic returns list of errors
        assert any(
            e["loc"] == ["body", "timeframe"] and "less than or equal to 90" in e["msg"]
            for e in detail
        )

    def test_create_dataset_timeframe_large_value(self, test_client: TestClient):
        """Test creating a dataset with very large timeframe fails validation."""
        response = test_client.post(
            "/api/v1/datasets/",
            json={
                "name": "Test",
                "regime": "LEO",
                "tier": "T1",
                "object_count": 5,
                "timeframe": 419,  # Large value like in the reported error
                "timeunit": "days",
                "sensors": ["optical"],
            },
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any(
            e["loc"] == ["body", "timeframe"] and "less than or equal to 90" in e["msg"]
            for e in detail
        )

    def test_create_dataset_timeframe_zero(self, test_client: TestClient):
        """Test creating a dataset with timeframe = 0 fails validation."""
        response = test_client.post(
            "/api/v1/datasets/",
            json={
                "name": "Test",
                "regime": "LEO",
                "tier": "T1",
                "object_count": 5,
                "timeframe": 0,  # Less than min of 1
                "timeunit": "days",
                "sensors": ["optical"],
            },
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any(
            e["loc"] == ["body", "timeframe"] and "greater than or equal to 1" in e["msg"]
            for e in detail
        )

    def test_create_dataset_timeframe_negative(self, test_client: TestClient):
        """Test creating a dataset with negative timeframe fails validation."""
        response = test_client.post(
            "/api/v1/datasets/",
            json={
                "name": "Test",
                "regime": "LEO",
                "tier": "T1",
                "object_count": 5,
                "timeframe": -5,
                "timeunit": "days",
                "sensors": ["optical"],
            },
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any(e["loc"] == ["body", "timeframe"] for e in detail)

    @patch("backend_api.routers.datasets.submit_dataset_generation")
    def test_create_dataset_timeframe_at_max_boundary(
        self,
        mock_submit: MagicMock,
        test_client: TestClient,
    ):
        """Test creating a dataset with timeframe = 90 (max boundary) succeeds."""
        mock_job = MagicMock()
        mock_job.id = "test-job-123"
        mock_submit.return_value = mock_job

        response = test_client.post(
            "/api/v1/datasets/",
            json={
                "name": "Test",
                "regime": "LEO",
                "tier": "T1",
                "object_count": 5,
                "timeframe": 90,  # Exactly at max boundary
                "timeunit": "days",
                "sensors": ["optical"],
            },
        )
        assert response.status_code == 200

    @patch("backend_api.routers.datasets.submit_dataset_generation")
    def test_create_dataset_timeframe_at_min_boundary(
        self,
        mock_submit: MagicMock,
        test_client: TestClient,
    ):
        """Test creating a dataset with timeframe = 1 (min boundary) succeeds."""
        mock_job = MagicMock()
        mock_job.id = "test-job-123"
        mock_submit.return_value = mock_job

        response = test_client.post(
            "/api/v1/datasets/",
            json={
                "name": "Test",
                "regime": "LEO",
                "tier": "T1",
                "object_count": 5,
                "timeframe": 1,  # Exactly at min boundary
                "timeunit": "days",
                "sensors": ["optical"],
            },
        )
        assert response.status_code == 200


class TestGetDatasetObservations:
    """Tests for GET /api/v1/datasets/{id}/observations endpoint."""

    def test_get_observations_dataset_not_found(self, test_client: TestClient):
        """Test getting observations for non-existent dataset returns 404."""
        response = test_client.get("/api/v1/datasets/99999/observations")
        assert response.status_code == 404

    def test_get_observations_empty(self, populated_test_client: TestClient):
        """Test getting observations when dataset has none."""
        response = populated_test_client.get("/api/v1/datasets/1/observations")
        assert response.status_code == 200

        data = response.json()
        assert data["dataset_id"] == "1"
        assert "observations" in data
        assert "total_count" in data

    def test_get_observations_pagination(self, populated_test_client: TestClient):
        """Test observation pagination parameters."""
        response = populated_test_client.get("/api/v1/datasets/1/observations?limit=10&offset=5")
        assert response.status_code == 200

        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 5


class TestDownloadDataset:
    """Tests for GET /api/v1/datasets/{id}/download endpoint."""

    def test_download_dataset_not_found(self, test_client: TestClient):
        """Test downloading non-existent dataset returns 404."""
        response = test_client.get("/api/v1/datasets/99999/download")
        assert response.status_code == 404

    def test_download_dataset_not_available(self, populated_test_client: TestClient):
        """Test downloading dataset that is not available returns 400."""
        response = populated_test_client.get("/api/v1/datasets/3/download")
        assert response.status_code == 400
        assert "not available" in response.json()["detail"].lower()

    def test_download_dataset_success(self, populated_test_client: TestClient):
        """Test downloading an available dataset."""
        response = populated_test_client.get("/api/v1/datasets/1/download")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        # Check JSON structure
        data = response.json()
        assert "dataset" in data
        assert "observations" in data
        assert data["dataset"]["id"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
