"""
Comprehensive tests for the v2.0.0 dataset completeness overhaul.

Tests cover:
1. Schema migration (new tables, expanded columns)
2. Full observation storage (46+ fields)
3. Query parameter tracking
4. Config hash + dataset reuse
5. Data source attribution
6. State vector physical params
7. Enrichment log
8. Download + provenance endpoints
9. Integration / end-to-end

Run with: uv run pytest backend_api/tests/test_dataset_completeness.py -v
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from uct_benchmark.database.connection import DatabaseManager
from uct_benchmark.database.repository import (
    DatasetEnrichmentLogRepository,
    DatasetDataSourceRepository,
    DatasetQueryRepository,
    DatasetRepository,
    ObservationRepository,
    StateVectorRepository,
)
from uct_benchmark.api.apiIntegration import compute_config_hash


def _fetchone(db: DatabaseManager, query: str, params: tuple = ()):
    """Helper: execute SELECT and return single row (works for both DuckDB and Postgres)."""
    return db.adapter.fetchone(query, params)


# ============================================================
# GROUP 1: Schema Migration Tests
# ============================================================


class TestSchemaMigration:
    """Verify v2.0.0 schema creates all new tables and columns."""

    def test_schema_creates_dataset_queries_table(self, db: DatabaseManager):
        """Verify dataset_queries table exists after init."""
        # Simply select from it - if it doesn't exist, this will fail
        try:
            df = db.adapter.fetchdf("SELECT * FROM dataset_queries LIMIT 0")
            assert df is not None
        except Exception:
            pytest.fail("dataset_queries table does not exist")

    def test_schema_creates_dataset_data_sources_table(self, db: DatabaseManager):
        """Verify dataset_data_sources table exists after init."""
        try:
            df = db.adapter.fetchdf("SELECT * FROM dataset_data_sources LIMIT 0")
            assert df is not None
        except Exception:
            pytest.fail("dataset_data_sources table does not exist")

    def test_schema_creates_dataset_validation_measurements_table(self, db: DatabaseManager):
        """Verify dataset_validation_measurements table exists."""
        try:
            df = db.adapter.fetchdf("SELECT * FROM dataset_validation_measurements LIMIT 0")
            assert df is not None
        except Exception:
            pytest.fail("dataset_validation_measurements table does not exist")

    def test_schema_creates_dataset_enrichment_log_table(self, db: DatabaseManager):
        """Verify dataset_enrichment_log table exists."""
        try:
            df = db.adapter.fetchdf("SELECT * FROM dataset_enrichment_log LIMIT 0")
            assert df is not None
        except Exception:
            pytest.fail("dataset_enrichment_log table does not exist")

    def test_observations_has_sensor_position_columns(self, db: DatabaseManager):
        """Verify observations table has sensor position (geodetic + ECI) columns."""
        db.execute(
            """INSERT INTO observations (id, ob_time, senlat, senlon, senalt, senx, seny, senz)
               VALUES ('test-sp-1', CURRENT_TIMESTAMP, 32.0, -110.0, 2.3, 1234.0, -2345.0, 3456.0)"""
        )
        result = _fetchone(db, "SELECT senlat, senlon, senalt, senx, seny, senz FROM observations WHERE id = 'test-sp-1'")
        assert result is not None
        assert abs(float(result[0]) - 32.0) < 0.01

    def test_observations_has_photometric_columns(self, db: DatabaseManager):
        """Verify observations table has photometric columns."""
        db.execute(
            """INSERT INTO observations (id, ob_time, mag, mag_unc, los_unc, exp_duration)
               VALUES ('test-ph-1', CURRENT_TIMESTAMP, 12.3, 0.2, 0.5, 1.5)"""
        )
        result = _fetchone(db, "SELECT mag, mag_unc, los_unc, exp_duration FROM observations WHERE id = 'test-ph-1'")
        assert result is not None
        assert abs(float(result[0]) - 12.3) < 0.01

    def test_observations_has_solar_angle_columns(self, db: DatabaseManager):
        """Verify observations table has solar angle columns."""
        db.execute(
            """INSERT INTO observations (id, ob_time, solar_phase_angle, solar_eq_phase_angle, solar_dec_angle)
               VALUES ('test-sa-1', CURRENT_TIMESTAMP, 60.0, 45.0, 30.0)"""
        )
        result = _fetchone(
            db, "SELECT solar_phase_angle, solar_eq_phase_angle, solar_dec_angle FROM observations WHERE id = 'test-sa-1'"
        )
        assert result is not None
        assert abs(float(result[0]) - 60.0) < 0.01

    def test_observations_has_udl_admin_columns(self, db: DatabaseManager):
        """Verify observations table has UDL administrative columns."""
        db.execute(
            """INSERT INTO observations (id, ob_time, classification_marking, id_sensor, source_name, observation_type_udl)
               VALUES ('test-ua-1', CURRENT_TIMESTAMP, 'U', 'SENSOR-001', 'EXO', 'OPTICAL')"""
        )
        result = _fetchone(
            db, "SELECT classification_marking, id_sensor, source_name, observation_type_udl FROM observations WHERE id = 'test-ua-1'"
        )
        assert result is not None
        assert result[0] == "U"
        assert result[1] == "SENSOR-001"

    def test_datasets_has_config_hash_column(self, db: DatabaseManager):
        """Verify datasets table has config_hash column."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, config_hash, created_at)
               VALUES (9001, 'Hash Test', 'HT', 'T1', 'LEO', 'available', 'abc123def456', CURRENT_TIMESTAMP)"""
        )
        result = _fetchone(db, "SELECT config_hash FROM datasets WHERE id = 9001")
        assert result is not None
        assert result[0] == "abc123def456"

    def test_datasets_has_performance_columns(self, db: DatabaseManager):
        """Verify datasets table has performance tracking columns."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, total_api_calls, total_api_errors, generation_duration_sec, created_at)
               VALUES (9002, 'Perf Test', 'PT', 'T1', 'LEO', 'available', 42, 3, 125.5, CURRENT_TIMESTAMP)"""
        )
        result = _fetchone(db, "SELECT total_api_calls, total_api_errors, generation_duration_sec FROM datasets WHERE id = 9002")
        assert result is not None
        assert result[0] == 42
        assert result[1] == 3
        assert abs(float(result[2]) - 125.5) < 0.01

    def test_schema_migration_idempotent(self, db: DatabaseManager):
        """Run schema init twice - should not error."""
        db.initialize(force=False)
        result = _fetchone(db, "SELECT COUNT(*) FROM datasets")
        assert result is not None

    def test_backward_compatible_null_new_columns(self, db: DatabaseManager):
        """Existing-style INSERT (no new columns) still works - new columns default to NULL."""
        db.execute(
            """INSERT INTO observations (id, sat_no, ob_time, ra, declination)
               VALUES ('test-compat-1', 25544, CURRENT_TIMESTAMP, 100.0, 45.0)"""
        )
        result = _fetchone(
            db, "SELECT senlat, mag, solar_phase_angle, classification_marking FROM observations WHERE id = 'test-compat-1'"
        )
        assert result is not None
        assert result[0] is None
        assert result[1] is None
        assert result[2] is None
        assert result[3] is None


# ============================================================
# GROUP 2: Full Observation Storage Tests
# ============================================================


class TestFullObservationStorage:
    """Test storing and retrieving observations with all 46+ fields."""

    def _make_full_observation(self, obs_id: str = "full-obs-001") -> dict:
        """Create a dict with all observation fields populated."""
        return {
            "id": obs_id,
            "sat_no": 25544,
            "ob_time": datetime.now(),
            "ra": 123.456789,
            "declination": -45.123456,
            "range_km": 500.1234,
            "range_rate_km_s": 1.234567,
            "azimuth": 180.0,
            "elevation": 45.0,
            "sensor_name": "GEODSS",
            "data_mode": "REAL",
            "track_id": "track-001",
            "is_uct": False,
            "is_simulated": False,
            "source_id": 1,
            "observation_type": "EO",
            "senlat": 32.123456,
            "senlon": -110.987654,
            "senalt": 2.345,
            "senx": 1234.567,
            "seny": -2345.678,
            "senz": 3456.789,
            "senvelx": 0.001234,
            "senvely": -0.002345,
            "senvelz": 0.003456,
            "los_unc": 0.5,
            "exp_duration": 1.5,
            "zeroptd": 1.23456789,
            "net_obj_sig": 12345.6,
            "net_obj_sig_unc": 1.2,
            "mag": 12.3,
            "mag_unc": 0.2,
            "geolat": 35.0,
            "geolon": -120.0,
            "geoalt": 400.0,
            "georange": 800.0,
            "solar_phase_angle": 60.0,
            "solar_eq_phase_angle": 45.0,
            "solar_dec_angle": 30.0,
            "classification_marking": "U",
            "id_sensor": "SENSOR-001",
            "id_on_orbit": "ORBIT-001",
            "orig_object_id": "OBJ-001",
            "orig_sensor_id": "SEN-001",
            "shutter_delay": 0.5,
            "raw_file_uri": "s3://bucket/file.fits",
            "source_name": "EXO",
            "created_by": "test-system",
            "orig_network": "SSN",
            "observation_type_udl": "OPTICAL",
        }

    def test_insert_full_observation_all_fields(self, db: DatabaseManager):
        """Insert observation with all fields, verify round-trip."""
        obs = self._make_full_observation()
        repo = ObservationRepository(db)
        df = pd.DataFrame([obs])
        count = repo.bulk_insert(df)
        assert count == 1

        result = _fetchone(db, "SELECT id, senlat, mag, classification_marking FROM observations WHERE id = 'full-obs-001'")
        assert result is not None
        assert result[0] == "full-obs-001"

    def test_insert_observation_minimal_fields(self, db: DatabaseManager):
        """Insert observation with only required fields - new fields default to NULL."""
        repo = ObservationRepository(db)
        df = pd.DataFrame([{
            "id": "min-obs-001",
            "ob_time": datetime.now(),
            "ra": 100.0,
            "declination": 45.0,
        }])
        count = repo.bulk_insert(df)
        assert count == 1

        result = _fetchone(db, "SELECT senlat, mag, classification_marking FROM observations WHERE id = 'min-obs-001'")
        assert result[0] is None
        assert result[1] is None
        assert result[2] is None

    def test_bulk_insert_observations_full_fields(self, db: DatabaseManager):
        """Bulk insert multiple observations with all fields."""
        repo = ObservationRepository(db)
        obs_list = []
        for i in range(50):
            obs = self._make_full_observation(f"bulk-obs-{i:03d}")
            obs["ra"] = 100.0 + i * 0.1
            obs_list.append(obs)

        df = pd.DataFrame(obs_list)
        count = repo.bulk_insert(df)
        assert count == 50

        result = _fetchone(db, "SELECT COUNT(*) FROM observations WHERE id LIKE 'bulk-obs-%'")
        assert result[0] == 50

    def test_observation_sensor_velocity_fields(self, db: DatabaseManager):
        """Verify sensor velocity ECI fields store correctly."""
        repo = ObservationRepository(db)
        df = pd.DataFrame([{
            "id": "vel-obs-001",
            "ob_time": datetime.now(),
            "ra": 100.0,
            "declination": 45.0,
            "senvelx": 0.001234,
            "senvely": -0.002345,
            "senvelz": 0.003456,
        }])
        repo.bulk_insert(df)

        result = _fetchone(db, "SELECT senvelx, senvely, senvelz FROM observations WHERE id = 'vel-obs-001'")
        assert result is not None
        assert abs(float(result[0]) - 0.001234) < 1e-6
        assert abs(float(result[1]) - (-0.002345)) < 1e-6
        assert abs(float(result[2]) - 0.003456) < 1e-6


# ============================================================
# GROUP 3: Query Parameter Tracking Tests
# ============================================================


class TestQueryParameterTracking:
    """Test dataset_queries table for query reproducibility."""

    def test_insert_udl_eo_query(self, db: DatabaseManager):
        """Store a UDL eoobservation query record."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (100, 'Query Test', 'QT', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetQueryRepository(db)
        records = [{
            "dataset_id": 100,
            "service": "udl:eoobservation",
            "query_params": {
                "satNo": "25544,28654",
                "obTime": ">now-7 days",
                "uct": "false",
                "dataMode": "REAL",
                "maxResults": "10000",
            },
            "sat_no": None,
            "time_range_start": datetime(2025, 1, 1),
            "time_range_end": datetime(2025, 1, 8),
            "response_record_count": 245,
            "response_time_ms": 1523.4,
            "success": True,
            "executed_at": datetime.now(),
        }]
        count = repo.bulk_insert(records)
        assert count == 1

        df = repo.get_by_dataset(100)
        assert len(df) == 1
        assert df.iloc[0]["service"] == "udl:eoobservation"
        assert df.iloc[0]["response_record_count"] == 245

    def test_insert_statevector_query(self, db: DatabaseManager):
        """Store statevector query with epoch, sort params."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (101, 'SV Query Test', 'SVQ', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetQueryRepository(db)
        records = [{
            "dataset_id": 101,
            "service": "udl:statevector",
            "query_params": {
                "satNo": "25544",
                "epoch": ">2025-01-01",
                "uct": "false",
                "sort": "epoch,DESC",
            },
            "sat_no": 25544,
            "response_record_count": 12,
            "response_time_ms": 890.2,
            "success": True,
            "executed_at": datetime.now(),
        }]
        count = repo.bulk_insert(records)
        assert count == 1

    def test_insert_discoweb_query(self, db: DatabaseManager):
        """Store ESA DiscoWeb query."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (102, 'DW Query Test', 'DWQ', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetQueryRepository(db)
        records = [{
            "dataset_id": 102,
            "service": "esa:discoweb",
            "query_params": {
                "filter": "in(satno,(25544,28654))",
                "data": "objects",
                "version": 2,
            },
            "response_record_count": 2,
            "response_time_ms": 2100.0,
            "success": True,
            "executed_at": datetime.now(),
        }]
        count = repo.bulk_insert(records)
        assert count == 1

    def test_query_tracks_errors(self, db: DatabaseManager):
        """Store a failed query with error_message and retry_count."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (103, 'Error Query Test', 'EQT', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetQueryRepository(db)
        records = [{
            "dataset_id": 103,
            "service": "udl:eoobservation",
            "query_params": {"satNo": "99999"},
            "response_record_count": 0,
            "response_status_code": 503,
            "response_time_ms": 30000.0,
            "retry_count": 3,
            "error_message": "Service unavailable after 3 retries",
            "success": False,
            "executed_at": datetime.now(),
        }]
        count = repo.bulk_insert(records)
        assert count == 1

        df = repo.get_by_dataset(103)
        assert len(df) == 1
        assert df.iloc[0]["success"] == False
        assert df.iloc[0]["retry_count"] == 3
        assert "Service unavailable" in df.iloc[0]["error_message"]

    def test_get_all_queries_for_dataset(self, db: DatabaseManager):
        """Insert multiple queries for a dataset, retrieve all."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (104, 'Multi Query Test', 'MQT', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetQueryRepository(db)
        records = [
            {
                "dataset_id": 104,
                "service": "udl:eoobservation",
                "query_params": {"satNo": "25544"},
                "response_record_count": 100,
                "success": True,
                "executed_at": datetime.now(),
            },
            {
                "dataset_id": 104,
                "service": "udl:statevector",
                "query_params": {"satNo": "25544"},
                "response_record_count": 10,
                "success": True,
                "executed_at": datetime.now(),
            },
            {
                "dataset_id": 104,
                "service": "esa:discoweb",
                "query_params": {"filter": "in(satno,(25544))"},
                "response_record_count": 1,
                "success": True,
                "executed_at": datetime.now(),
            },
        ]
        count = repo.bulk_insert(records)
        assert count == 3

        df = repo.get_by_dataset(104)
        assert len(df) == 3

        total = repo.count_by_dataset(104)
        assert total == 3


# ============================================================
# GROUP 4: Config Hash + Dataset Reuse Tests
# ============================================================


class TestConfigHashReuse:
    """Test config hash computation and dataset reuse."""

    def test_find_by_config_hash_returns_match(self, db: DatabaseManager):
        """find_by_config_hash returns existing available dataset."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, config_hash, observation_count, created_at)
               VALUES (200, 'Reuse Target', 'RT', 'T1', 'LEO', 'available', 'deadbeef1234', 500, CURRENT_TIMESTAMP)"""
        )

        repo = DatasetRepository(db)
        result = repo.find_by_config_hash("deadbeef1234")
        assert result is not None
        assert int(result["id"]) == 200
        assert result["name"] == "Reuse Target"

    def test_find_by_config_hash_no_match(self, db: DatabaseManager):
        """find_by_config_hash returns None when no match."""
        repo = DatasetRepository(db)
        result = repo.find_by_config_hash("nonexistent_hash_value")
        assert result is None

    def test_find_by_config_hash_ignores_failed(self, db: DatabaseManager):
        """find_by_config_hash only returns available datasets, not failed."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, config_hash, created_at)
               VALUES (201, 'Failed DS', 'FD', 'T1', 'LEO', 'failed', 'failhash123', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetRepository(db)
        result = repo.find_by_config_hash("failhash123")
        assert result is None

    def test_find_by_config_hash_ignores_generating(self, db: DatabaseManager):
        """find_by_config_hash only returns available datasets, not generating."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, config_hash, created_at)
               VALUES (202, 'Generating DS', 'GD', 'T1', 'LEO', 'generating', 'genhash123', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetRepository(db)
        result = repo.find_by_config_hash("genhash123")
        assert result is None

    def test_create_dataset_reuse_existing(self, test_client: TestClient):
        """POST same config twice - second returns existing dataset with reused=True."""
        import backend_api.database as db_module

        test_db = db_module._db_manager
        config = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 5,
            "search_strategy": "hybrid",
            "sensors": ["optical"],
            "coverage": "standard",
            "include_hamr": False,
        }
        config_hash = compute_config_hash(config)

        test_db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, config_hash, observation_count, satellite_count, created_at)
               VALUES (300, 'Existing DS', 'EDS', 'T1', 'LEO', 'available', ?, 1000, 5, CURRENT_TIMESTAMP)""",
            (config_hash,),
        )

        response = test_client.post(
            "/api/v1/datasets/",
            json={
                "name": "New Dataset",
                "regime": "LEO",
                "tier": "T1",
                "object_count": 5,
                "timeframe": 7,
                "timeunit": "days",
                "sensors": ["optical"],
                "coverage": "standard",
                "include_hamr": False,
                "search_strategy": "hybrid",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reused"] == True
        assert data["id"] == "300"

    @patch("backend_api.routers.datasets.submit_dataset_generation")
    def test_create_dataset_no_reuse_different_params(
        self,
        mock_submit: MagicMock,
        test_client: TestClient,
    ):
        """POST with different config creates a new dataset (no reuse)."""
        mock_job = MagicMock()
        mock_job.id = "test-job-999"
        mock_submit.return_value = mock_job

        response = test_client.post(
            "/api/v1/datasets/",
            json={
                "name": "Unique Dataset",
                "regime": "GEO",
                "tier": "T2",
                "object_count": 20,
                "timeframe": 30,
                "timeunit": "days",
                "sensors": ["radar"],
                "coverage": "high",
                "include_hamr": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["reused"] == False
        assert data["status"] == "generating"

    def test_check_existing_endpoint_found(self, test_client: TestClient):
        """POST /datasets/check-existing returns exists=True for matching config."""
        import backend_api.database as db_module

        test_db = db_module._db_manager
        config = {
            "regime": "MEO",
            "tier": "T1",
            "satellites": [],
            "timeframe": 14,
            "timeunit": "days",
            "object_count": 10,
            "search_strategy": "hybrid",
            "sensors": ["optical"],
            "coverage": "standard",
            "include_hamr": False,
        }
        config_hash = compute_config_hash(config)

        test_db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, config_hash, observation_count, created_at)
               VALUES (301, 'Check Existing', 'CE', 'T1', 'MEO', 'available', ?, 200, CURRENT_TIMESTAMP)""",
            (config_hash,),
        )

        response = test_client.post(
            "/api/v1/datasets/check-existing",
            json={
                "name": "Check Me",
                "regime": "MEO",
                "tier": "T1",
                "object_count": 10,
                "timeframe": 14,
                "timeunit": "days",
                "sensors": ["optical"],
                "coverage": "standard",
                "include_hamr": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] == True
        assert data["dataset_id"] == 301

    def test_check_existing_endpoint_not_found(self, test_client: TestClient):
        """POST /datasets/check-existing returns exists=False when no match."""
        response = test_client.post(
            "/api/v1/datasets/check-existing",
            json={
                "name": "No Match",
                "regime": "HEO",
                "tier": "T3",
                "object_count": 50,
                "timeframe": 60,
                "timeunit": "days",
                "sensors": ["optical", "radar"],
                "coverage": "high",
                "include_hamr": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] == False


# ============================================================
# GROUP 5: Data Source Attribution Tests
# ============================================================


class TestDataSourceAttribution:
    """Test per-dataset data source attribution."""

    def test_upsert_source_attribution(self, db: DatabaseManager):
        """Upsert source attribution for a dataset."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (400, 'Source Test', 'ST', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetDataSourceRepository(db)
        repo.upsert(
            dataset_id=400,
            source_id=1,
            observation_count=500,
            state_vector_count=10,
            element_set_count=5,
        )

        df = repo.get_by_dataset(400)
        assert len(df) == 1
        assert df.iloc[0]["observation_count"] == 500
        assert df.iloc[0]["state_vector_count"] == 10

    def test_upsert_multiple_sources(self, db: DatabaseManager):
        """Upsert multiple sources for a dataset."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (401, 'Multi Source Test', 'MST', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetDataSourceRepository(db)
        repo.upsert(dataset_id=401, source_id=1, observation_count=500)
        repo.upsert(dataset_id=401, source_id=2, observation_count=100)
        repo.upsert(dataset_id=401, source_id=5, observation_count=0, state_vector_count=20)

        df = repo.get_by_dataset(401)
        assert len(df) == 3

    def test_upsert_updates_existing(self, db: DatabaseManager):
        """Upsert on same (dataset_id, source_id) updates counts."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (402, 'Upsert Update Test', 'UUT', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetDataSourceRepository(db)
        repo.upsert(dataset_id=402, source_id=1, observation_count=100)
        repo.upsert(dataset_id=402, source_id=1, observation_count=500)

        df = repo.get_by_dataset(402)
        assert len(df) == 1
        assert df.iloc[0]["observation_count"] == 500


# ============================================================
# GROUP 6: State Vector Physical Params Tests
# ============================================================


class TestStateVectorPhysicalParams:
    """Test expanded state vector fields."""

    def test_state_vector_stores_mass(self, db: DatabaseManager):
        """Insert state vector with mass_kg."""
        db.execute(
            """INSERT INTO satellites (sat_no, name, orbital_regime) VALUES (90001, 'SV Test Sat', 'LEO')"""
        )
        repo = StateVectorRepository(db)
        df = pd.DataFrame([{
            "sat_no": 90001,
            "epoch": datetime.now(),
            "x_pos": 6778.0,
            "y_pos": 0.0,
            "z_pos": 0.0,
            "x_vel": 0.0,
            "y_vel": 7.5,
            "z_vel": 0.0,
            "source": "TEST",
            "mass_kg": 420000.0,
        }])
        count = repo.bulk_insert(df)
        assert count == 1

        result = _fetchone(db, "SELECT mass_kg FROM state_vectors WHERE sat_no = 90001")
        assert result is not None
        assert abs(float(result[0]) - 420000.0) < 1.0

    def test_state_vector_stores_drag_coeff(self, db: DatabaseManager):
        """Insert state vector with drag and SRP coefficients."""
        db.execute(
            """INSERT INTO satellites (sat_no, name, orbital_regime) VALUES (90002, 'Drag Test Sat', 'LEO')"""
        )
        repo = StateVectorRepository(db)
        df = pd.DataFrame([{
            "sat_no": 90002,
            "epoch": datetime.now(),
            "x_pos": 6778.0,
            "y_pos": 0.0,
            "z_pos": 0.0,
            "x_vel": 0.0,
            "y_vel": 7.5,
            "z_vel": 0.0,
            "source": "TEST",
            "drag_coeff": 2.2,
            "srp_coeff": 1.5,
        }])
        count = repo.bulk_insert(df)
        assert count == 1

        result = _fetchone(db, "SELECT drag_coeff, srp_coeff FROM state_vectors WHERE sat_no = 90002")
        assert result is not None
        assert abs(float(result[0]) - 2.2) < 0.01
        assert abs(float(result[1]) - 1.5) < 0.01

    def test_state_vector_stores_reference_frame(self, db: DatabaseManager):
        """Insert state vector with reference_frame."""
        db.execute(
            """INSERT INTO satellites (sat_no, name, orbital_regime) VALUES (90003, 'Frame Test Sat', 'LEO')"""
        )
        repo = StateVectorRepository(db)
        df = pd.DataFrame([{
            "sat_no": 90003,
            "epoch": datetime.now(),
            "x_pos": 6778.0,
            "y_pos": 0.0,
            "z_pos": 0.0,
            "x_vel": 0.0,
            "y_vel": 7.5,
            "z_vel": 0.0,
            "source": "TEST",
            "reference_frame": "J2000",
        }])
        count = repo.bulk_insert(df)
        assert count == 1

        result = _fetchone(db, "SELECT reference_frame FROM state_vectors WHERE sat_no = 90003")
        assert result is not None
        assert result[0] == "J2000"

    def test_state_vector_classification_marking(self, db: DatabaseManager):
        """Insert state vector with classification_marking."""
        db.execute(
            """INSERT INTO satellites (sat_no, name, orbital_regime) VALUES (90004, 'Class Test Sat', 'LEO')"""
        )
        repo = StateVectorRepository(db)
        df = pd.DataFrame([{
            "sat_no": 90004,
            "epoch": datetime.now(),
            "x_pos": 6778.0,
            "y_pos": 0.0,
            "z_pos": 0.0,
            "x_vel": 0.0,
            "y_vel": 7.5,
            "z_vel": 0.0,
            "source": "TEST",
            "classification_marking": "UNCLASSIFIED",
        }])
        count = repo.bulk_insert(df)
        assert count == 1

        result = _fetchone(db, "SELECT classification_marking FROM state_vectors WHERE sat_no = 90004")
        assert result is not None
        assert result[0] == "UNCLASSIFIED"


# ============================================================
# GROUP 7: Enrichment Log Tests
# ============================================================


class TestEnrichmentLog:
    """Test per-dataset enrichment logging."""

    def test_log_enrichment_ucs(self, db: DatabaseManager):
        """Log UCS enrichment for a satellite in a dataset."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (500, 'Enrich Test', 'ET', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetEnrichmentLogRepository(db)
        repo.log_enrichment(
            dataset_id=500,
            sat_no=25544,
            enrichment_source="UCS",
            fields_updated={"mass_kg": 420000, "launch_date": "1998-11-20"},
            success=True,
        )

        df = repo.get_by_dataset(500)
        assert len(df) == 1
        assert df.iloc[0]["sat_no"] == 25544
        assert df.iloc[0]["enrichment_source"] == "UCS"
        assert df.iloc[0]["enrichment_success"] == True

    def test_log_enrichment_gcat(self, db: DatabaseManager):
        """Log GCAT enrichment with fields_updated JSON."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (501, 'GCAT Enrich Test', 'GET', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetEnrichmentLogRepository(db)
        repo.log_enrichment(
            dataset_id=501,
            sat_no=25544,
            enrichment_source="GCAT",
            fields_updated={"orbital_period_min": 92.8, "apogee_km": 418, "perigee_km": 410},
            success=True,
        )

        df = repo.get_by_dataset(501)
        assert len(df) == 1
        fields = json.loads(df.iloc[0]["fields_updated"]) if isinstance(df.iloc[0]["fields_updated"], str) else df.iloc[0]["fields_updated"]
        assert fields["orbital_period_min"] == 92.8

    def test_log_enrichment_failure(self, db: DatabaseManager):
        """Log failed enrichment with error_message."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (502, 'Fail Enrich Test', 'FET', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetEnrichmentLogRepository(db)
        repo.log_enrichment(
            dataset_id=502,
            sat_no=99999,
            enrichment_source="DISCOWEB",
            fields_updated=None,
            success=False,
            error_message="Object not found in DiscoWeb catalog",
        )

        df = repo.get_by_dataset(502)
        assert len(df) == 1
        assert df.iloc[0]["enrichment_success"] == False
        assert "not found" in df.iloc[0]["error_message"]

    def test_bulk_insert_enrichment(self, db: DatabaseManager):
        """Bulk insert enrichment records."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (503, 'Bulk Enrich Test', 'BET', 'T1', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        repo = DatasetEnrichmentLogRepository(db)
        records = [
            {
                "dataset_id": 503,
                "sat_no": 25544,
                "enrichment_source": "UCS",
                "fields_updated": {"mass_kg": 420000},
                "enrichment_success": True,
            },
            {
                "dataset_id": 503,
                "sat_no": 25544,
                "enrichment_source": "GCAT",
                "fields_updated": {"apogee_km": 418},
                "enrichment_success": True,
            },
            {
                "dataset_id": 503,
                "sat_no": 43013,
                "enrichment_source": "UCS",
                "enrichment_success": False,
                "error_message": "Not found",
            },
        ]
        count = repo.bulk_insert(records)
        assert count == 3

        df = repo.get_by_dataset(503)
        assert len(df) == 3


# ============================================================
# GROUP 8: Download + Provenance Endpoint Tests
# ============================================================


class TestDownloadAndProvenance:
    """Test download with full fields and provenance endpoint."""

    def test_download_returns_dataset_metadata(self, populated_test_client: TestClient):
        """GET /{id}/download includes dataset metadata."""
        response = populated_test_client.get("/api/v1/datasets/1/download")
        assert response.status_code == 200

        data = response.json()
        assert "dataset" in data
        ds = data["dataset"]
        assert "id" in ds

    def test_queries_endpoint(self, populated_test_client: TestClient):
        """GET /{id}/queries returns query records (populated fixture has 2)."""
        response = populated_test_client.get("/api/v1/datasets/1/queries")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # populated_db now seeds 2 query records for dataset 1
        assert len(data) >= 2

    def test_sources_endpoint(self, populated_test_client: TestClient):
        """GET /{id}/sources returns source attribution (populated fixture has 1)."""
        response = populated_test_client.get("/api/v1/datasets/1/sources")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_provenance_endpoint(self, populated_test_client: TestClient):
        """GET /{id}/provenance returns full provenance chain."""
        response = populated_test_client.get("/api/v1/datasets/1/provenance")
        assert response.status_code == 200

        data = response.json()
        assert data["dataset_id"] == 1
        assert data["dataset_name"] == "LEO Test Dataset"
        assert "queries" in data
        assert "sources" in data
        assert "enrichment_log" in data
        assert isinstance(data["queries"], list)
        assert isinstance(data["sources"], list)
        assert isinstance(data["enrichment_log"], list)

    def test_provenance_dataset_not_found(self, test_client: TestClient):
        """GET /99999/provenance returns 404."""
        response = test_client.get("/api/v1/datasets/99999/provenance")
        assert response.status_code == 404

    def test_queries_dataset_not_found(self, test_client: TestClient):
        """GET /99999/queries returns 404."""
        response = test_client.get("/api/v1/datasets/99999/queries")
        assert response.status_code == 404

    def test_sources_dataset_not_found(self, test_client: TestClient):
        """GET /99999/sources returns 404."""
        response = test_client.get("/api/v1/datasets/99999/sources")
        assert response.status_code == 404


# ============================================================
# GROUP 9: ILRS Validation Linking Tests
# ============================================================


class TestILRSValidationLinking:
    """Test dataset_validation_measurements junction table."""

    def test_link_validation_measurement_to_dataset(self, db: DatabaseManager):
        """Create validation measurement, link to dataset."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, created_at)
               VALUES (600, 'ILRS Test', 'IT', 'T1H', 'LEO', 'available', CURRENT_TIMESTAMP)"""
        )

        try:
            db.execute(
                """INSERT INTO validation_measurements (id, sat_no, measurement_time, range_km, source)
                   VALUES (1, 25544, CURRENT_TIMESTAMP, 500.123, 'ILRS')"""
            )
        except Exception:
            pytest.skip("validation_measurements table not available")

        db.execute(
            """INSERT INTO dataset_validation_measurements (dataset_id, validation_measurement_id, is_in_time_window, distance_to_nearest_obs_sec)
               VALUES (600, 1, TRUE, 120.5)"""
        )

        result = _fetchone(
            db, "SELECT dataset_id, validation_measurement_id FROM dataset_validation_measurements WHERE dataset_id = 600"
        )
        assert result is not None
        assert result[0] == 600


# ============================================================
# GROUP 10: Integration / End-to-End Tests
# ============================================================


class TestIntegration:
    """Integration tests combining multiple v2.0.0 features."""

    def test_full_observation_round_trip_via_repository(self, db: DatabaseManager):
        """Insert full observation via repository, read back all fields."""
        repo = ObservationRepository(db)
        obs = {
            "id": "e2e-obs-001",
            "sat_no": 25544,
            "ob_time": datetime(2025, 6, 15, 12, 0, 0),
            "ra": 123.456,
            "declination": -45.123,
            "sensor_name": "GEODSS",
            "data_mode": "REAL",
            "senlat": 32.0,
            "senlon": -110.0,
            "senalt": 2.3,
            "mag": 12.5,
            "solar_phase_angle": 60.0,
            "classification_marking": "U",
            "source_name": "EXO",
        }
        df = pd.DataFrame([obs])
        repo.bulk_insert(df)

        result = _fetchone(
            db,
            """SELECT id, sat_no, ra, declination, senlat, senlon, senalt,
                      mag, solar_phase_angle, classification_marking, source_name
               FROM observations WHERE id = 'e2e-obs-001'"""
        )
        assert result is not None
        assert result[0] == "e2e-obs-001"
        assert result[1] == 25544
        assert abs(float(result[4]) - 32.0) < 0.01  # senlat
        assert abs(float(result[7]) - 12.5) < 0.01  # mag
        assert result[9] == "U"  # classification_marking
        assert result[10] == "EXO"  # source_name

    def test_query_log_and_source_attribution_together(self, db: DatabaseManager):
        """Create dataset, add query log + source attribution, verify both."""
        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, config_hash, created_at)
               VALUES (700, 'E2E Dataset', 'E2E', 'T1', 'LEO', 'available', 'e2ehash', CURRENT_TIMESTAMP)"""
        )

        qr = DatasetQueryRepository(db)
        qr.bulk_insert([{
            "dataset_id": 700,
            "service": "udl:eoobservation",
            "query_params": {"satNo": "25544"},
            "response_record_count": 200,
            "success": True,
            "executed_at": datetime.now(),
        }])

        dsr = DatasetDataSourceRepository(db)
        dsr.upsert(dataset_id=700, source_id=1, observation_count=200)

        elr = DatasetEnrichmentLogRepository(db)
        elr.log_enrichment(
            dataset_id=700,
            sat_no=25544,
            enrichment_source="UCS",
            fields_updated={"mass_kg": 420000},
            success=True,
        )

        assert qr.count_by_dataset(700) == 1
        assert len(dsr.get_by_dataset(700)) == 1
        assert len(elr.get_by_dataset(700)) == 1

    def test_config_hash_computation_and_storage(self, db: DatabaseManager):
        """Compute config hash, store on dataset, retrieve and match."""
        config = {
            "regime": "LEO",
            "tier": "T1",
            "satellites": [25544, 28654],
            "timeframe": 7,
            "timeunit": "days",
            "object_count": 10,
            "search_strategy": "hybrid",
            "sensors": ["optical"],
            "coverage": "standard",
            "include_hamr": False,
        }
        config_hash = compute_config_hash(config)

        db.execute(
            """INSERT INTO datasets (id, name, code, tier, orbital_regime, status, config_hash, created_at)
               VALUES (701, 'Hash Test', 'HT', 'T1', 'LEO', 'available', ?, CURRENT_TIMESTAMP)""",
            (config_hash,),
        )

        repo = DatasetRepository(db)
        result = repo.find_by_config_hash(config_hash)
        assert result is not None
        assert int(result["id"]) == 701

        assert compute_config_hash(config) == config_hash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
