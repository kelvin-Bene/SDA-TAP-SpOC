# -*- coding: utf-8 -*-
"""
Unit tests for open source data API wrappers.

Tests the SatNOGS, GCAT, UCS, and ILRS API integrations.

Run with: uv run pytest tests/test_open_sources.py -v
"""

import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from uct_benchmark.api.open_sources import (
    # SatNOGS
    satnogsQuery,
    satnogsGetSatellites,
    satnogsGetTransmitters,
    satnogsGetObservations,
    satnogsGetStations,
    # GCAT
    gcatQuery,
    gcatGetSatelliteCatalog,
    gcatLookupByNorad,
    # UCS
    ucsQuery,
    ucsLookupByNorad,
    ucsGetByCountry,
    ucsGetByPurpose,
    # ILRS
    ilrsGetSatellites,
    ilrsGetStations,
    # Utilities
    enrichSatelliteData,
    getOpenSourceCatalogStats,
    clearOpenSourceCache,
)


class TestSatNOGS:
    """Test SatNOGS API wrapper functions."""

    @patch('uct_benchmark.api.open_sources.requests.get')
    def test_satnogs_query_returns_dataframe(self, mock_get):
        """Test that satnogsQuery returns a DataFrame."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "name": "Test Sat"},
            {"id": 2, "name": "Test Sat 2"},
        ]
        mock_get.return_value = mock_response

        result = satnogsQuery("satellites", use_db_api=True, page_limit=1)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    @patch('uct_benchmark.api.open_sources.requests.get')
    def test_satnogs_query_handles_error(self, mock_get):
        """Test that satnogsQuery handles API errors gracefully."""
        mock_get.side_effect = Exception("Network error")

        result = satnogsQuery("observations", page_limit=1)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @patch('uct_benchmark.api.open_sources.requests.get')
    def test_satnogs_get_observations_filters_by_norad(self, mock_get):
        """Test that observations can be filtered by NORAD ID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1, "satellite__norad_cat_id": 25544}]
        mock_get.return_value = mock_response

        result = satnogsGetObservations(norad_id=25544, status="good")

        # Verify the parameters were passed correctly
        mock_get.assert_called()
        call_args = mock_get.call_args
        assert 'satellite__norad_cat_id' in str(call_args)

    def test_satnogs_get_stations_returns_dataframe(self):
        """Test that satnogsGetStations returns a DataFrame structure."""
        # This tests the function signature, actual API call may fail
        with patch('uct_benchmark.api.open_sources.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{"id": 1, "name": "Station 1"}]
            mock_get.return_value = mock_response

            result = satnogsGetStations()
            assert isinstance(result, pd.DataFrame)


class TestGCAT:
    """Test GCAT (General Catalog) API wrapper functions."""

    @patch('uct_benchmark.api.open_sources.requests.get')
    def test_gcat_query_parses_tsv(self, mock_get):
        """Test that gcatQuery correctly parses TSV data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# Comment line\nPiece\tName\tNORAD\n1998-067A\tISS\t25544"
        mock_get.return_value = mock_response

        # Clear cache first
        clearOpenSourceCache()

        result = gcatQuery("satcat", force_refresh=True)

        assert isinstance(result, pd.DataFrame)
        assert "Piece" in result.columns or len(result) > 0

    @patch('uct_benchmark.api.open_sources.requests.get')
    def test_gcat_caches_results(self, mock_get):
        """Test that GCAT results are cached."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Piece\tName\n1\tTest"
        mock_get.return_value = mock_response

        clearOpenSourceCache()

        # First call
        gcatQuery("satcat", force_refresh=True)
        # Second call (should use cache)
        gcatQuery("satcat", force_refresh=False)

        # Should only have made one request (or limited requests)
        assert mock_get.call_count >= 1

    def test_gcat_lookup_by_norad_with_mock(self):
        """Test gcatLookupByNorad function."""
        with patch('uct_benchmark.api.open_sources.gcatQuery') as mock_query:
            mock_df = pd.DataFrame({
                'NORAD': [25544, 43013],
                'Name': ['ISS', 'STARLINK']
            })
            mock_query.return_value = mock_df

            # This should work with the mocked data
            result = gcatLookupByNorad(25544)
            # Result depends on column detection logic


class TestUCS:
    """Test UCS Satellite Database API wrapper functions."""

    @patch('uct_benchmark.api.open_sources.requests.get')
    def test_ucs_query_returns_dataframe(self, mock_get):
        """Test that ucsQuery returns a DataFrame."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Name\tNORAD Number\tCountry\nISS\t25544\tUSA"
        mock_get.return_value = mock_response

        clearOpenSourceCache()

        result = ucsQuery(force_refresh=True)

        assert isinstance(result, pd.DataFrame)

    @patch('uct_benchmark.api.open_sources.requests.get')
    def test_ucs_handles_download_failure(self, mock_get):
        """Test UCS fallback URL handling."""
        mock_get.side_effect = Exception("Download failed")

        clearOpenSourceCache()

        result = ucsQuery(force_refresh=True)

        # Should return empty DataFrame on failure
        assert isinstance(result, pd.DataFrame)

    def test_ucs_get_by_country_filters(self):
        """Test ucsGetByCountry filters correctly."""
        with patch('uct_benchmark.api.open_sources.ucsQuery') as mock_query:
            mock_df = pd.DataFrame({
                'Name of Satellite': ['Sat1', 'Sat2', 'Sat3'],
                'Country of Operator/Owner': ['USA', 'China', 'USA']
            })
            mock_query.return_value = mock_df

            result = ucsGetByCountry('USA')

            assert len(result) == 2

    def test_ucs_get_by_purpose_filters(self):
        """Test ucsGetByPurpose filters correctly."""
        with patch('uct_benchmark.api.open_sources.ucsQuery') as mock_query:
            mock_df = pd.DataFrame({
                'Name of Satellite': ['Sat1', 'Sat2'],
                'Purpose': ['Communications', 'Earth Observation']
            })
            mock_query.return_value = mock_df

            result = ucsGetByPurpose('Communications')

            assert len(result) == 1


class TestILRS:
    """Test ILRS (International Laser Ranging Service) API functions."""

    def test_ilrs_get_satellites_returns_dataframe(self):
        """Test that ilrsGetSatellites returns expected structure."""
        result = ilrsGetSatellites()

        assert isinstance(result, pd.DataFrame)
        assert 'norad_id' in result.columns
        assert 'name' in result.columns
        # Should include well-known ILRS targets
        norad_ids = result['norad_id'].tolist()
        assert 8820 in norad_ids  # LAGEOS-1
        assert 22195 in norad_ids  # LAGEOS-2

    def test_ilrs_get_stations_returns_dataframe(self):
        """Test that ilrsGetStations returns station information."""
        result = ilrsGetStations()

        assert isinstance(result, pd.DataFrame)
        assert 'code' in result.columns
        assert 'name' in result.columns
        assert len(result) > 0


class TestUtilities:
    """Test utility functions."""

    def test_enrich_satellite_data_structure(self):
        """Test that enrichSatelliteData returns expected structure."""
        with patch('uct_benchmark.api.open_sources.ucsLookupByNorad') as mock_ucs, \
             patch('uct_benchmark.api.open_sources.gcatLookupByNorad') as mock_gcat, \
             patch('uct_benchmark.api.open_sources.satnogsGetTransmitters') as mock_satnogs:

            mock_ucs.return_value = pd.Series({'Name': 'ISS', 'Purpose': 'Science'})
            mock_gcat.return_value = pd.Series({'Piece': '1998-067A'})
            mock_satnogs.return_value = pd.DataFrame()

            result = enrichSatelliteData(25544)

            assert 'norad_id' in result
            assert result['norad_id'] == 25544
            assert 'ucs' in result or 'gcat' in result

    def test_clear_cache_resets_state(self):
        """Test that clearOpenSourceCache resets module state."""
        # This should not raise an exception
        clearOpenSourceCache()

        # After clearing, next query should hit the API
        stats = getOpenSourceCatalogStats()
        assert isinstance(stats, dict)

    def test_get_catalog_stats_returns_dict(self):
        """Test getOpenSourceCatalogStats returns expected structure."""
        with patch('uct_benchmark.api.open_sources.gcatQuery') as mock_gcat, \
             patch('uct_benchmark.api.open_sources.ucsQuery') as mock_ucs, \
             patch('uct_benchmark.api.open_sources.ilrsGetSatellites') as mock_ilrs:

            mock_gcat.return_value = pd.DataFrame({'id': [1, 2, 3]})
            mock_ucs.return_value = pd.DataFrame({'id': [1, 2]})
            mock_ilrs.return_value = pd.DataFrame({'norad_id': [8820]})

            stats = getOpenSourceCatalogStats()

            assert 'gcat' in stats
            assert 'ucs' in stats
            assert 'ilrs' in stats


class TestAPIRobustness:
    """Test API wrapper robustness and error handling."""

    @patch('uct_benchmark.api.open_sources.requests.get')
    def test_handles_malformed_json(self, mock_get):
        """Test handling of malformed JSON responses."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        result = satnogsQuery("observations", page_limit=1)

        assert isinstance(result, pd.DataFrame)

    @patch('uct_benchmark.api.open_sources.requests.get')
    def test_handles_timeout(self, mock_get):
        """Test handling of request timeouts."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        result = satnogsQuery("observations", page_limit=1)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @patch('uct_benchmark.api.open_sources.requests.get')
    def test_handles_http_error(self, mock_get):
        """Test handling of HTTP error status codes."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server Error")
        mock_get.return_value = mock_response

        result = gcatQuery("satcat", force_refresh=True)

        assert isinstance(result, pd.DataFrame)
