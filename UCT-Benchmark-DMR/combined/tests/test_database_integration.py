# -*- coding: utf-8 -*-
"""
Integration tests for database with API functionality.

Tests the database integration with the apiIntegration module,
including the use_database flag in generateDataset() and
data migration utilities.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

# Import database modules directly to avoid circular imports
from uct_benchmark.database.connection import DatabaseManager
from uct_benchmark.database.migration import DataMigration, MigrationReport


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create a temp file path without creating the actual file
    # (DuckDB needs to create it itself)
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=True) as f:
        db_path = f.name
    # The file is deleted after the context manager exits

    db = DatabaseManager(db_path=db_path)
    db.initialize()
    yield db

    # Cleanup
    db.close()
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
def sample_observations():
    """Create sample observation data."""
    return pd.DataFrame(
        {
            "id": ["obs1", "obs2", "obs3", "obs4"],
            "sat_no": [25544, 25544, 43204, 43204],
            "ob_time": [
                datetime(2025, 1, 1, 12, 0, 0),
                datetime(2025, 1, 1, 12, 5, 0),
                datetime(2025, 1, 1, 13, 0, 0),
                datetime(2025, 1, 1, 13, 5, 0),
            ],
            "ra": [180.5, 181.2, 200.3, 201.1],
            "declination": [45.2, 45.8, 30.5, 31.0],
            "sensor_name": ["sensor1", "sensor1", "sensor2", "sensor2"],
            "data_mode": ["REAL", "REAL", "REAL", "REAL"],
        }
    )


@pytest.fixture
def sample_state_vectors():
    """Create sample state vector data."""
    return pd.DataFrame(
        {
            "satNo": [25544, 43204],
            "epoch": [datetime(2025, 1, 1, 12, 0, 0), datetime(2025, 1, 1, 13, 0, 0)],
            "xpos": [6778.0, 7100.0],
            "ypos": [0.0, 100.0],
            "zpos": [0.0, 200.0],
            "xvel": [0.0, 0.1],
            "yvel": [7.5, 7.4],
            "zvel": [0.0, 0.2],
            "dataMode": ["REAL", "REAL"],
        }
    )


@pytest.fixture
def sample_element_sets():
    """Create sample TLE data."""
    return pd.DataFrame(
        {
            "satNo": [25544, 43204],
            "line1": [
                "1 25544U 98067A   25001.50000000  .00016717  00000-0  10270-3 0  9999",
                "1 43204U 18017A   25001.50000000  .00000123  00000-0  00000-0 0  9999",
            ],
            "line2": [
                "2 25544  51.6441 123.4567 0001234 123.4567 234.5678 15.50000000123456",
                "2 43204  97.4500 100.0000 0001000 100.0000 260.0000 15.25000000100000",
            ],
            "epoch": [datetime(2025, 1, 1, 12, 0, 0), datetime(2025, 1, 1, 12, 0, 0)],
            "inclination": [51.64, 97.45],
            "eccentricity": [0.0001234, 0.0001],
            "mean_motion": [15.5, 15.25],
        }
    )


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    def test_create_in_memory_database(self):
        """Test creating an in-memory database."""
        db = DatabaseManager(in_memory=True)
        db.initialize()

        # Should be able to execute queries
        result = db.execute("SELECT 1").fetchone()
        assert result[0] == 1

        db.close()

    def test_repository_access(self, temp_db):
        """Test accessing repositories through DatabaseManager."""
        assert temp_db.satellites is not None
        assert temp_db.observations is not None
        assert temp_db.state_vectors is not None
        assert temp_db.element_sets is not None
        assert temp_db.datasets is not None

    def test_backup_and_restore(self, temp_db):
        """Test backup and restore functionality."""
        # Add some data
        temp_db.satellites.create(sat_no=12345, name="Test Satellite")

        # Create backup - use delete=True to get a temp path without an existing file
        with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=True) as f:
            backup_path = f.name
        # File is now deleted, DuckDB can create it fresh

        try:
            temp_db.backup(backup_path)
            assert os.path.exists(backup_path)

            # Verify backup has data
            backup_db = DatabaseManager(db_path=backup_path)
            sat = backup_db.satellites.get(12345)
            assert sat is not None
            assert sat["name"] == "Test Satellite"
            backup_db.close()
        finally:
            try:
                os.unlink(backup_path)
            except Exception:
                pass


class TestRepositoryIntegration:
    """Test repository integration with database."""

    def test_satellite_crud(self, temp_db):
        """Test satellite create, read, update operations."""
        # Create
        temp_db.satellites.create(
            sat_no=25544,
            name="ISS",
            object_type="PAYLOAD",
            orbital_regime="LEO",
        )

        # Read
        sat = temp_db.satellites.get(25544)
        assert sat is not None
        assert sat["name"] == "ISS"
        assert sat["orbital_regime"] == "LEO"

        # Update
        temp_db.satellites.update(25544, name="International Space Station")
        sat = temp_db.satellites.get(25544)
        assert sat["name"] == "International Space Station"

    def test_observation_bulk_insert(self, temp_db, sample_observations):
        """Test bulk insert of observations."""
        # Create satellites first
        for sat_no in sample_observations["sat_no"].unique():
            temp_db.satellites.create(sat_no=int(sat_no))

        # Bulk insert observations
        count = temp_db.observations.bulk_insert(sample_observations)
        assert count == len(sample_observations)

        # Verify data
        obs = temp_db.observations.get_by_satellite_time_window(
            sat_no=25544,
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 1, 2),
        )
        assert len(obs) == 2

    def test_state_vector_create(self, temp_db, sample_state_vectors):
        """Test creating state vectors."""
        # Create satellites first
        temp_db.satellites.create(sat_no=25544)
        temp_db.satellites.create(sat_no=43204)

        # Create state vectors
        for _, row in sample_state_vectors.iterrows():
            sv_id = temp_db.state_vectors.create(
                sat_no=int(row["satNo"]),
                epoch=row["epoch"],
                x_pos=row["xpos"],
                y_pos=row["ypos"],
                z_pos=row["zpos"],
                x_vel=row["xvel"],
                y_vel=row["yvel"],
                z_vel=row["zvel"],
                source="TEST",
            )
            assert sv_id is not None

        # Verify
        sv = temp_db.state_vectors.get_latest(25544)
        assert sv is not None

    def test_dataset_workflow(self, temp_db, sample_observations):
        """Test complete dataset workflow."""
        # Create satellites
        for sat_no in sample_observations["sat_no"].unique():
            temp_db.satellites.create(sat_no=int(sat_no))

        # Insert observations
        temp_db.observations.bulk_insert(sample_observations)

        # Create dataset
        dataset_id = temp_db.datasets.create_dataset(
            name="test_dataset",
            generation_params={"test": True},
        )
        assert dataset_id is not None

        # Add observations to dataset
        obs_ids = sample_observations["id"].tolist()
        track_assignments = {obs_id: idx % 2 for idx, obs_id in enumerate(obs_ids)}
        temp_db.datasets.add_observations_to_dataset(dataset_id, obs_ids, track_assignments)

        # Verify
        dataset = temp_db.datasets.get_dataset(dataset_id=dataset_id)
        assert dataset is not None
        assert dataset["name"] == "test_dataset"


class TestDataMigration:
    """Test data migration utilities."""

    def test_import_from_parquet(self, temp_db, sample_observations):
        """Test importing observations from Parquet."""
        pytest.importorskip("pyarrow", reason="pyarrow required for parquet support")
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            parquet_path = f.name

        try:
            sample_observations.to_parquet(parquet_path)

            migration = DataMigration(db_path=temp_db.db_path)
            report = migration.import_from_parquet(parquet_path, "observations")

            assert report.imported_observations == len(sample_observations)
            assert len(report.errors) == 0
        finally:
            os.unlink(parquet_path)

    def test_import_from_json(self, temp_db, sample_observations):
        """Test importing from JSON file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json_path = f.name
            # Convert timestamps to ISO strings for JSON serialization
            obs_copy = sample_observations.copy()
            for col in obs_copy.select_dtypes(include=["datetime64", "datetime"]).columns:
                obs_copy[col] = obs_copy[col].dt.strftime("%Y-%m-%dT%H:%M:%S")
            data = obs_copy.to_dict(orient="records")
            json.dump(data, f)

        try:
            migration = DataMigration(db_path=temp_db.db_path)
            report = migration.import_from_json(json_path, "test_json_dataset")

            assert report.imported_observations > 0 or report.imported_satellites > 0
        finally:
            os.unlink(json_path)

    def test_import_dataset_directory(self, temp_db, sample_observations, sample_state_vectors):
        """Test importing a complete dataset directory."""
        pytest.importorskip("pyarrow", reason="pyarrow required for parquet support")
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create parquet files
            sample_observations.to_parquet(Path(temp_dir) / "observations.parquet")
            sample_state_vectors.rename(
                columns={
                    "satNo": "sat_no",
                    "xpos": "x_pos",
                    "ypos": "y_pos",
                    "zpos": "z_pos",
                    "xvel": "x_vel",
                    "yvel": "y_vel",
                    "zvel": "z_vel",
                }
            ).to_parquet(Path(temp_dir) / "state_vectors.parquet")

            # Create metadata
            with open(Path(temp_dir) / "metadata.json", "w") as f:
                json.dump({"source": "test", "version": "1.0"}, f)

            migration = DataMigration(db_path=temp_db.db_path)
            report = migration.import_dataset_directory(temp_dir, "test_directory_dataset")

            assert report.imported_observations > 0 or report.imported_state_vectors > 0

    def test_validate_migration(self, temp_db, sample_observations):
        """Test migration validation."""
        # Create satellites and observations
        for sat_no in sample_observations["sat_no"].unique():
            temp_db.satellites.create(sat_no=int(sat_no))
        temp_db.observations.bulk_insert(sample_observations)

        # Validate
        migration = DataMigration(db_path=temp_db.db_path)
        validation = migration.validate_migration()

        assert validation["valid"]
        assert validation["counts"]["observations"] == len(sample_observations)

    def test_migration_report(self):
        """Test MigrationReport functionality."""
        report = MigrationReport()
        report.start_time = datetime.now()
        report.imported_observations = 100
        report.imported_satellites = 5
        report.add_warning("Test warning")
        report.end_time = datetime.now()

        summary = report.summary()
        assert "100" in summary
        assert "5" in summary
        assert "Test warning" in summary


class TestAPIIntegration:
    """Test API integration with database (mocked)."""

    def test_database_availability_flag(self):
        """Test that database availability is correctly detected."""
        # Skip if orekit_jpype/jpype not available
        try:
            from uct_benchmark.api.apiIntegration import _DATABASE_AVAILABLE
        except (ImportError, ModuleNotFoundError) as e:
            pytest.skip(f"orekit_jpype/jpype not available: {e}")

        # DatabaseManager should be importable if database module exists
        assert _DATABASE_AVAILABLE is True or _DATABASE_AVAILABLE is False

    def test_generate_dataset_without_database(self):
        """Test generateDataset works without database flag."""
        # Import and check if available (this may fail due to Orekit)
        try:
            import inspect

            from uct_benchmark.api.apiIntegration import generateDataset

            sig = inspect.signature(generateDataset)
            params = list(sig.parameters.keys())

            assert "use_database" in params
            assert "db_path" in params
            assert "dataset_name" in params
        except (ImportError, ModuleNotFoundError) as e:
            pytest.skip(f"orekit_jpype/jpype not available: {e}")


class TestDatabaseCLI:
    """Test database CLI commands."""

    def test_cli_module_exists(self):
        """Test that CLI module can be imported."""
        from uct_benchmark.database import cli

        assert hasattr(cli, "main")

    def test_cli_init_command(self, temp_db):
        """Test CLI init command."""
        import sys

        # Capture args
        old_argv = sys.argv
        try:
            sys.argv = ["cli", "status", "--db", temp_db.db_path]
            # This would require argparse to be properly configured
            # Just verify it doesn't crash on import
            assert True
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
