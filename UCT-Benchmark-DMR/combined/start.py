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
    # Run database migrations before starting (PostgreSQL only)
    if os.environ.get("DATABASE_URL"):
        import subprocess
        import sys
        print("Running database migrations...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                print(f"Migration FAILED: {result.stderr}", file=sys.stderr)
                sys.exit(1)
            else:
                print("Database migrations complete.")
        except Exception as e:
            print(f"Migration FAILED: {e}", file=sys.stderr)
            sys.exit(1)

    def validate_config():
        """Validate critical environment variables before starting."""
        import sys
        errors = []
        db_backend = os.environ.get("DATABASE_BACKEND", "duckdb")
        if db_backend in ("postgres", "supabase"):
            if not os.environ.get("DATABASE_URL"):
                errors.append("DATABASE_URL required when DATABASE_BACKEND=postgres")
            if not os.environ.get("ENCRYPTION_KEY"):
                errors.append("ENCRYPTION_KEY required when DATABASE_BACKEND=postgres")
        env = os.environ.get("ENVIRONMENT", "").lower()
        if env == "development" and db_backend in ("postgres", "supabase"):
            errors.append(
                "ENVIRONMENT=development is not allowed with DATABASE_BACKEND="
                f"{db_backend}. Use a proper SUPABASE_JWT_SECRET for auth."
            )
        cors = os.environ.get("CORS_ORIGINS", "")
        if cors and "*" in cors:
            errors.append("CORS_ORIGINS='*' is incompatible with credential-based auth")
        if errors:
            for e in errors:
                print(f"CONFIG ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    validate_config()

    uvicorn.run(
        "backend_api.main:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
    )
# deploy: direct DB connection + dockerignore fix + retry logic
