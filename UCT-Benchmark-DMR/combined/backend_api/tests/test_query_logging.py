"""Tests for the QueryLoggingMiddleware."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend_api.middleware.query_logging import QueryLoggingMiddleware


# ============================================================
# Helpers
# ============================================================


def _build_app(slow_route_delay: float = 0.0) -> FastAPI:
    """Build a minimal FastAPI app with the query logging middleware.

    Args:
        slow_route_delay: Seconds to sleep in the /slow endpoint.
    """
    app = FastAPI()
    app.add_middleware(QueryLoggingMiddleware)

    @app.get("/fast")
    async def fast_route():
        return {"ok": True}

    @app.get("/slow")
    async def slow_route():
        await asyncio.sleep(slow_route_delay)
        return {"ok": True}

    return app


# ============================================================
# Tests
# ============================================================


class TestQueryLoggingMiddleware:
    """Tests for the QueryLoggingMiddleware."""

    def test_fast_request_not_logged(self):
        """Requests faster than the threshold should NOT trigger logging."""
        app = _build_app(slow_route_delay=0.0)

        with patch("backend_api.config.get_config") as mock_cfg:
            from backend_api.config import DatabaseBackend

            cfg = MagicMock()
            cfg.db_backend = DatabaseBackend.POSTGRES
            mock_cfg.return_value = cfg

            with patch(
                "backend_api.services.audit_service.log_system_event"
            ) as mock_log:
                client = TestClient(app)
                resp = client.get("/fast")

                assert resp.status_code == 200
                mock_log.assert_not_called()

    def test_slow_request_is_logged(self):
        """Requests slower than the threshold SHOULD trigger logging."""
        app = _build_app(slow_route_delay=0.6)

        with patch("backend_api.config.get_config") as mock_cfg:
            from backend_api.config import DatabaseBackend

            cfg = MagicMock()
            cfg.db_backend = DatabaseBackend.POSTGRES
            mock_cfg.return_value = cfg

            with patch(
                "backend_api.services.audit_service.log_system_event"
            ) as mock_log:
                client = TestClient(app)
                resp = client.get("/slow")

                assert resp.status_code == 200
                mock_log.assert_called_once()

                call_kwargs = mock_log.call_args
                # Verify the log call has the expected shape
                assert call_kwargs.kwargs.get("level") == "WARNING" or (
                    call_kwargs.args and call_kwargs.args[0] == "WARNING"
                )

    def test_skips_when_not_postgres(self):
        """Middleware should be a no-op when backend is DuckDB."""
        app = _build_app(slow_route_delay=0.6)

        with patch("backend_api.config.get_config") as mock_cfg:
            from backend_api.config import DatabaseBackend

            cfg = MagicMock()
            cfg.db_backend = DatabaseBackend.DUCKDB
            mock_cfg.return_value = cfg

            with patch(
                "backend_api.services.audit_service.log_system_event"
            ) as mock_log:
                client = TestClient(app)
                resp = client.get("/slow")

                assert resp.status_code == 200
                mock_log.assert_not_called()

    def test_logging_error_does_not_break_request(self):
        """If log_system_event raises, the response should still succeed."""
        app = _build_app(slow_route_delay=0.6)

        with patch("backend_api.config.get_config") as mock_cfg:
            from backend_api.config import DatabaseBackend

            cfg = MagicMock()
            cfg.db_backend = DatabaseBackend.POSTGRES
            mock_cfg.return_value = cfg

            with patch(
                "backend_api.services.audit_service.log_system_event",
                side_effect=RuntimeError("DB down"),
            ):
                client = TestClient(app)
                resp = client.get("/slow")

                # The request itself should still succeed
                assert resp.status_code == 200
                assert resp.json() == {"ok": True}

    def test_log_message_contains_path_and_duration(self):
        """The logged message should contain the request path and duration."""
        app = _build_app(slow_route_delay=0.6)

        with patch("backend_api.config.get_config") as mock_cfg:
            from backend_api.config import DatabaseBackend

            cfg = MagicMock()
            cfg.db_backend = DatabaseBackend.POSTGRES
            mock_cfg.return_value = cfg

            with patch(
                "backend_api.services.audit_service.log_system_event"
            ) as mock_log:
                client = TestClient(app)
                client.get("/slow")

                assert mock_log.called
                kwargs = mock_log.call_args.kwargs
                assert "Slow request" in kwargs.get("message", "")
                assert "/slow" in kwargs.get("message", "")
                details = kwargs.get("details", {})
                assert "duration_ms" in details
                assert details["duration_ms"] >= 500

    def test_threshold_attribute(self):
        """The SLOW_THRESHOLD_MS class attribute should be 500."""
        assert QueryLoggingMiddleware.SLOW_THRESHOLD_MS == 500
