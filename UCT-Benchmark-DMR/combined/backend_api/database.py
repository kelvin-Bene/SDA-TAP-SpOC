"""
Database integration module for FastAPI backend.

Provides a singleton DatabaseManager for dependency injection and
lifespan management.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI

from uct_benchmark.database.connection import DatabaseManager


# Global database manager instance (singleton)
_db_manager: Optional[DatabaseManager] = None


def get_database_path() -> Path:
    """Get database path from environment or use default."""
    db_path = os.getenv("DATABASE_PATH")
    if db_path:
        return Path(db_path)
    # Default path relative to project root
    return Path(__file__).parent.parent / "data" / "database" / "uct_benchmark.duckdb"


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
        raise RuntimeError(
            "Database not initialized. Ensure the app lifespan context is active."
        )
    return _db_manager


def init_database(db_path: Optional[Path] = None) -> DatabaseManager:
    """
    Initialize the database manager singleton.

    Args:
        db_path: Optional path to database file. Uses default if not provided.

    Returns:
        DatabaseManager: The initialized database instance
    """
    global _db_manager

    if _db_manager is not None:
        return _db_manager

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
    print(f"Database initialized at: {db.db_path}")

    yield

    # Shutdown
    close_database()
    print("Database connection closed.")
