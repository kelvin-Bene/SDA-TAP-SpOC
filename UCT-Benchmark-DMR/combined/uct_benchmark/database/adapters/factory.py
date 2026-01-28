"""
Database adapter factory for UCT Benchmark.

Provides factory functions to create appropriate database adapters
based on configuration.
"""

import os
from pathlib import Path
from typing import Optional

from .base import DatabaseAdapter
from .duckdb_adapter import DuckDBAdapter

# PostgreSQL/Supabase connection requires DATABASE_URL environment variable
# Example: postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres
# See docs/SUPABASE_SETUP.md for configuration instructions


def get_database_backend() -> str:
    """
    Determine the database backend from environment configuration.

    Checks DATABASE_BACKEND environment variable.
    Falls back to 'duckdb' if not set.

    Returns:
        Backend name: 'duckdb' or 'postgres'
    """
    return os.environ.get("DATABASE_BACKEND", "duckdb").lower()


def create_adapter(
    backend: Optional[str] = None,
    # DuckDB options
    db_path: Optional[str | Path] = None,
    in_memory: bool = False,
    read_only: bool = False,
    # PostgreSQL options
    database_url: Optional[str] = None,
    pool_min: Optional[int] = None,
    pool_max: Optional[int] = None,
) -> DatabaseAdapter:
    """
    Create a database adapter based on configuration.

    Args:
        backend: Database backend ('duckdb' or 'postgres').
                 If None, reads from DATABASE_BACKEND env var.

        DuckDB options:
            db_path: Path to DuckDB file.
            in_memory: Use in-memory database.
            read_only: Open in read-only mode.

        PostgreSQL options:
            database_url: PostgreSQL connection string.
                          If None, reads from DATABASE_URL env var.
            pool_min: Minimum connection pool size.
            pool_max: Maximum connection pool size.

    Returns:
        Configured DatabaseAdapter instance.

    Raises:
        ValueError: If backend is unknown or required parameters are missing.
    """
    backend = backend or get_database_backend()

    if backend == "duckdb":
        return _create_duckdb_adapter(
            db_path=db_path,
            in_memory=in_memory,
            read_only=read_only,
        )
    elif backend in ("postgres", "postgresql", "supabase"):
        return _create_postgres_adapter(
            database_url=database_url,
            pool_min=pool_min,
            pool_max=pool_max,
        )
    else:
        raise ValueError(
            f"Unknown database backend: {backend}. "
            "Supported backends: 'duckdb', 'postgres'"
        )


def _create_duckdb_adapter(
    db_path: Optional[str | Path] = None,
    in_memory: bool = False,
    read_only: bool = False,
) -> DuckDBAdapter:
    """
    Create a DuckDB adapter with configuration from environment.

    Args:
        db_path: Path to DuckDB file. If None, reads from DATABASE_PATH env var.
        in_memory: Use in-memory database.
        read_only: Open in read-only mode.

    Returns:
        Configured DuckDBAdapter instance.
    """
    if not in_memory and db_path is None:
        # Try to get path from environment
        env_path = os.environ.get("DATABASE_PATH")
        if env_path:
            db_path = Path(env_path)
        else:
            # Fall back to default path
            try:
                from uct_benchmark.settings import DATA_DIR

                db_path = DATA_DIR / "database" / "uct_benchmark.duckdb"
            except ImportError:
                db_path = Path(__file__).parent.parent.parent.parent / "data" / "database" / "uct_benchmark.duckdb"

    return DuckDBAdapter(
        db_path=db_path,
        in_memory=in_memory,
        read_only=read_only,
    )


def _create_postgres_adapter(
    database_url: Optional[str] = None,
    pool_min: Optional[int] = None,
    pool_max: Optional[int] = None,
) -> DatabaseAdapter:
    """
    Create a PostgreSQL adapter with configuration from environment.

    Args:
        database_url: PostgreSQL connection string.
                      If None, reads from DATABASE_URL env var.
        pool_min: Minimum connection pool size. Defaults to DATABASE_POOL_MIN env var or 2.
        pool_max: Maximum connection pool size. Defaults to DATABASE_POOL_MAX env var or 10.

    Returns:
        Configured PostgresAdapter instance.

    Raises:
        ValueError: If DATABASE_URL is not provided or set in environment.
    """
    # Import here to avoid requiring psycopg when using DuckDB
    from .postgres_adapter import PostgresAdapter

    # Get connection URL from parameter or environment
    url = database_url or os.environ.get("DATABASE_URL")

    if not url:
        raise ValueError(
            "DATABASE_URL environment variable must be set for PostgreSQL backend. "
            "See docs/SUPABASE_SETUP.md for configuration instructions."
        )

    # Get pool configuration from environment if not provided
    min_conn = pool_min
    if min_conn is None:
        min_conn = int(os.environ.get("DATABASE_POOL_MIN", "2"))

    max_conn = pool_max
    if max_conn is None:
        max_conn = int(os.environ.get("DATABASE_POOL_MAX", "10"))

    return PostgresAdapter(
        database_url=url,
        min_connections=min_conn,
        max_connections=max_conn,
    )


def create_test_adapter(backend: Optional[str] = None) -> DatabaseAdapter:
    """
    Create a database adapter suitable for testing.

    For DuckDB, creates an in-memory database.
    For PostgreSQL, uses the TEST_DATABASE_URL environment variable.

    Args:
        backend: Database backend to use. If None, reads from TEST_DATABASE_BACKEND
                 env var, falling back to DATABASE_BACKEND, then 'duckdb'.

    Returns:
        Configured DatabaseAdapter instance for testing.
    """
    # Determine backend for tests
    if backend is None:
        backend = os.environ.get(
            "TEST_DATABASE_BACKEND",
            os.environ.get("DATABASE_BACKEND", "duckdb")
        ).lower()

    if backend == "duckdb":
        return DuckDBAdapter(in_memory=True)
    elif backend in ("postgres", "postgresql", "supabase"):
        from .postgres_adapter import PostgresAdapter

        test_url = os.environ.get("TEST_DATABASE_URL")
        if not test_url:
            raise ValueError(
                "TEST_DATABASE_URL environment variable must be set "
                "for PostgreSQL testing"
            )
        return PostgresAdapter(
            database_url=test_url,
            min_connections=1,
            max_connections=5,
        )
    else:
        raise ValueError(f"Unknown test database backend: {backend}")
