"""
Abstract database backend interface.

Defines the contract that both DuckDB and PostgreSQL backends must implement.
This enables feature-flag-based switching between backends without changing
consumer code (repositories, workers, routers).
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, List, Optional, Tuple

import pandas as pd


class QueryResult:
    """Unified query result wrapper that normalizes DuckDB and PostgreSQL results."""

    def __init__(
        self,
        rows: List[Tuple],
        columns: List[str],
        rowcount: int = 0,
    ):
        self.rows = rows
        self.columns = columns
        self.rowcount = rowcount
        self.description = [(col,) for col in columns]

    def fetchone(self) -> Optional[Tuple]:
        """Return the first row or None."""
        return self.rows[0] if self.rows else None

    def fetchall(self) -> List[Tuple]:
        """Return all rows."""
        return self.rows

    def fetchdf(self) -> pd.DataFrame:
        """Return results as a pandas DataFrame."""
        if not self.rows:
            return pd.DataFrame(columns=self.columns)
        return pd.DataFrame(self.rows, columns=self.columns)


class DatabaseBackendInterface(ABC):
    """Abstract interface for database backends (DuckDB, PostgreSQL)."""

    @abstractmethod
    def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute a SQL query with positional parameters.

        Args:
            query: SQL query string (uses ? placeholders for DuckDB, %s for PostgreSQL)
            params: Query parameters

        Returns:
            A result object with fetchone(), fetchall(), fetchdf() methods
        """
        ...

    @abstractmethod
    def executemany(self, query: str, params_list: list) -> None:
        """Execute a query with multiple parameter sets.

        Args:
            query: SQL query string with placeholders
            params_list: List of parameter tuples
        """
        ...

    @abstractmethod
    def execute_df_insert(
        self,
        table: str,
        df: pd.DataFrame,
        columns: List[str],
        conflict_clause: str = "",
    ) -> int:
        """Bulk insert from a DataFrame.

        Args:
            table: Target table name
            df: DataFrame containing the data
            columns: Column names to insert
            conflict_clause: ON CONFLICT clause (e.g. "ON CONFLICT (id) DO NOTHING")

        Returns:
            Number of rows inserted
        """
        ...

    @abstractmethod
    @contextmanager
    def connection(self):
        """Context manager for raw connection access.

        Yields:
            A raw database connection object
        """
        ...

    @abstractmethod
    def initialize_schema(self, force: bool = False) -> None:
        """Create tables and seed data.

        Args:
            force: If True, drop and recreate all tables
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Close all connections and clean up resources."""
        ...

    @abstractmethod
    def is_initialized(self) -> bool:
        """Check if the database schema has been created.

        Returns:
            True if tables exist
        """
        ...

    @property
    @abstractmethod
    def schema_name(self) -> str:
        """Return the schema name for information_schema queries.

        Returns:
            'main' for DuckDB, 'public' for PostgreSQL
        """
        ...
