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


@asynccontextmanager
async def db_lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for database initialization.

    Usage:
        app = FastAPI(lifespan=db_lifespan)

    This ensures the database is initialized on startup and properly
    closed on shutdown.
    """
    # Startup
    db = init_database()
    backend = db.backend
    if backend == "duckdb":
        print(f"Database initialized ({backend}): {db.db_path}")
    else:
        print(f"Database initialized ({backend}): PostgreSQL connection pool ready")

    yield

    # Shutdown
    close_database()
    print("Database connection closed.")
