"""
UCT Benchmark API - FastAPI backend.

This module provides REST endpoints for:
- Dataset management (list, create, retrieve)
- Submission handling (upload, process)
- Result retrieval
- Leaderboard data
- Job status tracking

Note: Auto-links observations when retrieving dataset observations.
"""

import json
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .database import close_database, init_database
from .jobs import init_job_manager
from .jobs.workers import shutdown_executor
from .middleware.auth import get_current_user
from .middleware.logging import RequestLoggingMiddleware
from .middleware.rate_limit import limiter
from .routers import auth as auth_router
from .routers import datasets, feedback, jobs, leaderboard, results, submissions

# Module-level flag to skip lifespan initialization during testing
# Set to True when using create_test_app() to prevent double database initialization
_skip_lifespan_init = False


def get_cors_origins() -> list[str]:
    """
    Get CORS origins from environment or use defaults for development.

    Environment Variables:
        CORS_ORIGINS: Comma-separated list of allowed origins (e.g., "https://example.com,https://app.example.com")

    Returns:
        List of allowed origin URLs
    """
    env_origins = os.getenv("CORS_ORIGINS")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]

    # Default development origins
    return [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown tasks:
    - Initialize database connection
    - Initialize job manager
    - Clean up on shutdown

    Note: When _skip_lifespan_init is True (set by create_test_app),
    database initialization is skipped to allow test fixtures to control the database.
    """
    global _skip_lifespan_init

    if _skip_lifespan_init:
        # Skip initialization - test fixtures handle database setup
        logger.info("Skipping lifespan init (test mode)")
        yield
        logger.info("Skipping lifespan cleanup (test mode)")
        return

    # Startup
    logger.info("Starting UCT Benchmark API...")

    # Initialize database
    db = init_database()
    if db.backend == "duckdb":
        logger.info(f"Database initialized (DuckDB): {db.db_path}")
    else:
        logger.info("Database initialized (PostgreSQL): connection pool ready")
        # Verify connection works and log diagnostics
        try:
            result = db.execute("SELECT 1").fetchone()
            logger.info(f"PostgreSQL connection verified: SELECT 1 = {result}")
            tables = db.adapter.get_tables()
            logger.info(f"Database tables found: {tables}")
        except Exception as e:
            logger.error(f"PostgreSQL connection test FAILED: {e}")

    # Verify critical modules are importable
    try:
        import uct_benchmark.data.dataManipulation  # noqa: F401
        logger.info("Module uct_benchmark.data loaded successfully")
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import uct_benchmark.data: {e}")

    # Initialize job manager with DB persistence for crash recovery
    job_manager = init_job_manager(db=db)
    logger.info("Job manager initialized (with DB persistence)")

    yield

    # Shutdown
    logger.info("Shutting down UCT Benchmark API...")

    # Shutdown worker threads
    shutdown_executor()

    # Close database
    close_database()
    logger.info("Cleanup complete")


app = FastAPI(
    title="UCT Benchmark API",
    version="1.0.0",
    description="Backend API for the UCT Benchmark platform",
    lifespan=lifespan,
)

# Rate limiting (slowapi) — attach limiter to app state and register error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses (S6)."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # HSTS only in production (when CORS_ORIGINS is set to non-localhost)
        if os.getenv("CORS_ORIGINS"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log details server-side but return sanitized error to client (S7)."""
    body = await request.body()
    logger.error(f"Validation error for {request.method} {request.url}")
    logger.error(f"Request body: {body.decode()}")
    logger.error(f"Validation errors: {json.dumps(exc.errors(), indent=2, default=str)}")

    # Sanitize: only return field names and error types, not raw input values
    sanitized = []
    for err in exc.errors():
        sanitized.append({
            "loc": err.get("loc"),
            "msg": err.get("msg"),
            "type": err.get("type"),
        })
    return JSONResponse(
        status_code=422,
        content={"detail": sanitized},
    )


# Security headers middleware (S6) — added first so it wraps all responses
app.add_middleware(SecurityHeadersMiddleware)

# Request logging with correlation IDs
app.add_middleware(RequestLoggingMiddleware)

# Configure CORS - use environment variable in production (S11)
cors_origins = get_cors_origins()
if not os.getenv("CORS_ORIGINS"):
    logger.warning(
        "CORS_ORIGINS not set — using localhost defaults. "
        "Set CORS_ORIGINS env var for production."
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

# Include routers with JWT auth dependency (S1)
# All API routes require valid Supabase JWT — / and /health remain public
_auth_deps = [Depends(get_current_user)]
app.include_router(
    datasets.router, prefix="/api/v1/datasets", tags=["Datasets"],
    dependencies=_auth_deps,
)
app.include_router(
    submissions.router, prefix="/api/v1/submissions", tags=["Submissions"],
    dependencies=_auth_deps,
)
app.include_router(
    results.router, prefix="/api/v1/results", tags=["Results"],
    dependencies=_auth_deps,
)
app.include_router(
    leaderboard.router, prefix="/api/v1/leaderboard", tags=["Leaderboard"],
    dependencies=_auth_deps,
)
app.include_router(
    jobs.router, prefix="/api/v1/jobs", tags=["Jobs"],
    dependencies=_auth_deps,
)

# Auth router (verify, profile management) — uses its own auth dependency
# from backend_api.auth (ES256 JWKS in production)
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Auth"])

# Feedback router — POST is public (optional auth), GET/PATCH are admin-only
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])


@app.get("/")
async def root():
    """API root - health check."""
    return {"status": "ok", "message": "UCT Benchmark API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from .database import get_db

    try:
        db = get_db()
        # Quick database check
        db.execute("SELECT 1").fetchone()
        db_status = "connected"
    except Exception as e:
        # Log the actual error for debugging, but don't expose details to clients
        logger.warning(f"Health check database error: {e}")
        db_status = "error"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
    }


def create_test_app() -> FastAPI:
    """
    Create a FastAPI app instance configured for testing.

    This function sets a module-level flag that causes the lifespan
    context manager to skip database initialization, allowing test
    fixtures to inject their own database via dependency overrides.

    Usage in tests:
        from backend_api.main import create_test_app
        from backend_api.database import get_db

        app = create_test_app()

        def override_get_db():
            return test_db

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as client:
            # Run tests
            pass

    Returns:
        The global FastAPI app instance with test mode enabled
    """
    global _skip_lifespan_init
    _skip_lifespan_init = True
    return app


def reset_test_mode():
    """
    Reset test mode flag after tests complete.

    Call this in test teardown to restore normal operation.
    """
    global _skip_lifespan_init
    _skip_lifespan_init = False
