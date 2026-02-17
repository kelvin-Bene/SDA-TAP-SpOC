"""
Database adapters for UCT Benchmark.

This module provides database backend abstraction through the adapter pattern,
supporting both DuckDB (local development) and PostgreSQL (Supabase production).

Usage:
    from uct_benchmark.database.adapters import create_adapter, DatabaseAdapter

    # Create adapter based on environment configuration
    adapter = create_adapter()

    # Or specify backend explicitly
    adapter = create_adapter(backend='duckdb', db_path='./data/db.duckdb')
    adapter = create_adapter(backend='postgres', database_url='postgresql://...')

    # For testing
    adapter = create_test_adapter()  # In-memory DuckDB by default
"""

from .base import DatabaseAdapter
from .duckdb_adapter import DuckDBAdapter
from .factory import create_adapter, create_test_adapter, get_database_backend

# PostgresAdapter is imported on-demand to avoid requiring psycopg
# when only using DuckDB
__all__ = [
    "DatabaseAdapter",
    "DuckDBAdapter",
    "create_adapter",
    "create_test_adapter",
    "get_database_backend",
]


def get_postgres_adapter():
    """
    Import and return the PostgresAdapter class.

    This is a convenience function to lazily import PostgresAdapter,
    avoiding the need to have psycopg installed when only using DuckDB.

    Returns:
        PostgresAdapter class

    Raises:
        ImportError: If psycopg is not installed
    """
    from .postgres_adapter import PostgresAdapter

    return PostgresAdapter
