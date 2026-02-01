# -*- coding: utf-8 -*-
"""
Tests for the UDL Publisher module.

Tests schema mapping, validation, dry-run publishing, and export integration.
All tests are offline — no network calls are made.

Run with: uv run pytest tests/test_udl_publisher.py -v
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from uct_benchmark.api.udl_publisher import (
    DataMode,
    DryRunReport,
    PublishResult,
    TIER_DATA_MODE_MAP,
    UDLPublisher,
    UDLService,
    ValidationResult,
    map_element_set_to_udl,
    map_observation_to_udl,
    map_state_vector_to_udl,
    validate_payload,
    validate_udl_record,
    DEFAULT_SOURCE,
)


# =============================================================================
# Sample data helpers
# =============================================================================

def _sample_observation(**overrides):
    """Return a minimal internal observation dict."""
    obs = {
        "ob_time": "2025-01-01T12:00:00.000000Z",
        "ra": 100.5,
        "declination": 45.2,
        "sat_no": 25544,
        "sensor_name": "TEST_SENSOR",
    }
    obs.update(overrides)
    return obs


def _sample_state_vector(**overrides):
    """Return a minimal internal state vector dict."""
    sv = {
        "epoch": "2025-01-01T12:00:00.000000Z",
        "sat_no": 25544,
        "position_km": [6800.0, 100.0, 200.0],
        "velocity_km_s": [0.1, 7.5, 0.3],
    }
    sv.update(overrides)
    return sv


def _sample_element_set(**overrides):
    """Return a minimal internal element set (TLE) dict."""
    elset = {
        "epoch": "2025-01-01T12:00:00.000000Z",
        "sat_no": 25544,
        "line1": "1 25544U 98067A   25001.50000000  .00002000  00000-0  40000-4 0  9991",
        "line2": "2 25544  51.6400 200.0000 0007000  90.0000 270.0000 15.50000000100001",
    }
    elset.update(overrides)
    return elset


def _sample_dataset(**overrides):
    """Return a minimal dataset dict matching export_dataset_to_json format."""
    dataset = {
        "metadata": {
            "name": "test-dataset",
            "tier": "T2",
        },
        "observations": [
            _sample_observation(),
            _sample_observation(ra=101.0, declination=46.0, sat_no=43013),
        ],
        "references": [
            {
                "sat_no": 25544,
                "state_vector": {
                    "epoch": "2025-01-01T12:00:00.000000Z",
                    "position_km": [6800.0, 100.0, 200.0],
                    "velocity_km_s": [0.1, 7.5, 0.3],
                },
                "tle": {
                    "line1": "1 25544U 98067A   25001.50000000 ...",
                    "line2": "2 25544  51.6400 200.0000 ...",
                    "epoch": "2025-01-01T12:00:00.000000Z",
                },
            }
        ],
    }
    dataset.update(overrides)
    return dataset


# =============================================================================
# TestDataMode
# =============================================================================


class TestDataMode:
    """Tests for DataMode enum and tier mapping constants."""

    def test_tier_data_mode_mapping(self):
        """Verify T1/T2→TEST, T3→EXERCISE, T4/T5→SIMULATED."""
        assert TIER_DATA_MODE_MAP["T1"] == DataMode.TEST
        assert TIER_DATA_MODE_MAP["T2"] == DataMode.TEST
        assert TIER_DATA_MODE_MAP["T3"] == DataMode.EXERCISE
        assert TIER_DATA_MODE_MAP["T4"] == DataMode.SIMULATED
        assert TIER_DATA_MODE_MAP["T5"] == DataMode.SIMULATED

        # Sub-tiers follow their parent
        assert TIER_DATA_MODE_MAP["T1H"] == DataMode.TEST
        assert TIER_DATA_MODE_MAP["T3L"] == DataMode.EXERCISE
        assert TIER_DATA_MODE_MAP["T4L"] == DataMode.SIMULATED

    def test_data_mode_values(self):
        """Verify enum values match UDL spec strings."""
        assert DataMode.REAL.value == "REAL"
        assert DataMode.TEST.value == "TEST"
        assert DataMode.SIMULATED.value == "SIMULATED"
        assert DataMode.EXERCISE.value == "EXERCISE"


# =============================================================================
# TestSchemaMapping
# =============================================================================


class TestSchemaMapping:
    """Tests for schema mapping functions (no network calls)."""

    def test_map_observation_to_udl(self):
        """Map internal obs dict → UDL eoobservation format."""
        obs = _sample_observation()
        result = map_observation_to_udl(obs)

        assert result["classificationMarking"] == "U"
        assert result["source"] == DEFAULT_SOURCE
        assert result["dataMode"] == DataMode.TEST
        assert result["obTime"] == "2025-01-01T12:00:00.000000Z"
        assert result["ra"] == 100.5
        assert result["declination"] == 45.2
        assert result["satNo"] == 25544
        assert result["sensorName"] == "TEST_SENSOR"

    def test_map_observation_missing_optional_fields(self):
        """Sparse obs with only time+RA/Dec should not raise KeyError."""
        sparse_obs = {
            "ob_time": "2025-06-15T00:00:00Z",
            "ra": 200.0,
            "declination": -10.0,
        }
        result = map_observation_to_udl(sparse_obs)

        assert result["obTime"] == "2025-06-15T00:00:00Z"
        assert result["ra"] == 200.0
        assert result["declination"] == -10.0
        # Optional fields should be absent, not None
        assert "satNo" not in result
        assert "sensorName" not in result

    def test_map_state_vector_to_udl(self):
        """Map SV dict with position_km/velocity_km_s → UDL fields."""
        sv = _sample_state_vector()
        result = map_state_vector_to_udl(sv)

        assert result["classificationMarking"] == "U"
        assert result["source"] == DEFAULT_SOURCE
        assert result["dataMode"] == DataMode.TEST
        assert result["epoch"] == "2025-01-01T12:00:00.000000Z"
        assert result["satNo"] == 25544
        assert result["xPosition"] == 6800.0
        assert result["yPosition"] == 100.0
        assert result["zPosition"] == 200.0
        assert result["xVelocity"] == 0.1
        assert result["yVelocity"] == 7.5
        assert result["zVelocity"] == 0.3

    def test_map_element_set_to_udl(self):
        """Map TLE dict → UDL elset format with line1/line2."""
        elset = _sample_element_set()
        result = map_element_set_to_udl(elset)

        assert result["classificationMarking"] == "U"
        assert result["source"] == DEFAULT_SOURCE
        assert result["dataMode"] == DataMode.TEST
        assert result["epoch"] == "2025-01-01T12:00:00.000000Z"
        assert result["satNo"] == 25544
        assert "line1" in result
        assert "line2" in result
        assert result["line1"].startswith("1 25544")

    def test_classification_marking_propagates(self):
        """Verify classificationMarking passes through to mapped record."""
        obs = _sample_observation()
        result = map_observation_to_udl(obs, classification="S")
        assert result["classificationMarking"] == "S"

    def test_custom_source_propagates(self):
        """Verify custom source name is applied."""
        obs = _sample_observation()
        result = map_observation_to_udl(obs, source="MY-CUSTOM-SOURCE")
        assert result["source"] == "MY-CUSTOM-SOURCE"


# =============================================================================
# TestValidation
# =============================================================================


class TestValidation:
    """Tests for validate_payload and validate_udl_record."""

    def test_validate_valid_observation(self):
        """Valid record passes validation."""
        record = {
            "classificationMarking": "U",
            "source": DEFAULT_SOURCE,
            "dataMode": "TEST",
            "obTime": "2025-01-01T12:00:00Z",
        }
        errors = validate_udl_record(record, UDLService.EOOBSERVATION)
        assert errors == []

    def test_validate_missing_required_fields(self):
        """Missing classificationMarking/source/dataMode → errors."""
        record = {"obTime": "2025-01-01T12:00:00Z"}
        errors = validate_udl_record(record, UDLService.EOOBSERVATION)
        assert len(errors) == 3
        field_names = " ".join(errors)
        assert "classificationMarking" in field_names
        assert "source" in field_names
        assert "dataMode" in field_names

    def test_validate_invalid_data_mode(self):
        """Invalid enum value → error."""
        record = {
            "classificationMarking": "U",
            "source": DEFAULT_SOURCE,
            "dataMode": "INVALID_MODE",
            "obTime": "2025-01-01T12:00:00Z",
        }
        errors = validate_udl_record(record, UDLService.EOOBSERVATION)
        assert any("Invalid dataMode" in e for e in errors)

    def test_validate_eo_missing_ob_time(self):
        """eoobservation without obTime → error."""
        record = {
            "classificationMarking": "U",
            "source": DEFAULT_SOURCE,
            "dataMode": "TEST",
        }
        errors = validate_udl_record(record, UDLService.EOOBSERVATION)
        assert any("obTime" in e for e in errors)

    def test_validate_sv_missing_epoch(self):
        """statevector without epoch → error."""
        record = {
            "classificationMarking": "U",
            "source": DEFAULT_SOURCE,
            "dataMode": "TEST",
        }
        errors = validate_udl_record(record, UDLService.STATEVECTOR)
        assert any("epoch" in e for e in errors)

    def test_validate_batch_mixed_sources_warning(self):
        """Multiple sources in batch → warning (not error)."""
        records = [
            {
                "classificationMarking": "U",
                "source": "SOURCE-A",
                "dataMode": "TEST",
                "obTime": "2025-01-01T12:00:00Z",
            },
            {
                "classificationMarking": "U",
                "source": "SOURCE-B",
                "dataMode": "TEST",
                "obTime": "2025-01-01T13:00:00Z",
            },
        ]
        result = validate_payload(records, UDLService.EOOBSERVATION)
        assert result.valid is True
        assert len(result.warnings) >= 1
        assert any("source" in w.lower() for w in result.warnings)

    def test_validate_empty_records(self):
        """Empty list → invalid."""
        result = validate_payload([], UDLService.EOOBSERVATION)
        assert result.valid is False
        assert result.record_count == 0
        assert len(result.errors) >= 1


# =============================================================================
# TestUDLPublisher
# =============================================================================


class TestUDLPublisher:
    """Tests for UDLPublisher class (dry-run, no network)."""

    def test_publisher_default_dry_run(self):
        """Default init has dry_run=True."""
        publisher = UDLPublisher()
        assert publisher.is_dry_run is True

    def test_publisher_requires_token_for_live(self):
        """dry_run=False without token → ValueError."""
        with pytest.raises(ValueError, match="token"):
            UDLPublisher(dry_run=False)

    def test_dry_run_with_sample_dataset(self):
        """dry_run() on a sample dataset returns DryRunReport with expected fields."""
        publisher = UDLPublisher()
        dataset = _sample_dataset()
        report = publisher.dry_run(dataset)

        assert isinstance(report, DryRunReport)
        assert report.dataset_name == "test-dataset"
        assert report.tier == "T2"
        assert report.data_mode == "TEST"
        assert report.source == DEFAULT_SOURCE
        assert report.observation_validation is not None
        assert report.observation_validation.valid is True
        assert report.observation_validation.record_count == 2
        assert report.state_vector_validation is not None
        assert report.element_set_validation is not None
        assert "eoobservation" in report.sample_payloads
        assert len(report.summary) > 0

    def test_publish_dataset_dry_run(self):
        """publish_dataset() in dry_run returns results per service."""
        publisher = UDLPublisher()
        dataset = _sample_dataset()
        results = publisher.publish_dataset(dataset)

        assert isinstance(results, dict)
        assert "observations" in results
        assert results["observations"].success is True
        assert results["observations"].dry_run is True
        assert results["observations"].records_submitted == 2

        # Dataset has references with state_vector and tle
        assert "state_vectors" in results
        assert results["state_vectors"].success is True
        assert "element_sets" in results
        assert results["element_sets"].success is True

    def test_publish_observations_dry_run(self):
        """publish_observations() validates and returns success."""
        publisher = UDLPublisher()
        observations = [_sample_observation(), _sample_observation(ra=102.0)]
        result = publisher.publish_observations(observations)

        assert isinstance(result, PublishResult)
        assert result.success is True
        assert result.dry_run is True
        assert result.records_submitted == 2
        assert result.records_accepted == 2
        assert result.service == UDLService.EOOBSERVATION

    def test_publish_state_vectors_dry_run(self):
        """publish_state_vectors() validates and returns success."""
        publisher = UDLPublisher()
        svs = [_sample_state_vector()]
        result = publisher.publish_state_vectors(svs)

        assert result.success is True
        assert result.dry_run is True
        assert result.records_submitted == 1
        assert result.service == UDLService.STATEVECTOR

    def test_publish_element_sets_dry_run(self):
        """publish_element_sets() validates and returns success."""
        publisher = UDLPublisher()
        elsets = [_sample_element_set()]
        result = publisher.publish_element_sets(elsets)

        assert result.success is True
        assert result.dry_run is True
        assert result.records_submitted == 1
        assert result.service == UDLService.ELSET

    def test_publish_dataset_from_file(self):
        """Load dataset from JSON file path in temp dir."""
        publisher = UDLPublisher()
        dataset = _sample_dataset()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dataset.json"
            with open(file_path, "w") as f:
                json.dump(dataset, f)

            results = publisher.publish_dataset(str(file_path))

        assert isinstance(results, dict)
        assert "observations" in results
        assert results["observations"].success is True

    def test_publish_dataset_tier_detection(self):
        """Tier from metadata maps to correct dataMode."""
        publisher = UDLPublisher()

        # T4 tier → SIMULATED
        dataset_t4 = _sample_dataset(metadata={"name": "synth", "tier": "T4"})
        report = publisher.dry_run(dataset_t4)
        assert report.data_mode == "SIMULATED"

        # T3 tier → EXERCISE
        dataset_t3 = _sample_dataset(metadata={"name": "blend", "tier": "T3"})
        report = publisher.dry_run(dataset_t3)
        assert report.data_mode == "EXERCISE"

    def test_publish_history_tracking(self):
        """Multiple publishes tracked in publish_history."""
        publisher = UDLPublisher()
        publisher.publish_observations([_sample_observation()])
        publisher.publish_state_vectors([_sample_state_vector()])

        history = publisher.publish_history
        assert len(history) == 2
        assert history[0].service == UDLService.EOOBSERVATION
        assert history[1].service == UDLService.STATEVECTOR

    def test_get_publish_summary(self):
        """Summary stats after operations."""
        publisher = UDLPublisher()
        publisher.publish_observations(
            [_sample_observation(), _sample_observation(ra=99.0)]
        )
        publisher.publish_element_sets([_sample_element_set()])

        summary = publisher.get_publish_summary()
        assert summary["total_operations"] == 2
        assert summary["total_submitted"] == 3  # 2 obs + 1 elset
        assert summary["total_accepted"] == 3
        assert summary["dry_run_count"] == 2
        assert summary["live_count"] == 0
        assert summary["total_errors"] == 0
        assert len(summary["operations"]) == 2


# =============================================================================
# TestExportUDLIntegration
# =============================================================================


class TestExportUDLIntegration:
    """Tests for export.py publish_to_udl flag."""

    def test_export_with_publish_dry_run(self):
        """export_dataset_to_json with publish_to_udl=True calls UDLPublisher."""
        with patch(
            "uct_benchmark.api.udl_publisher.UDLPublisher"
        ) as MockPublisher:
            mock_instance = MagicMock()
            MockPublisher.return_value = mock_instance

            # We need a fake db that returns enough data for export
            mock_db = MagicMock()
            mock_db.datasets.get_dataset.return_value = {
                "name": "test-ds",
                "code": "T2-LEO",
                "tier": "T2",
                "orbital_regime": "LEO",
                "time_window_start": None,
                "time_window_end": None,
                "satellite_count": 0,
                "created_at": None,
                "generation_params": {},
            }

            import pandas as pd

            mock_db.datasets.get_dataset_observations.return_value = (
                pd.DataFrame(
                    {
                        "id": ["obs-1"],
                        "ob_time": ["2025-01-01T12:00:00Z"],
                        "ra": [100.0],
                        "declination": [45.0],
                        "assigned_track_id": [None],
                        "assigned_object_id": [None],
                        "sat_no": [25544],
                        "sensor_name": [None],
                        "range_km": [None],
                        "range_rate_km_s": [None],
                        "azimuth": [None],
                        "elevation": [None],
                    }
                )
            )
            mock_db.datasets.get_dataset_references.return_value = (
                pd.DataFrame()
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "out.json"

                from uct_benchmark.database.export import (
                    export_dataset_to_json,
                )

                export_dataset_to_json(
                    mock_db,
                    dataset_id=1,
                    output_path=output_path,
                    publish_to_udl=True,
                    udl_dry_run=True,
                )

            MockPublisher.assert_called_once()
            mock_instance.publish_dataset.assert_called_once()

    def test_export_default_no_publish(self):
        """Default export does NOT call UDLPublisher."""
        with patch(
            "uct_benchmark.api.udl_publisher.UDLPublisher"
        ) as MockPublisher:
            mock_db = MagicMock()
            mock_db.datasets.get_dataset.return_value = {
                "name": "test-ds",
                "code": "T2-LEO",
                "tier": "T2",
                "orbital_regime": "LEO",
                "time_window_start": None,
                "time_window_end": None,
                "satellite_count": 0,
                "created_at": None,
                "generation_params": {},
            }

            import pandas as pd

            mock_db.datasets.get_dataset_observations.return_value = (
                pd.DataFrame(
                    {
                        "id": ["obs-1"],
                        "ob_time": ["2025-01-01T12:00:00Z"],
                        "ra": [100.0],
                        "declination": [45.0],
                        "assigned_track_id": [None],
                        "assigned_object_id": [None],
                        "sat_no": [25544],
                        "sensor_name": [None],
                        "range_km": [None],
                        "range_rate_km_s": [None],
                        "azimuth": [None],
                        "elevation": [None],
                    }
                )
            )
            mock_db.datasets.get_dataset_references.return_value = (
                pd.DataFrame()
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "out.json"

                from uct_benchmark.database.export import (
                    export_dataset_to_json,
                )

                export_dataset_to_json(
                    mock_db,
                    dataset_id=1,
                    output_path=output_path,
                    # publish_to_udl defaults to False
                )

            MockPublisher.assert_not_called()
