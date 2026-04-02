"""Tests for middleware modules (rate limiting, audit, logging)."""
import pytest
from unittest.mock import MagicMock
from starlette.requests import Request

from backend_api.middleware.rate_limit import _get_real_client_ip


class TestGetRealClientIp:
    """Test the rate limiter IP extraction function."""

    def _make_request(self, headers=None, client_host=None):
        """Create a mock request with optional headers and client."""
        request = MagicMock(spec=Request)
        request.headers = headers or {}
        if client_host:
            request.client = MagicMock()
            request.client.host = client_host
        else:
            request.client = None
        return request

    def test_extracts_last_ip_from_x_forwarded_for(self):
        """Should trust the rightmost (proxy-appended) IP."""
        request = self._make_request(
            headers={"X-Forwarded-For": "1.1.1.1, 10.0.0.1, 172.16.0.1"},
            client_host="127.0.0.1",
        )
        assert _get_real_client_ip(request) == "172.16.0.1"

    def test_single_ip_in_forwarded_for(self):
        """Single IP in X-Forwarded-For should be returned."""
        request = self._make_request(
            headers={"X-Forwarded-For": "203.0.113.50"},
            client_host="127.0.0.1",
        )
        assert _get_real_client_ip(request) == "203.0.113.50"

    def test_strips_whitespace_from_ip(self):
        """IPs should be stripped of whitespace."""
        request = self._make_request(
            headers={"X-Forwarded-For": "1.1.1.1,  10.0.0.1  "},
        )
        assert _get_real_client_ip(request) == "10.0.0.1"

    def test_falls_back_to_client_host(self):
        """Without X-Forwarded-For, use request.client.host."""
        request = self._make_request(client_host="192.168.1.100")
        assert _get_real_client_ip(request) == "192.168.1.100"

    def test_returns_unknown_when_no_client(self):
        """When no headers and no client, return 'unknown'."""
        request = self._make_request()
        assert _get_real_client_ip(request) == "unknown"

    def test_ignores_forwarded_for_when_empty(self):
        """Empty X-Forwarded-For should fall back to client host."""
        request = self._make_request(
            headers={"X-Forwarded-For": ""},
            client_host="10.10.10.10",
        )
        assert _get_real_client_ip(request) == "10.10.10.10"
