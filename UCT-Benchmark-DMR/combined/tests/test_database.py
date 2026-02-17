"""
Unit tests for the UCT Benchmark database module.

Run with: uv run pytest tests/test_database.py -v
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

# Import directly from submodules to avoid circular import in uct_benchmark.config
from uct_benchmark.database.connection import DatabaseManager
from uct_benchmark.database.export import (
    export_dataset_to_json,
    export_observations_to_parquet,
    import_dataset_from_json,
)
from uct_benchmark.database.ingestion import (
    DataIngestionPipeline,
    IngestionReport,
)
from uct_benchmark.database.schema import (
    SCHEMA_VERSION,
    get_schema_version,
    verify_schema,
)


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    db = DatabaseManager(in_memory=True)
    db.initialize()
    return db


@pytest.fixture
def populated_db(db):
    """Create a database with sample data."""
    # Add satellites
    db.satellites.create(
        sat_no=25544,
        name="ISS (ZARYA)",
        orbital_regime="LEO",
        object_type="PAYLOAD",
    )
    db.satellites.create(
        sat_no=43013,
        name="STARLINK-1234",
        orbital_regime="LEO",
        object_type="PAYLOAD",
    )

    # Add observations
    base_time = datetime(2025, 1, 1, 12, 0, 0)
    obs_data = []
    for i in range(10):
        obs_data.append(
            {
                "id": f"obs-{i}",
                "sat_no": 25544,
                "ob_time": base_time + timedelta(hours=i),
                "ra": 100.0 + i,
                "declination": 45.0 + i * 0.1,
                "sensor_name": "TEST_SENSOR",
                "data_mode": "REAL",
            }
        )

    obs_df = pd.DataFrame(obs_data)
    db.observations.bulk_insert(obs_df)

    # Add state vectors
    db.state_vectors.create(
        sat_no=25544,
        epoch=base_time,
        x_pos=6678.0,
        y_pos=0.0,
        z_pos=0.0,
        x_vel=0.0,
        y_vel=7.8,
        z_vel=0.0,
        source="TEST",
    )

    # Add element sets
    db.element_sets.create(
        sat_no=25544,
        line1="1 25544U 98067A   25001.50000000  .00016717  00000-0  10270-3 0  9995",
        line2="2 25544  51.6416 339.8501 0006720  22.0000 338.1000 15.48919100000000",
        epoch=base_time,
        inclination=51.6416,
        eccentricity=0.000672,
        mean_motion=15.489191,
        source="TEST",
    )

    return db


class TestDatabaseManager:
    """Tests for DatabaseManager."""

    def test_init_in_memory(self):
        """Test creating an in-memory database."""
        db = DatabaseManager(in_memory=True)
        assert db.in_memory is True
        assert db.db_path == ":memory:"

    def test_init_file_based(self):
        """Test creating a file-based database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            db = DatabaseManager(db_path=db_path)
            assert db.in_memory is False
            assert db.db_path == db_path

    def test_initialize_schema(self, db):
        """Test schema initialization."""
        assert db.is_initialized() is True

        verification = verify_schema(db)
        assert verification["valid"] is True
        assert verification["schema_version"] == SCHEMA_VERSION

    def test_get_statistics(self, db):
        """Test getting database statistics."""
        stats = db.get_statistics()
        assert "satellites" in stats
        assert "observations" in stats
        assert "datasets" in stats

    def test_execute(self, db):
        """Test direct SQL execution."""
        result = db.execute("SELECT 1 + 1 AS result").fetchone()
        assert result[0] == 2

    def test_context_manager(self):
        """Test using DatabaseManager as context manager."""
        with DatabaseManager(in_memory=True) as db:
            db.initialize()
            assert db.is_initialized()


class TestSatelliteRepository:
    """Tests for SatelliteRepository."""

    def test_create_and_get(self, db):
        """Test creating and retrieving a satellite."""
        sat_no = db.satellites.create(
            sat_no=12345,
            name="TEST SAT",
            orbital_regime="LEO",
        )
        assert sat_no == 12345

        sat = db.satellites.get(12345)
        assert sat is not None
        assert sat["name"] == "TEST SAT"
        assert sat["orbital_regime"] == "LEO"

    def test_get_nonexistent(self, db):
        """Test getting a non-existent satellite."""
        sat = db.satellites.get(99999)
        assert sat is None

    def test_update(self, db):
        """Test updating a satellite."""
        db.satellites.create(sat_no=12345, name="OLD NAME")
        db.satellites.update(12345, name="NEW NAME", orbital_regime="GEO")

        sat = db.satellites.get(12345)
        assert sat["name"] == "NEW NAME"
        assert sat["orbital_regime"] == "GEO"

    def test_delete(self, db):
        """Test deleting a satellite."""
        db.satellites.create(sat_no=12345, name="TO DELETE")
        db.satellites.delete(12345)

        sat = db.satellites.get(12345)
        assert sat is None

    def test_get_by_regime(self, populated_db):
        """Test getting satellites by orbital regime."""
        leo_sats = populated_db.satellites.get_by_regime("LEO")
        assert len(leo_sats) == 2

        geo_sats = populated_db.satellites.get_by_regime("GEO")
        assert len(geo_sats) == 0

    def test_count(self, populated_db):
        """Test counting satellites."""
        count = populated_db.satellites.count()
        assert count == 2


class TestObservationRepository:
    """Tests for ObservationRepository."""

    def test_bulk_insert(self, db):
        """Test bulk inserting observations."""
        obs_data = [
            {
                "id": f"obs-{i}",
                "sat_no": 25544,
                "ob_time": datetime(2025, 1, 1, i, 0, 0),
                "ra": 100.0,
                "declination": 45.0,
            }
            for i in range(5)
        ]
        df = pd.DataFrame(obs_data)
        count = db.observations.bulk_insert(df)
        assert count == 5

    def test_get_by_satellite_time_window(self, populated_db):
        """Test querying by satellite and time window."""
        start = datetime(2025, 1, 1, 12, 0, 0)
        end = datetime(2025, 1, 1, 17, 0, 0)

        obs = populated_db.observations.get_by_satellite_time_window(
            sat_no=25544, start_time=start, end_time=end
        )
        assert len(obs) == 6  # Hours 0-5

    def test_get_statistics(self, populated_db):
        """Test getting observation statistics."""
        stats = populated_db.observations.get_statistics()
        assert len(stats) == 1
        assert stats.iloc[0]["sat_no"] == 25544
        assert stats.iloc[0]["obs_count"] == 10

    def test_count_by_satellite(self, populated_db):
        """Test counting observations by satellite."""
        count = populated_db.observations.count_by_satellite(25544)
        assert count == 10

        count = populated_db.observations.count_by_satellite(99999)
        assert count == 0


class TestStateVectorRepository:
    """Tests for StateVectorRepository."""

    def test_create_and_get(self, db):
        """Test creating and retrieving a state vector."""
        epoch = datetime(2025, 1, 1, 12, 0, 0)
        sv_id = db.state_vectors.create(
            sat_no=25544,
            epoch=epoch,
            x_pos=6678.0,
            y_pos=0.0,
            z_pos=0.0,
            x_vel=0.0,
            y_vel=7.8,
            z_vel=0.0,
            source="TEST",
        )
        assert sv_id > 0

        sv = db.state_vectors.get(sv_id)
        assert sv is not None
        assert float(sv["x_pos"]) == 6678.0

    def test_get_latest(self, db):
        """Test getting latest state vector."""
        epoch1 = datetime(2025, 1, 1, 12, 0, 0)
        epoch2 = datetime(2025, 1, 2, 12, 0, 0)

        db.state_vectors.create(
            sat_no=25544,
            epoch=epoch1,
            x_pos=1.0,
            y_pos=0.0,
            z_pos=0.0,
            x_vel=0.0,
            y_vel=0.0,
            z_vel=0.0,
            source="TEST1",
        )
        db.state_vectors.create(
            sat_no=25544,
            epoch=epoch2,
            x_pos=2.0,
            y_pos=0.0,
            z_pos=0.0,
            x_vel=0.0,
            y_vel=0.0,
            z_vel=0.0,
            source="TEST2",
        )

        latest = db.state_vectors.get_latest(25544)
        assert float(latest["x_pos"]) == 2.0


class TestElementSetRepository:
    """Tests for ElementSetRepository."""

    def test_create_and_get(self, db):
        """Test creating and retrieving an element set."""
        epoch = datetime(2025, 1, 1, 12, 0, 0)
        elset_id = db.element_sets.create(
            sat_no=25544,
            line1="1 25544U 98067A   25001.50000000 ...",
            line2="2 25544  51.6416 339.8501 ...",
            epoch=epoch,
            inclination=51.6416,
            mean_motion=15.489,
            source="TEST",
        )
        assert elset_id > 0

        elset = db.element_sets.get(elset_id)
        assert elset is not None
        assert float(elset["inclination"]) == pytest.approx(51.6416, rel=1e-4)


class TestDatasetRepository:
    """Tests for DatasetRepository."""

    def test_create_dataset(self, db):
        """Test creating a dataset."""
        dataset_id = db.datasets.create_dataset(
            name="Test Dataset",
            code="LEO_A_H_H_H",
            tier="T1",
            orbital_regime="LEO",
        )
        assert dataset_id > 0

    def test_get_dataset_by_id(self, db):
        """Test getting a dataset by ID."""
        dataset_id = db.datasets.create_dataset(name="Test Dataset")
        dataset = db.datasets.get_dataset(dataset_id=dataset_id)
        assert dataset is not None
        assert dataset["name"] == "Test Dataset"

    def test_get_dataset_by_name(self, db):
        """Test getting a dataset by name."""
        db.datasets.create_dataset(name="Named Dataset")
        dataset = db.datasets.get_dataset(name="Named Dataset")
        assert dataset is not None
        assert dataset["name"] == "Named Dataset"

    def test_list_datasets(self, db):
        """Test listing datasets."""
        db.datasets.create_dataset(name="Dataset 1", tier="T1", orbital_regime="LEO")
        db.datasets.create_dataset(name="Dataset 2", tier="T2", orbital_regime="GEO")

        all_datasets = db.datasets.list_datasets()
        assert len(all_datasets) == 2

        leo_datasets = db.datasets.list_datasets(orbital_regime="LEO")
        assert len(leo_datasets) == 1

    def test_update_dataset(self, db):
        """Test updating a dataset."""
        dataset_id = db.datasets.create_dataset(name="Test Dataset")
        db.datasets.update_dataset(dataset_id, status="complete", observation_count=100)

        dataset = db.datasets.get_dataset(dataset_id=dataset_id)
        assert dataset["status"] == "complete"
        assert dataset["observation_count"] == 100

    def test_delete_dataset(self, db):
        """Test deleting a dataset."""
        dataset_id = db.datasets.create_dataset(name="To Delete")
        db.datasets.delete_dataset(dataset_id)

        dataset = db.datasets.get_dataset(dataset_id=dataset_id)
        assert dataset is None

    def test_create_version(self, db):
        """Test creating a dataset version."""
        parent_id = db.datasets.create_dataset(
            name="Original Dataset",
            generation_params={"param1": "value1"},
        )

        child_id = db.datasets.create_version(parent_id, changes={"param2": "value2"})

        child = db.datasets.get_dataset(dataset_id=child_id)
        assert child is not None
        assert child["parent_id"] == parent_id
        assert child["version"] == 2

    def test_get_dataset_versions(self, db):
        """Test getting dataset version history."""
        parent_id = db.datasets.create_dataset(name="Versioned Dataset")
        db.datasets.create_version(parent_id)
        db.datasets.create_version(parent_id)

        versions = db.datasets.get_dataset_versions(parent_id)
        assert len(versions) >= 1  # At least the original

    def test_add_observations_to_dataset(self, populated_db):
        """Test adding observations to a dataset."""
        dataset_id = populated_db.datasets.create_dataset(name="Test Dataset")

        obs_ids = [f"obs-{i}" for i in range(5)]
        track_assignments = {f"obs-{i}": i + 1 for i in range(5)}

        count = populated_db.datasets.add_observations_to_dataset(
            dataset_id, obs_ids, track_assignments
        )
        assert count == 5

    def test_get_dataset_observations(self, populated_db):
        """Test getting observations for a dataset."""
        dataset_id = populated_db.datasets.create_dataset(name="Test Dataset")
        obs_ids = [f"obs-{i}" for i in range(5)]
        populated_db.datasets.add_observations_to_dataset(dataset_id, obs_ids)

        obs = populated_db.datasets.get_dataset_observations(dataset_id)
        assert len(obs) == 5

    def test_compare_datasets(self, populated_db):
        """Test comparing two datasets."""
        ds1_id = populated_db.datasets.create_dataset(name="Dataset 1")
        ds2_id = populated_db.datasets.create_dataset(name="Dataset 2")

        # Add overlapping observations
        populated_db.datasets.add_observations_to_dataset(ds1_id, [f"obs-{i}" for i in range(5)])
        populated_db.datasets.add_observations_to_dataset(ds2_id, [f"obs-{i}" for i in range(3, 8)])

        comparison = populated_db.datasets.compare_datasets(ds1_id, ds2_id)
        assert comparison["dataset_1"]["observation_count"] == 5
        assert comparison["dataset_2"]["observation_count"] == 5
        assert comparison["common_observations"] == 2  # obs-3, obs-4


class TestEventRepository:
    """Tests for EventRepository."""

    def test_create_event(self, populated_db):
        """Test creating an event."""
        event_id = populated_db.events.create_event(
            event_type="maneuver",
            primary_sat_no=25544,
            event_time_start=datetime(2025, 1, 1, 12, 0, 0),
            confidence=0.95,
        )
        assert event_id > 0

    def test_get_events_for_satellite(self, populated_db):
        """Test getting events for a satellite."""
        populated_db.events.create_event(
            event_type="maneuver",
            primary_sat_no=25544,
            event_time_start=datetime(2025, 1, 1, 12, 0, 0),
        )
        populated_db.events.create_event(
            event_type="launch",
            primary_sat_no=25544,
            event_time_start=datetime(2025, 1, 2, 12, 0, 0),
        )

        events = populated_db.events.get_events_for_satellite(25544)
        assert len(events) == 2

        maneuvers = populated_db.events.get_events_for_satellite(25544, event_type="maneuver")
        assert len(maneuvers) == 1


class TestDataIngestionPipeline:
    """Tests for DataIngestionPipeline."""

    def test_ingest_observations(self, db):
        """Test ingesting observations from DataFrame."""
        pipeline = DataIngestionPipeline(db)

        obs_data = [
            {
                "id": f"obs-{i}",
                "sat_no": 25544,
                "ob_time": datetime(2025, 1, 1, i, 0, 0),
                "ra": 100.0,
                "declination": 45.0,
            }
            for i in range(10)
        ]
        df = pd.DataFrame(obs_data)

        report = pipeline.ingest_observations_from_dataframe(df)
        assert report.inserted_records == 10
        assert report.failed_records == 0

    def test_ingest_with_validation_error(self, db):
        """Test ingestion with invalid data."""
        pipeline = DataIngestionPipeline(db)

        # Missing required columns
        df = pd.DataFrame([{"foo": "bar"}])
        report = pipeline.ingest_observations_from_dataframe(df)
        assert len(report.validation_errors) > 0


class TestIngestionReport:
    """Tests for IngestionReport."""

    def test_report_initialization(self):
        """Test report initialization."""
        report = IngestionReport()
        assert report.total_records == 0
        assert report.inserted_records == 0

    def test_add_success(self):
        """Test adding success records."""
        report = IngestionReport()
        report.add_success(25544, 10)
        assert 25544 in report.successes
        assert report.inserted_records == 10

    def test_add_failure(self):
        """Test adding failure records."""
        report = IngestionReport()
        report.add_failure(25544, "Error message")
        assert 25544 in report.failures
        assert report.failed_records == 1

    def test_success_rate(self):
        """Test success rate calculation."""
        report = IngestionReport()
        report.inserted_records = 80
        report.duplicate_records = 10
        report.failed_records = 10
        report.finalize()
        assert report.success_rate == pytest.approx(80.0, rel=0.01)


class TestExportImport:
    """Tests for export and import functionality."""

    def test_export_dataset_to_json(self, populated_db):
        """Test exporting a dataset to JSON."""
        # Create dataset with observations
        dataset_id = populated_db.datasets.create_dataset(
            name="Export Test",
            code="TEST_CODE",
            tier="T1",
            orbital_regime="LEO",
        )
        obs_ids = [f"obs-{i}" for i in range(5)]
        populated_db.datasets.add_observations_to_dataset(dataset_id, obs_ids)
        populated_db.datasets.update_dataset(dataset_id, observation_count=5, satellite_count=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_export.json"
            result_path = export_dataset_to_json(populated_db, dataset_id, output_path)

            assert result_path.exists()

            with open(result_path) as f:
                data = json.load(f)

            assert data["metadata"]["name"] == "Export Test"
            assert len(data["observations"]) == 5

    def test_import_dataset_from_json(self, db):
        """Test importing a dataset from JSON."""
        # Create a test JSON file
        test_data = {
            "metadata": {
                "name": "Imported Dataset",
                "code": "IMP_TEST",
                "tier": "T1",
                "orbital_regime": "LEO",
            },
            "observations": [
                {
                    "id": f"imp-obs-{i}",
                    "ob_time": "2025-01-01T12:00:00.000000Z",
                    "ra": 100.0,
                    "declination": 45.0,
                    "track_id": i,
                    "orig_object_id": 25544,
                }
                for i in range(3)
            ],
            "references": [
                {
                    "sat_no": 25544,
                    "sat_name": "TEST SAT",
                    "orbital_regime": "LEO",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "import_test.json"
            with open(json_path, "w") as f:
                json.dump(test_data, f)

            dataset_id = import_dataset_from_json(db, json_path)

            dataset = db.datasets.get_dataset(dataset_id=dataset_id)
            assert dataset is not None
            assert dataset["name"] == "Imported Dataset"

    def test_export_observations_to_parquet(self, populated_db):
        """Test exporting observations to Parquet."""
        pytest.importorskip("pyarrow", reason="pyarrow required for parquet export")
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "observations.parquet"
            result_path = export_observations_to_parquet(populated_db, output_path)

            assert result_path.exists()

            # Verify we can read it back
            df = pd.read_parquet(result_path)
            assert len(df) == 10


class TestSchemaVerification:
    """Tests for schema verification."""

    def test_verify_valid_schema(self, db):
        """Test verifying a valid schema."""
        results = verify_schema(db)
        assert results["valid"] is True
        assert len(results["missing_tables"]) == 0

    def test_get_schema_version(self, db):
        """Test getting schema version."""
        version = get_schema_version(db)
        assert version == SCHEMA_VERSION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
