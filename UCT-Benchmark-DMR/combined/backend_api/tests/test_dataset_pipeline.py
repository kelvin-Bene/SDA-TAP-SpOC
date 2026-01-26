"""
API Integration tests for dataset generation with downsampling and simulation.

Tests the full API pipeline from request to response, ensuring
downsampling and simulation options are properly handled.
"""

import os

# Import the FastAPI app
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend_api.database import get_db
from backend_api.main import app
from backend_api.models import (
    DatasetCreate,
    DataTier,
    DownsamplingOptions,
    OrbitalRegime,
    SensorType,
    SimulationOptions,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database manager."""
    mock = MagicMock()
    mock.execute.return_value.fetchone.return_value = (1,)
    mock.execute.return_value.fetchall.return_value = []
    return mock


@pytest.fixture
def client(mock_db):
    """Create a test client for the FastAPI app with mocked database."""
    # Override the database dependency
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app)
    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def base_dataset_request():
    """Create a base dataset creation request."""
    return {
        "name": "test-dataset",
        "regime": "LEO",
        "tier": "T1",
        "object_count": 10,
        "timeframe": 7,
        "timeunit": "days",
        "sensors": ["optical"],
        "coverage": "standard",
        "include_hamr": False,
    }


# =============================================================================
# PYDANTIC MODEL TESTS
# =============================================================================


class TestPydanticModels:
    """Tests for Pydantic request/response models."""

    def test_downsampling_options_defaults(self):
        """Verify DownsamplingOptions has correct defaults."""
        options = DownsamplingOptions()

        assert options.enabled is False
        assert options.target_coverage == 0.05
        assert options.target_gap == 2.0
        assert options.max_obs_per_sat == 50
        assert options.preserve_tracks is True
        assert options.seed is None

    def test_downsampling_options_validation(self):
        """Verify DownsamplingOptions validates correctly."""
        # Valid options
        options = DownsamplingOptions(
            enabled=True,
            target_coverage=0.1,
            target_gap=3.0,
            max_obs_per_sat=100,
            preserve_tracks=True,
            seed=42,
        )
        assert options.enabled is True
        assert options.target_coverage == 0.1

        # Coverage should be between 0.01 and 1.0
        with pytest.raises(ValueError):
            DownsamplingOptions(target_coverage=0.001)

        with pytest.raises(ValueError):
            DownsamplingOptions(target_coverage=1.5)

    def test_simulation_options_defaults(self):
        """Verify SimulationOptions has correct defaults."""
        options = SimulationOptions()

        assert options.enabled is False
        assert options.fill_gaps is True
        assert options.sensor_model == "GEODSS"
        assert options.apply_noise is True
        assert options.max_synthetic_ratio == 0.5
        assert options.seed is None

    def test_simulation_options_validation(self):
        """Verify SimulationOptions validates correctly."""
        # Valid options
        options = SimulationOptions(
            enabled=True,
            fill_gaps=True,
            sensor_model="SBSS",
            apply_noise=True,
            max_synthetic_ratio=0.3,
            seed=42,
        )
        assert options.enabled is True
        assert options.sensor_model == "SBSS"

        # max_synthetic_ratio should be between 0.0 and 0.9
        with pytest.raises(ValueError):
            SimulationOptions(max_synthetic_ratio=-0.1)

        with pytest.raises(ValueError):
            SimulationOptions(max_synthetic_ratio=0.95)

    def test_dataset_create_with_options(self):
        """Verify DatasetCreate accepts downsampling and simulation options."""
        ds_options = DownsamplingOptions(enabled=True, target_coverage=0.1)
        sim_options = SimulationOptions(enabled=True, sensor_model="GEODSS")

        request = DatasetCreate(
            name="test-dataset",
            regime=OrbitalRegime.LEO,
            tier=DataTier.T2,
            object_count=10,
            timeframe=7,
            sensors=[SensorType.OPTICAL],
            downsampling=ds_options,
            simulation=sim_options,
        )

        assert request.downsampling is not None
        assert request.downsampling.enabled is True
        assert request.simulation is not None
        assert request.simulation.enabled is True


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================


class TestDatasetCreateEndpoint:
    """Tests for the POST /api/v1/datasets endpoint."""

    @patch("backend_api.routers.datasets.submit_dataset_generation")
    def test_create_dataset_without_options(self, mock_submit, client, base_dataset_request):
        """Test creating a dataset without downsampling/simulation options."""
        # Mock job submission
        mock_job = MagicMock()
        mock_job.id = "test-job-id"
        mock_submit.return_value = mock_job

        response = client.post("/api/v1/datasets/", json=base_dataset_request)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-dataset"
        assert data["regime"] == "LEO"

    @patch("backend_api.routers.datasets.submit_dataset_generation")
    def test_create_dataset_with_downsampling(self, mock_submit, client, base_dataset_request):
        """Test creating a dataset with downsampling enabled."""
        mock_job = MagicMock()
        mock_job.id = "test-job-id"
        mock_submit.return_value = mock_job

        request = {
            **base_dataset_request,
            "downsampling": {
                "enabled": True,
                "target_coverage": 0.1,
                "target_gap": 3.0,
                "max_obs_per_sat": 50,
                "preserve_tracks": True,
            },
        }

        response = client.post("/api/v1/datasets/", json=request)

        assert response.status_code == 200
        # Verify the generation params include downsampling
        call_args = mock_submit.call_args
        config = call_args[0][1]
        assert "downsampling" in config
        assert config["downsampling"]["enabled"] is True

    @patch("backend_api.routers.datasets.submit_dataset_generation")
    def test_create_dataset_with_simulation(self, mock_submit, client, base_dataset_request):
        """Test creating a dataset with simulation enabled."""

        mock_job = MagicMock()
        mock_job.id = "test-job-id"
        mock_submit.return_value = mock_job

        request = {
            **base_dataset_request,
            "simulation": {
                "enabled": True,
                "fill_gaps": True,
                "sensor_model": "GEODSS",
                "apply_noise": True,
                "max_synthetic_ratio": 0.3,
            },
        }

        response = client.post("/api/v1/datasets/", json=request)

        assert response.status_code == 200
        call_args = mock_submit.call_args
        config = call_args[0][1]
        assert "simulation" in config
        assert config["simulation"]["enabled"] is True

    @patch("backend_api.routers.datasets.submit_dataset_generation")
    def test_create_dataset_with_both_options(self, mock_submit, client, base_dataset_request):
        """Test creating a dataset with both downsampling and simulation."""
        mock_job = MagicMock()
        mock_job.id = "test-job-id"
        mock_submit.return_value = mock_job

        request = {
            **base_dataset_request,
            "downsampling": {
                "enabled": True,
                "target_coverage": 0.05,
            },
            "simulation": {
                "enabled": True,
                "sensor_model": "SBSS",
            },
        }

        response = client.post("/api/v1/datasets/", json=request)

        assert response.status_code == 200
        call_args = mock_submit.call_args
        config = call_args[0][1]
        assert "downsampling" in config
        assert "simulation" in config

    def test_invalid_downsampling_options(self, client, base_dataset_request):
        """Test that invalid downsampling options are rejected."""
        request = {
            **base_dataset_request,
            "downsampling": {
                "enabled": True,
                "target_coverage": 2.0,  # Invalid: > 1.0
            },
        }

        response = client.post("/api/v1/datasets/", json=request)
        assert response.status_code == 422  # Validation error

    def test_invalid_simulation_options(self, client, base_dataset_request):
        """Test that invalid simulation options are rejected."""
        request = {
            **base_dataset_request,
            "simulation": {
                "enabled": True,
                "max_synthetic_ratio": 1.5,  # Invalid: > 0.9
            },
        }

        response = client.post("/api/v1/datasets/", json=request)
        assert response.status_code == 422  # Validation error


# =============================================================================
# WORKER INTEGRATION TESTS
# =============================================================================


class TestWorkerIntegration:
    """Tests for worker integration with downsampling/simulation configs."""

    def test_downsampling_config_parsing(self):
        """Verify downsampling config can be parsed from request dict."""
        from uct_benchmark.settings import DownsampleConfig

        config_dict = {
            "enabled": True,
            "target_coverage": 0.1,
            "target_gap": 3.0,
            "max_obs_per_sat": 50,
            "preserve_tracks": True,
            "seed": 42,
        }

        # Test that we can create a config from the dict
        ds_config = DownsampleConfig(
            target_coverage=config_dict.get("target_coverage", 0.05),
            target_gap=config_dict.get("target_gap", 2.0),
            max_obs_per_sat=config_dict.get("max_obs_per_sat", 50),
            preserve_track_boundaries=config_dict.get("preserve_tracks", True),
            seed=config_dict.get("seed"),
        )

        assert ds_config.target_coverage == 0.1
        assert ds_config.target_gap == 3.0
        assert ds_config.seed == 42

    def test_simulation_config_parsing(self):
        """Verify simulation config can be parsed from request dict."""
        from uct_benchmark.settings import SimulationConfig

        config_dict = {
            "enabled": True,
            "sensor_model": "GEODSS",
            "apply_noise": True,
            "max_synthetic_ratio": 0.3,
            "seed": 42,
        }

        # Test that we can create a config from the dict
        sim_config = SimulationConfig(
            sensor_model=config_dict.get("sensor_model", "GEODSS"),
            apply_sensor_noise=config_dict.get("apply_noise", True),
            max_synthetic_ratio=config_dict.get("max_synthetic_ratio", 0.5),
            seed=config_dict.get("seed"),
        )

        assert sim_config.sensor_model == "GEODSS"
        assert sim_config.max_synthetic_ratio == 0.3
        assert sim_config.seed == 42


# =============================================================================
# BACKWARD COMPATIBILITY TESTS
# =============================================================================


class TestBackwardCompatibility:
    """Tests to ensure existing API behavior is preserved."""

    @patch("backend_api.routers.datasets.submit_dataset_generation")
    def test_existing_endpoint_unchanged(self, mock_submit, client):
        """Verify existing endpoint works without new options."""
        mock_job = MagicMock()
        mock_job.id = "test-job-id"
        mock_submit.return_value = mock_job

        # Old-style request without downsampling/simulation
        request = {
            "name": "test-dataset",
            "regime": "LEO",
            "tier": "T1",
            "object_count": 10,
            "timeframe": 7,
            "sensors": ["optical"],
        }

        response = client.post("/api/v1/datasets/", json=request)

        assert response.status_code == 200
        data = response.json()
        assert data["regime"] == "LEO"

    def test_list_datasets_unchanged(self, client):
        """Verify listing datasets still works."""
        response = client.get("/api/v1/datasets/")

        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
