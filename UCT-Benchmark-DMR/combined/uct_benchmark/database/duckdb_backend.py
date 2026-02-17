"""
DuckDB database backend implementation.

Extracts the DuckDB-specific logic from the original DatabaseManager
and implements the DatabaseBackendInterface contract.
"""

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, List, Optional

import duckdb
import pandas as pd

from .backend_interface import DatabaseBackendInterface


class DuckDBBackend(DatabaseBackendInterface):
    """DuckDB implementation of the database backend interface."""

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        read_only: bool = False,
        in_memory: bool = False,
    ):
        self.in_memory = in_memory
        self.read_only = read_only

        if in_memory:
            self.db_path = ":memory:"
        else:
            if db_path is None:
                from .connection import get_db_path

                db_path = get_db_path()
            self.db_path = Path(db_path) if not isinstance(db_path, Path) and db_path != ":memory:" else db_path
            if isinstance(self.db_path, Path):
                self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._local = threading.local()
        self._lock = threading.Lock()
        self._initialized = False
        self._shared_connection: Optional[duckdb.DuckDBPyConnection] = None

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create a thread-local DuckDB connection."""
        if self.in_memory:
            if self._shared_connection is None:
                config = {}
                if self.read_only:
                    config["access_mode"] = "read_only"
                self._shared_connection = duckdb.connect(":memory:", config=config)
            return self._shared_connection

        if not hasattr(self._local, "connection") or self._local.connection is None:
            config = {}
            if self.read_only:
                config["access_mode"] = "read_only"
            self._local.connection = duckdb.connect(
                str(self.db_path) if isinstance(self.db_path, Path) else self.db_path,
                config=config,
            )
        return self._local.connection

    def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute a SQL query. Returns the native DuckDB relation object."""
        return self._get_connection().execute(query, params)

    def executemany(self, query: str, params_list: list) -> None:
        """Execute a SQL query with multiple parameter sets."""
        self._get_connection().executemany(query, params_list)

    def execute_df_insert(
        self,
        table: str,
        df: pd.DataFrame,
        columns: List[str],
        conflict_clause: str = "",
    ) -> int:
        """Bulk insert from a DataFrame using DuckDB's register/unregister pattern."""
        if df.empty:
            return 0

        conn = self._get_connection()
        temp_name = f"_temp_insert_{table}"
        insert_df = df[columns].copy()

        col_list = ", ".join(columns)
        select_list = ", ".join(columns)

        conn.register(temp_name, insert_df)
        try:
            query = f"INSERT INTO {table} ({col_list}) SELECT {select_list} FROM {temp_name}"
            if conflict_clause:
                query += f" {conflict_clause}"
            conn.execute(query)
        finally:
            conn.unregister(temp_name)

        return len(df)

    @contextmanager
    def connection(self):
        """Context manager for raw DuckDB connection access."""
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            raise

    def initialize_schema(self, force: bool = False) -> None:
        """Initialize the DuckDB schema."""
        from .schema import initialize_schema

        with self._lock:
            # We need a DatabaseManager-like interface for schema init
            initialize_schema(self, force=force)
            self._initialized = True

    def close(self) -> None:
        """Close all DuckDB connections."""
        if self._shared_connection is not None:
            self._shared_connection.close()
            self._shared_connection = None

        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    def is_initialized(self) -> bool:
        """Check if the DuckDB schema exists."""
        if self._initialized:
            return True
        try:
            result = self.execute(
                f"SELECT name FROM information_schema.tables WHERE table_schema = '{self.schema_name}'"
            ).fetchall()
            return len(result) > 0
        except Exception:
            return False

    @property
    def schema_name(self) -> str:
        return "main"
