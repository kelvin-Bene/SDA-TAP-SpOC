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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown tasks:
    - Initialize database connection
    - Initialize job manager
    - Clean up on shutdown
    """
    # Startup
    print("Starting UCT Benchmark API...")

    # Initialize database
    db = init_database()
    if db.backend == "duckdb":
        print(f"Database initialized (DuckDB): {db.db_path}")
    else:
        print(f"Database initialized (PostgreSQL): connection pool ready")

    # Initialize job manager
    job_manager = init_job_manager()
    print("Job manager initialized")

    yield

    # Shutdown
    print("Shutting down UCT Benchmark API...")

    # Shutdown worker threads
    shutdown_executor()

    # Close database
    close_database()
    print("Cleanup complete")


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


# Configure CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
    }
