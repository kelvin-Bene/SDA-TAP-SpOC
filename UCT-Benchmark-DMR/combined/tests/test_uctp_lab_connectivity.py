"""
Tests for UCTP Lab connectivity module.

Run with: uv run pytest tests/test_uctp_lab_connectivity.py -v
"""

import pytest

from uct_benchmark.uctp_lab.connectors import (
    ALL_CONNECTORS,
    get_connector,
    test_all_connections,
)
from uct_benchmark.uctp_lab.connectors.base import AbstractConnector, ConnectionResult


# ---------------------------------------------------------------------------
# Base classes
# ---------------------------------------------------------------------------


class TestConnectionResult:
    def test_to_dict(self):
        r = ConnectionResult(
            service_name="test",
            status="connected",
            response_time_ms=42.5,
            last_checked="2025-06-01T12:00:00",
        )
        d = r.to_dict()
        assert d["service_name"] == "test"
        assert d["status"] == "connected"
        assert d["response_time_ms"] == 42.5

    def test_default_metadata(self):
        r = ConnectionResult(service_name="x", status="failed")
        assert r.metadata == {}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestConnectorRegistry:
    def test_all_connectors_populated(self):
        assert len(ALL_CONNECTORS) == 6

    def test_unique_service_names(self):
        names = [c.service_name for c in ALL_CONNECTORS]
        assert len(names) == len(set(names))

    def test_expected_services(self):
        names = {c.service_name for c in ALL_CONNECTORS}
        expected = {"orekit", "orbdetpy", "spacetrack", "satnogs", "celestrak", "udl"}
        assert names == expected

    def test_get_connector_known(self):
        c = get_connector("orekit")
        assert isinstance(c, AbstractConnector)
        assert c.service_name == "orekit"

    def test_get_connector_unknown_raises(self):
        with pytest.raises(KeyError):
            get_connector("nonexistent")

    def test_all_inherit_abstract(self):
        for c in ALL_CONNECTORS:
            assert isinstance(c, AbstractConnector)
            assert hasattr(c, "test_connection")
            assert hasattr(c, "service_name")


# ---------------------------------------------------------------------------
# Individual connector tests (local libs only – no network)
# ---------------------------------------------------------------------------


class TestLocalConnectors:
    def test_orekit_returns_result(self):
        c = get_connector("orekit")
        result = c.test_connection()
        assert isinstance(result, ConnectionResult)
        assert result.service_name == "orekit"
        assert result.status in ("connected", "failed", "not_installed")

    def test_orbdetpy_returns_result(self):
        c = get_connector("orbdetpy")
        result = c.test_connection()
        assert isinstance(result, ConnectionResult)
        assert result.service_name == "orbdetpy"
        assert result.status in ("connected", "failed", "not_installed")


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


class TestTestAllConnections:
    def test_returns_list(self):
        results = test_all_connections()
        assert isinstance(results, list)
        assert len(results) == 6

    def test_all_have_service_name(self):
        results = test_all_connections()
        for r in results:
            assert r.service_name
            assert r.status in (
                "connected",
                "failed",
                "timeout",
                "unauthorized",
                "not_installed",
            )
