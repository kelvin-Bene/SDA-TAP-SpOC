"""Audit middleware for capturing API mutations and request metadata.

Only active when DB_BACKEND=postgres. Captures POST/PUT/PATCH/DELETE
requests into the api_call_log table for compliance and debugging.
"""

import time
from typing import Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class AuditMiddleware(BaseHTTPMiddleware):
    """Logs API calls to the database for auditing.

    Captures request method, path, status code, duration, body sizes,
    and user identity (from JWT) for mutation endpoints.
    """

    MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Read request body size
        body = await request.body()
        request_body_size = len(body)

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000

        # Only log mutation methods
        if request.method in self.MUTATION_METHODS:
            try:
                self._log_api_call(
                    request=request,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    request_body_size=request_body_size,
                )
            except Exception as exc:
                # Logging must never break the request
                logger.warning(f"Audit logging failed: {exc}")

        return response

    def _log_api_call(
        self,
        request: Request,
        status_code: int,
        duration_ms: float,
        request_body_size: int,
    ) -> None:
        """Persist an API call record to the database."""
        try:
            from backend_api.services.audit_service import log_api_call

            # Extract user info from JWT if available
            user_id = None
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                try:
                    from backend_api.config import get_config
                    from backend_api.auth.middleware import verify_jwt

                    config = get_config()
                    if config.supabase_jwt_secret:
                        payload = verify_jwt(auth_header[7:], config.supabase_jwt_secret)
                        if payload:
                            user_id = payload.get("sub")
                except Exception:
                    pass

            log_api_call(
                user_id=user_id,
                method=request.method,
                path=str(request.url.path),
                status_code=status_code,
                request_body_size=request_body_size,
                duration_ms=duration_ms,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        except Exception as exc:
            logger.debug(f"Could not log API call: {exc}")
