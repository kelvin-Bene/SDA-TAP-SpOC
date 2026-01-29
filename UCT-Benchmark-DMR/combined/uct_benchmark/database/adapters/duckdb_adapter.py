"""
DuckDB database adapter implementation.

Provides DuckDB-specific implementation of the DatabaseAdapter interface.
"""

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, List, Optional, Tuple

import duckdb
import pandas as pd

from .base import DatabaseAdapter


class DuckDBAdapter(DatabaseAdapter):
    """
    DuckDB implementation of DatabaseAdapter.

    Supports:
    - File-based databases
    - In-memory databases
    - Read-only mode
    - Thread-local connection management
    """

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        read_only: bool = False,
        in_memory: bool = False,
    ):
        """
        Initialize the DuckDB adapter.

        Args:
            db_path: Path to the DuckDB file. If None and not in_memory, raises error.
            read_only: If True, open database in read-only mode.
            in_memory: If True, use an in-memory database (ignores db_path).
        """
        self.in_memory = in_memory
        self.read_only = read_only

        if in_memory:
            self.db_path: str | Path = ":memory:"
        elif db_path:
            self.db_path = Path(db_path)
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            raise ValueError("db_path is required when not using in_memory mode")

        self._local = threading.local()
        self._lock = threading.Lock()

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create a thread-local connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            config = {}
            if self.read_only:
                config["access_mode"] = "read_only"

            self._local.connection = duckdb.connect(
                str(self.db_path) if isinstance(self.db_path, Path) else self.db_path,
                config=config,
            )
        return self._local.connection

    def connect(self) -> None:
        """Establish a database connection."""
        self._get_connection()

    def close(self) -> None:
        """Close the current thread's connection."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    def is_connected(self) -> bool:
        """Check if the adapter has an active connection."""
        return hasattr(self._local, "connection") and self._local.connection is not None

    @contextmanager
    def connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """
        Context manager for database connections.

        Yields:
            DuckDB connection object
        """
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            raise

    def execute(self, query: str, params: Tuple = ()) -> duckdb.DuckDBPyRelation:
        """
        Execute a SQL query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            DuckDB relation object
        """
        return self._get_connection().execute(query, params)

    def executemany(self, query: str, params_list: List[Tuple]) -> None:
        """
        Execute a SQL query with multiple parameter sets.

        Args:
            query: SQL query string with placeholders
            params_list: List of parameter tuples
        """
        self._get_connection().executemany(query, params_list)

    def fetchone(self, query: str, params: Tuple = ()) -> Optional[Tuple]:
        """
        Execute a query and return a single row.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Single row as tuple, or None if no results
        """
        return self.execute(query, params).fetchone()

    def fetchall(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """
        Execute a query and return all rows.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of tuples
        """
        return self.execute(query, params).fetchall()

    def fetchdf(self, query: str, params: Tuple = ()) -> pd.DataFrame:
        """
        Execute a query and return results as a DataFrame.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            pandas DataFrame with query results
        """
        return self.execute(query, params).fetchdf()

    def bulk_insert_df(
        self,
        table: str,
        df: pd.DataFrame,
        columns: List[str],
        on_conflict: Optional[str] = None,
        conflict_columns: Optional[List[str]] = None,
    ) -> int:
        """
        Bulk insert data from a DataFrame using DuckDB's efficient DataFrame registration.

        Args:
            table: Target table name
            df: DataFrame with data to insert
            columns: List of columns to insert
            on_conflict: Conflict resolution ('nothing', 'update', or None)
            conflict_columns: Columns that define uniqueness for conflict resolution

        Returns:
            Number of rows inserted
        """
        if df.empty:
            return 0

        # Filter to requested columns
        insert_df = df[columns].copy()

        # Convert pandas StringDtype to object for DuckDB compatibility
        for col in insert_df.columns:
            dtype_name = insert_df[col].dtype.name
            dtype_str = str(insert_df[col].dtype)
            if dtype_name in ("string", "str") or dtype_str in ("string", "str"):
                insert_df[col] = insert_df[col].astype(object)

        conn = self._get_connection()
        temp_table_name = f"temp_bulk_insert_{table}"
        conn.register(temp_table_name, insert_df)

        try:
            columns_str = ", ".join(columns)

            if on_conflict == "nothing" and conflict_columns:
                # Use ON CONFLICT DO NOTHING
                conflict_cols = ", ".join(conflict_columns)
                conn.execute(
                    f"""
                    INSERT INTO {table} ({columns_str})
                    SELECT {columns_str} FROM {temp_table_name}
                    ON CONFLICT ({conflict_cols}) DO NOTHING
                    """
                )
            elif on_conflict == "update" and conflict_columns:
                # Use ON CONFLICT DO UPDATE
                conflict_cols = ", ".join(conflict_columns)
                update_cols = [c for c in columns if c not in conflict_columns]
                update_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
                conn.execute(
                    f"""
                    INSERT INTO {table} ({columns_str})
                    SELECT {columns_str} FROM {temp_table_name}
                    ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_clause}
                    """
                )
            else:
                # Simple insert
                conn.execute(
                    f"""
                    INSERT INTO {table} ({columns_str})
                    SELECT {columns_str} FROM {temp_table_name}
                    """
                )
        finally:
            conn.unregister(temp_table_name)

        return len(df)

    def get_tables(self) -> List[str]:
        """
        Get list of all tables in the database.

        Returns:
            List of table names
        """
        result = self.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        return [row[0] for row in result]

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists.

        Args:
            table_name: Name of the table

        Returns:
            True if the table exists
        """
        result = self.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'main' AND table_name = ?
            """,
            (table_name,),
        ).fetchone()
        return result[0] > 0 if result else False

    def get_row_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.

        Args:
            table_name: Name of the table

        Returns:
            Number of rows
        """
        result = self.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0] if result else 0

    @property
    def backend_name(self) -> str:
        """Return the name of the database backend."""
        return "duckdb"

    @property
    def placeholder(self) -> str:
        """Return the placeholder style for DuckDB."""
        return "?"

    @property
    def schema_name(self) -> str:
        """Return the default schema name for DuckDB."""
        return "main"

    # DuckDB-specific methods

    def register_df(self, name: str, df: pd.DataFrame) -> None:
        """
        Register a DataFrame as a virtual table.

        Args:
            name: Name to register the DataFrame as
            df: DataFrame to register
        """
        self._get_connection().register(name, df)

    def unregister_df(self, name: str) -> None:
        """
        Unregister a previously registered DataFrame.

        Args:
            name: Name of the registered DataFrame
        """
        self._get_connection().unregister(name)

    def vacuum(self) -> None:
        """Optimize the database by reclaiming unused space."""
        self.execute("VACUUM")

    def get_file_size_mb(self) -> Optional[float]:
        """
        Get the database file size in MB.

        Returns:
            File size in MB, or None if in-memory database
        """
        if self.in_memory or not isinstance(self.db_path, Path):
            return None
        if self.db_path.exists():
            return self.db_path.stat().st_size / (1024 * 1024)
        return None
