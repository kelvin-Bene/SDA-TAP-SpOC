"""
UCT Benchmark API - FastAPI backend for the frontend demo UI.

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

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .database import close_database, init_database
from .jobs import init_job_manager
from .jobs.workers import shutdown_executor
from .routers import datasets, jobs, leaderboard, results, submissions

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
    description="Backend API for the UCT Benchmark demo UI",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log and return detailed validation errors."""
    body = await request.body()
    logger.error(f"Validation error for {request.method} {request.url}")
    logger.error(f"Request body: {body.decode()}")
    logger.error(f"Validation errors: {json.dumps(exc.errors(), indent=2, default=str)}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


# Configure CORS - use environment variable in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

# Include routers
app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["Datasets"])
app.include_router(submissions.router, prefix="/api/v1/submissions", tags=["Submissions"])
app.include_router(results.router, prefix="/api/v1/results", tags=["Results"])
app.include_router(leaderboard.router, prefix="/api/v1/leaderboard", tags=["Leaderboard"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])


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
