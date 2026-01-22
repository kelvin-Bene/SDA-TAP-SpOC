"""
UCT Benchmark API - FastAPI backend for the frontend demo UI.

This module provides REST endpoints for:
- Dataset management (list, create, retrieve)
- Submission handling (upload, process)
- Result retrieval
- Leaderboard data
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import datasets, submissions, results, leaderboard

app = FastAPI(
    title="UCT Benchmark API",
    version="1.0.0",
    description="Backend API for the UCT Benchmark demo UI",
)

# Configure CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
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


@app.get("/")
async def root():
    """API root - health check."""
    return {"status": "ok", "message": "UCT Benchmark API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
