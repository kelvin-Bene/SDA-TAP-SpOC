"""
Request logging middleware with correlation IDs.

Provides structured logging for all HTTP requests with timing,
request IDs, and contextual information.

IMPORTANT: This middleware must NOT re-raise exceptions. When an exception
escapes a BaseHTTPMiddleware, the outer CORSMiddleware never gets to inject
Access-Control-Allow-Origin headers into the error response, causing the
browser to report a CORS error instead of the real error (e.g. 401, 500).
We catch all exceptions and convert them to JSONResponse so the response
flows back through the middleware stack normally.
"""

import contextvars
import time
import traceback
import uuid

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for request-scoped correlation ID
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def get_request_id() -> str:
    """Get the current request's correlation ID."""
    return request_id_var.get()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs request start/end with timing and correlation IDs.

    Reads X-Request-ID header if present, otherwise generates a UUID.
    Stores the request ID in a context variable for use in downstream loggers.

    Catches all exceptions from downstream and converts them to JSON error
    responses so that the outer CORSMiddleware can still inject CORS headers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate or read request ID
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:12])
        request_id_var.set(req_id)

        # Skip logging for health checks to reduce noise
        if request.url.path in ("/health", "/health/ready"):
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response

        start_time = time.perf_counter()

        logger.info(
            "request_start",
            method=request.method,
            path=request.url.path,
            request_id=req_id,
            client=request.client.host if request.client else "unknown",
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            # CRITICAL: Do NOT re-raise. Convert to a JSON error response so it
            # flows back through CORSMiddleware which will add CORS headers.
            # Without this, exceptions that escape BaseHTTPMiddleware bypass
            # CORSMiddleware.send(), causing the browser to see missing
            # Access-Control-Allow-Origin and report a CORS error.
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "request_error",
                method=request.method,
                path=request.url.path,
                request_id=req_id,
                duration_ms=round(duration_ms, 2),
                error=str(exc),
            )
            logger.debug(f"Exception traceback:\n{traceback.format_exc()}")

            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
            response.headers["X-Request-ID"] = req_id
            return response

        duration_ms = (time.perf_counter() - start_time) * 1000

        log_func = logger.warning if response.status_code >= 400 else logger.info
        log_func(
            "request_end",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            request_id=req_id,
            duration_ms=round(duration_ms, 2),
        )

        # Warn on slow requests
        if duration_ms > 2000:
            logger.warning(
                "slow_request",
                method=request.method,
                path=request.url.path,
                request_id=req_id,
                duration_ms=round(duration_ms, 2),
            )

        response.headers["X-Request-ID"] = req_id
        return response
