"""
Query logging middleware.
Logs slow API requests (>500ms) to the query_log table.
"""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class QueryLoggingMiddleware(BaseHTTPMiddleware):
    """Logs slow API requests to the query_log table."""

    SLOW_THRESHOLD_MS = 500  # Log requests slower than this

    async def dispatch(self, request: Request, call_next):
        from backend_api.config import DatabaseBackend, get_config

        config = get_config()

        if config.db_backend != DatabaseBackend.POSTGRES:
            return await call_next(request)

        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Log slow requests
        if duration_ms > self.SLOW_THRESHOLD_MS:
            try:
                from backend_api.services.audit_service import log_system_event

                log_system_event(
                    level="WARNING",
                    component="api",
                    message=f"Slow request: {request.method} {request.url.path} took {duration_ms:.0f}ms",
                    details={
                        "method": request.method,
                        "path": str(request.url.path),
                        "duration_ms": round(duration_ms, 3),
                        "status_code": response.status_code,
                    },
                )
            except Exception:
                pass

        return response
