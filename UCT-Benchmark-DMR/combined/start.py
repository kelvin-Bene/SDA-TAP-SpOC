"""Railway-compatible startup script."""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    # Default to 1 worker: JobManager stores job state in-process memory,
    # so multiple workers cause job-status 404s.  Do NOT raise this default
    # until JobManager is migrated to a shared backend (Redis / Celery / ARQ).
    workers = int(os.environ.get("WEB_WORKERS", "1"))
    if workers > 1:
        import warnings
        warnings.warn(
            f"WEB_WORKERS={workers}: JobManager uses in-memory state that is NOT shared "
            "across workers. Job status polling may return 404. Set WEB_WORKERS=1 or "
            "migrate to a shared task queue (Celery/ARQ).",
            stacklevel=1,
        )
    uvicorn.run(
        "backend_api.main:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
    )
# deploy: direct DB connection + dockerignore fix + retry logic
