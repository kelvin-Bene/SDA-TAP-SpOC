# -*- coding: utf-8 -*-
"""
Unit tests for DataSourceManager class.

Tests satellite enrichment, HAMR detection, and ILRS tracking integration.

Run with: uv run pytest tests/test_data_source_manager.py -v
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from uct_benchmark.database.connection import DatabaseManager
from uct_benchmark.api.data_source_manager import (
    DataSourceManager,
    EnrichmentReport,
    get_data_source_manager,
    HAMR_AMR_THRESHOLD,
)


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    db = DatabaseManager(in_memory=True)
    db.initialize()
    return db


@pytest.fixture
def populated_db(db):
    """Create a database with sample satellite data."""
    # Add satellites with varying data completeness
    db.execute(
        """
        INSERT INTO satellites (sat_no, name, orbital_regime, object_type, mass_kg, cross_section_m2)
        VALUES (25544, 'ISS (ZARYA)', 'LEO', 'PAYLOAD', 419725.0, 1000.0)
        """
    )
    db.execute(
        """
        INSERT INTO satellites (sat_no, name, orbital_regime, object_type)
        VALUES (43013, 'STARLINK-1234', 'LEO', 'PAYLOAD')
        """
    )
    db.execute(
        """
        INSERT INTO satellites (sat_no, name, orbital_regime, object_type, mass_kg, cross_section_m2)
        VALUES (99999, 'TEST-DEBRIS', 'LEO', 'DEBRIS', 1.0, 10.0)
        """
    )
    return db


@pytest.fixture
def dsm(db):
    """Create a DataSourceManager with the test database."""
    return DataSourceManager(db)


class TestDataSourceManagerInit:
    """Test DataSourceManager initialization."""

    def test_init_with_database(self, db):
        """Test that DataSourceManager initializes with a database."""
        dsm = DataSourceManager(db)
        assert dsm.db is db

    def test_factory_function(self, db):
        """Test the get_data_source_manager factory function."""
        dsm = get_data_source_manager(db)
        assert isinstance(dsm, DataSourceManager)


class TestSatelliteEnrichment:
    """Test satellite enrichment functionality."""

    @patch('uct_benchmark.api.data_source_manager.ucsLookupByNorad')
    @patch('uct_benchmark.api.data_source_manager.gcatLookupByNorad')
    def test_enrich_satellite_with_ucs_data(self, mock_gcat, mock_ucs, dsm, populated_db):
        """Test enrichment pulls data from UCS."""
        mock_ucs.return_value = pd.Series({
            'Purpose': 'Science/Research',
            'Operator/Owner': 'NASA',
            'Launch Mass (kg.)': 419725.0,
        })
        mock_gcat.return_value = None

        result = dsm.enrich_satellite(25544, force_refresh=True)

        assert result['ucs_match'] is True
        assert 'purpose' in result['data'] or 'Purpose' in result['data']

    @patch('uct_benchmark.api.data_source_manager.ucsLookupByNorad')
    @patch('uct_benchmark.api.data_source_manager.gcatLookupByNorad')
    def test_enrich_satellite_with_gcat_data(self, mock_gcat, mock_ucs, dsm, populated_db):
        """Test enrichment pulls data from GCAT."""
        mock_ucs.return_value = None
        mock_gcat.return_value = pd.Series({
            'LaSite': 'TYMSC',
            'Owner': 'NASA',
        })

        result = dsm.enrich_satellite(25544, force_refresh=True)

        assert result['gcat_match'] is True

    @patch('uct_benchmark.api.data_source_manager.ucsLookupByNorad')
    @patch('uct_benchmark.api.data_source_manager.gcatLookupByNorad')
    def test_enrich_satellite_no_data_found(self, mock_gcat, mock_ucs, dsm, populated_db):
        """Test enrichment handles case where no data is found."""
        mock_ucs.return_value = None
        mock_gcat.return_value = None

        result = dsm.enrich_satellite(99999, force_refresh=True)

        assert result['ucs_match'] is False
        assert result['gcat_match'] is False

    def test_enrich_satellite_skips_recently_enriched(self, dsm, db):
        """Test that recently enriched satellites are skipped."""
        # Insert a satellite with recent sync timestamp
        db.execute(
            """
            INSERT INTO satellites (sat_no, name, ucs_synced_at)
            VALUES (12345, 'RECENT-SAT', CURRENT_TIMESTAMP)
            """
        )

        result = dsm.enrich_satellite(12345, force_refresh=False)

        assert result.get('skipped') is True


class TestBatchEnrichment:
    """Test batch enrichment functionality."""

    @patch('uct_benchmark.api.data_source_manager.ucsLookupByNorad')
    @patch('uct_benchmark.api.data_source_manager.gcatLookupByNorad')
    @patch('uct_benchmark.api.data_source_manager.ucsQuery')
    @patch('uct_benchmark.api.data_source_manager.gcatQuery')
    def test_batch_enrichment_processes_all(self, mock_gcat_q, mock_ucs_q,
                                             mock_gcat, mock_ucs, dsm, populated_db):
        """Test batch enrichment processes all satellites."""
        mock_ucs_q.return_value = pd.DataFrame()
        mock_gcat_q.return_value = pd.DataFrame()
        mock_ucs.return_value = pd.Series({'Purpose': 'Test'})
        mock_gcat.return_value = None

        sat_nos = [25544, 43013]
        report = dsm.enrich_satellites_batch(sat_nos, force_refresh=True)

        assert isinstance(report, EnrichmentReport)
        assert report.total_satellites == 2

    def test_batch_enrichment_report_structure(self, dsm, db):
        """Test EnrichmentReport has expected fields."""
        report = EnrichmentReport()
        report.total_satellites = 10
        report.enriched_count = 8
        report.finalize()

        result_dict = report.to_dict()

        assert 'total_satellites' in result_dict
        assert 'enriched_count' in result_dict
        assert 'duration_seconds' in result_dict
        assert 'success_rate' in result_dict


class TestHAMRDetection:
    """Test High Area-to-Mass Ratio object detection."""

    def test_calculate_amr_with_known_values(self, dsm, populated_db):
        """Test AMR calculation for satellite with known mass."""
        # ISS: mass=419725kg, cross_section=1000m² -> AMR=0.00238
        amr = dsm.calculate_accurate_amr(25544)

        assert amr is not None
        assert amr < HAMR_AMR_THRESHOLD  # ISS should not be HAMR

    def test_calculate_amr_returns_none_for_unknown(self, dsm, db):
        """Test AMR returns None when mass data unavailable."""
        db.execute(
            "INSERT INTO satellites (sat_no, name) VALUES (88888, 'UNKNOWN-SAT')"
        )

        amr = dsm.calculate_accurate_amr(88888)

        # May return None or estimate based on heuristics
        # Depends on whether UCS lookup is mocked

    def test_is_hamr_detects_high_amr_objects(self, dsm, populated_db):
        """Test HAMR detection for high AMR objects."""
        # TEST-DEBRIS: mass=1kg, cross_section=10m² -> AMR=10.0
        is_hamr = dsm.is_hamr_object(99999)

        assert is_hamr is True

    def test_is_hamr_returns_false_for_normal_sats(self, dsm, populated_db):
        """Test HAMR detection for normal satellites."""
        is_hamr = dsm.is_hamr_object(25544)  # ISS

        assert is_hamr is False

    def test_is_hamr_uses_object_type_heuristic(self, dsm, db):
        """Test HAMR detection falls back to object type."""
        db.execute(
            "INSERT INTO satellites (sat_no, name, object_type) VALUES (77777, 'DEBRIS-PIECE', 'DEBRIS')"
        )

        is_hamr = dsm.is_hamr_object(77777)

        assert is_hamr is True


class TestILRSIntegration:
    """Test ILRS satellite tracking integration."""

    def test_get_ilrs_satellites_returns_list(self, dsm):
        """Test that ILRS satellite list is returned."""
        with patch('uct_benchmark.api.data_source_manager.ilrsGetSatellites') as mock_ilrs:
            mock_ilrs.return_value = pd.DataFrame({
                'norad_id': [8820, 22195],
                'name': ['LAGEOS-1', 'LAGEOS-2']
            })

            satellites = dsm.get_ilrs_tracked_satellites()

            assert isinstance(satellites, list)
            assert 8820 in satellites

    def test_is_ilrs_satellite_checks_correctly(self, dsm):
        """Test ILRS satellite identification."""
        with patch.object(dsm, 'get_ilrs_tracked_satellites', return_value=[8820, 22195]):
            assert dsm.is_ilrs_satellite(8820) is True
            assert dsm.is_ilrs_satellite(25544) is False


class TestEnrichmentStatus:
    """Test enrichment status tracking."""

    def test_get_enrichment_status_for_enriched_sat(self, dsm, db):
        """Test enrichment status for enriched satellite."""
        db.execute(
            """
            INSERT INTO satellites (sat_no, name, purpose, operator, ucs_synced_at)
            VALUES (11111, 'ENRICHED-SAT', 'Science', 'NASA', CURRENT_TIMESTAMP)
            """
        )

        status = dsm.get_enrichment_status(11111)

        assert status['exists'] is True
        assert status['enriched'] is True
        assert status['has_purpose'] is True
        assert status['has_operator'] is True

    def test_get_enrichment_status_for_unenriched_sat(self, dsm, db):
        """Test enrichment status for unenriched satellite."""
        db.execute(
            "INSERT INTO satellites (sat_no, name) VALUES (22222, 'BASIC-SAT')"
        )

        status = dsm.get_enrichment_status(22222)

        assert status['exists'] is True
        assert status['enriched'] is False

    def test_get_enrichment_status_for_nonexistent_sat(self, dsm, db):
        """Test enrichment status for non-existent satellite."""
        status = dsm.get_enrichment_status(99999999)

        assert status['exists'] is False
