"""
Database integration module for FastAPI backend.

Provides a singleton DatabaseManager for dependency injection and
lifespan management. Supports both DuckDB (local) and PostgreSQL (Supabase) backends.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI

from uct_benchmark.database.connection import DatabaseManager

# Global database manager instance (singleton)
_db_manager: Optional[DatabaseManager] = None


def get_database_backend() -> str:
    """
    Get database backend from environment.

    Returns:
        Backend name: 'duckdb' or 'postgres'
    """
    return os.getenv("DATABASE_BACKEND", "duckdb").lower()


def get_database_url() -> Optional[str]:
    """
    Get database URL from environment (for PostgreSQL).

    Returns:
        PostgreSQL connection string or None
    """
    return os.getenv("DATABASE_URL")


def get_database_path() -> Path:
    """
    Get database path from environment or use default (for DuckDB).

    Returns:
        Path to the DuckDB database file
    """
    db_path = os.getenv("DATABASE_PATH")
    if db_path:
        return Path(db_path)
    # Default path relative to project root
    return Path(__file__).parent.parent / "data" / "database" / "uct_benchmark.duckdb"


def get_pool_config() -> dict:
    """
    Get connection pool configuration from environment.

    Returns:
        Dictionary with pool_min and pool_max settings
    """
    return {
        "pool_min": int(os.getenv("DATABASE_POOL_MIN", "2")),
        "pool_max": int(os.getenv("DATABASE_POOL_MAX", "10")),
    }


def get_db() -> DatabaseManager:
    """
    Get the database manager instance.

    Used as a FastAPI dependency for routes that need database access.

    Returns:
        DatabaseManager: The singleton database instance

    Raises:
        RuntimeError: If database has not been initialized
    """
    global _db_manager
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Ensure the app lifespan context is active.")
    return _db_manager


def init_database(
    db_path: Optional[Path] = None,
    database_url: Optional[str] = None,
    backend: Optional[str] = None,
) -> DatabaseManager:
    """
    Initialize the database manager singleton.

    Supports both DuckDB and PostgreSQL backends based on configuration.

    Args:
        db_path: Optional path to DuckDB file (DuckDB only)
        database_url: Optional PostgreSQL connection string (PostgreSQL only)
        backend: Optional backend override ('duckdb' or 'postgres')

    Returns:
        DatabaseManager: The initialized database instance

    Environment Variables:
        DATABASE_BACKEND: 'duckdb' or 'postgres' (default: 'duckdb')
        DATABASE_URL: PostgreSQL connection string (required for postgres backend)
        DATABASE_PATH: Path to DuckDB file (optional, uses default if not set)
        DATABASE_POOL_MIN: Minimum pool size for PostgreSQL (default: 2)
        DATABASE_POOL_MAX: Maximum pool size for PostgreSQL (default: 10)
    """
    global _db_manager

    if _db_manager is not None:
        return _db_manager

    # Determine backend
    backend = backend or get_database_backend()

    if backend in ("postgres", "postgresql", "supabase"):
        # PostgreSQL/Supabase configuration
        url = database_url or get_database_url()

        if not url:
            raise ValueError(
                "DATABASE_URL environment variable must be set for PostgreSQL backend. "
                "See docs/SUPABASE_SETUP.md for configuration instructions."
            )

        pool_config = get_pool_config()
        _db_manager = DatabaseManager(
            backend="postgres",
            database_url=url,
            pool_min=pool_config["pool_min"],
            pool_max=pool_config["pool_max"],
        )
    else:
        # DuckDB configuration (default)
        path = db_path or get_database_path()
        _db_manager = DatabaseManager(db_path=path)

    _db_manager.initialize()
    return _db_manager


def close_database() -> None:
    """Close the database connection and clear the singleton."""
    global _db_manager
    if _db_manager is not None:
        _db_manager.close()
        _db_manager = None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 LLM features: shared DB handle for SQL execution
# ─────────────────────────────────────────────────────────────────────────────
#
# See the docstring on get_llm_db() for why this is just an alias for
# get_db() rather than a separate read-only handle. The original plan was
# to open a second read-only DuckDB connection alongside the writer; that
# fails because DuckDB blocks intra-process secondary opens of an already-
# held file. The sqlglot AST validator in services/llm/sql_safety.py is
# the primary safety control instead.


def get_llm_db() -> DatabaseManager:
    """
    Return a DatabaseManager handle for LLM-generated SQL execution.

    Originally this was supposed to be a SECOND read-only handle alongside
    the main writer. That doesn't work in practice — DuckDB blocks intra-
    process secondary opens of a file already held by another connection
    in the same process ("Conflicting lock is held in PID X"). Cross-
    process read-only handles ARE allowed, but spawning a worker process
    per LLM call is more complexity than the security gain warrants.

    Instead, we return the SAME singleton as get_db(). The five-layer SQL
    safety pipeline in backend_api/services/llm/sql_safety.py is the
    primary control — it parses every LLM-generated query with sqlglot
    and rejects anything that isn't a SELECT against an allowlisted
    table. DuckDB read-only mode would have been defense-in-depth on top
    of that, but it's not load-bearing.

    Used as a FastAPI dependency by backend_api/routers/llm.py. Cloud
    builds never call this because the llm router is never mounted there.
    """
    return get_db()


@asynccontextmanager
async def db_lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for database initialization.

    Usage:
        app = FastAPI(lifespan=db_lifespan)

    This ensures the database is initialized on startup and properly
    closed on shutdown.
    """
    from loguru import logger

    # Startup
    db = init_database()
    backend = db.backend
    if backend == "duckdb":
        logger.info(f"Database initialized ({backend}): {db.db_path}")
    else:
        logger.info(f"Database initialized ({backend}): PostgreSQL connection pool ready")

    yield

    # Shutdown
    close_database()
    logger.info("Database connection closed.")
