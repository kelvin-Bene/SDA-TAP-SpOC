"""
Abstract database adapter interface for UCT Benchmark.

Provides a common interface for different database backends (DuckDB, PostgreSQL).
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Generator, List, Optional, Tuple

import pandas as pd


class DatabaseAdapter(ABC):
    """
    Abstract base class for database adapters.

    Implementations must provide methods for:
    - Connection management
    - Query execution
    - DataFrame operations
    - Transaction support
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish a database connection."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the adapter has an active connection."""
        pass

    @abstractmethod
    @contextmanager
    def connection(self) -> Generator[Any, None, None]:
        """
        Context manager for database connections.

        Yields:
            Database connection object
        """
        pass

    @abstractmethod
    def execute(self, query: str, params: Tuple = ()) -> Any:
        """
        Execute a SQL query.

        Args:
            query: SQL query string with placeholders
            params: Query parameters

        Returns:
            Query result object (implementation-specific)
        """
        pass

    @abstractmethod
    def executemany(self, query: str, params_list: List[Tuple]) -> None:
        """
        Execute a SQL query with multiple parameter sets.

        Args:
            query: SQL query string with placeholders
            params_list: List of parameter tuples
        """
        pass

    @abstractmethod
    def fetchone(self, query: str, params: Tuple = ()) -> Optional[Tuple]:
        """
        Execute a query and return a single row.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Single row as tuple, or None if no results
        """
        pass

    @abstractmethod
    def fetchall(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """
        Execute a query and return all rows.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of tuples
        """
        pass

    @abstractmethod
    def fetchdf(self, query: str, params: Tuple = ()) -> pd.DataFrame:
        """
        Execute a query and return results as a DataFrame.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            pandas DataFrame with query results
        """
        pass

    @abstractmethod
    def bulk_insert_df(
        self,
        table: str,
        df: pd.DataFrame,
        columns: List[str],
        on_conflict: Optional[str] = None,
        conflict_columns: Optional[List[str]] = None,
    ) -> int:
        """
        Bulk insert data from a DataFrame.

        Args:
            table: Target table name
            df: DataFrame with data to insert
            columns: List of columns to insert
            on_conflict: Conflict resolution strategy ('nothing', 'update', or None)
            conflict_columns: Columns that define uniqueness for conflict resolution

        Returns:
            Number of rows inserted
        """
        pass

    @abstractmethod
    def get_tables(self) -> List[str]:
        """
        Get list of all tables in the database.

        Returns:
            List of table names
        """
        pass

    @abstractmethod
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists.

        Args:
            table_name: Name of the table

        Returns:
            True if the table exists
        """
        pass

    @abstractmethod
    def get_row_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.

        Args:
            table_name: Name of the table

        Returns:
            Number of rows
        """
        pass

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the name of the database backend (e.g., 'duckdb', 'postgres')."""
        pass

    @property
    @abstractmethod
    def placeholder(self) -> str:
        """Return the placeholder style for this backend ('?' or '%s')."""
        pass

    def convert_placeholders(self, query: str) -> str:
        """
        Convert query placeholders to the backend's native format.

        By default, assumes queries use '?' placeholders.
        Override in subclasses if needed.

        Args:
            query: SQL query with '?' placeholders

        Returns:
            Query with backend-specific placeholders
        """
        if self.placeholder == "?":
            return query
        # Convert ? to %s for PostgreSQL-style backends
        return query.replace("?", "%s")

    @property
    def schema_name(self) -> str:
        """Return the default schema name ('main' for DuckDB, 'public' for PostgreSQL)."""
        return "main"
