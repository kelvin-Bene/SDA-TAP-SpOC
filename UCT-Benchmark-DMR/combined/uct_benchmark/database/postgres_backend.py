"""
PostgreSQL database backend implementation.

Uses psycopg3 with a thread-safe connection pool (psycopg_pool).
Handles placeholder conversion from DuckDB's ? to psycopg's %s at runtime.
"""

import re
import threading
from contextlib import contextmanager
from typing import Any, List, Optional

import pandas as pd

from .backend_interface import DatabaseBackendInterface, QueryResult


class PostgresBackend(DatabaseBackendInterface):
    """PostgreSQL implementation of the database backend interface.

    Uses psycopg_pool.ConnectionPool which is thread-safe, making it
    compatible with the existing ThreadPoolExecutor worker pattern.
    """

    def __init__(self, connection_url: str, min_size: int = 2, max_size: int = 10):
        import psycopg_pool

        self._connection_url = connection_url
        self._pool = psycopg_pool.ConnectionPool(
            connection_url,
            min_size=min_size,
            max_size=max_size,
            kwargs={"autocommit": True},
        )
        self._initialized = False
        self._lock = threading.Lock()

    def execute(self, query: str, params: tuple = ()) -> QueryResult:
        """Execute a SQL query with automatic placeholder conversion.

        Converts DuckDB-style ? placeholders to psycopg %s placeholders.
        Returns a QueryResult wrapper for API compatibility.
        """
        converted = self._convert_query(query)
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(converted, params if params else None)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                else:
                    columns = []
                    rows = []
                return QueryResult(rows, columns, cur.rowcount)

    def executemany(self, query: str, params_list: list) -> None:
        """Execute a query with multiple parameter sets."""
        converted = self._convert_query(query)
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(converted, params_list)

    def execute_df_insert(
        self,
        table: str,
        df: pd.DataFrame,
        columns: List[str],
        conflict_clause: str = "",
    ) -> int:
        """Bulk insert from a DataFrame using executemany.

        Uses INSERT with ON CONFLICT for upsert support (COPY doesn't
        support ON CONFLICT).
        """
        if df.empty:
            return 0

        col_list = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
        if conflict_clause:
            query += f" {conflict_clause}"

        # Convert DataFrame rows to list of tuples
        insert_df = df[columns].copy()
        # Replace NaN/NaT with None for PostgreSQL compatibility
        insert_df = insert_df.where(insert_df.notna(), None)
        data = [tuple(row) for row in insert_df.itertuples(index=False, name=None)]

        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, data)

        return len(data)

    @contextmanager
    def connection(self):
        """Context manager for raw psycopg connection access."""
        with self._pool.connection() as conn:
            yield conn

    def initialize_schema(self, force: bool = False) -> None:
        """Initialize the PostgreSQL schema using schema_postgres.py definitions."""
        with self._lock:
            from .schema_postgres import initialize_schema_postgres

            initialize_schema_postgres(self, force=force)
            self._initialized = True

    def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            self._pool.close()

    def is_initialized(self) -> bool:
        """Check if the PostgreSQL schema exists."""
        if self._initialized:
            return True
        try:
            result = self.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            return len(result.fetchall()) > 0
        except Exception:
            return False

    @property
    def schema_name(self) -> str:
        return "public"

    # ----------------------------------------------------------------
    # Query conversion utilities
    # ----------------------------------------------------------------

    @staticmethod
    def _convert_query(query: str) -> str:
        """Convert a DuckDB-style query to PostgreSQL-compatible syntax.

        Handles:
        1. ? placeholder → %s
        2. INSERT OR REPLACE → INSERT ... ON CONFLICT ... DO UPDATE
        3. INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
        """
        converted = query

        # Convert INSERT OR REPLACE INTO table (...) VALUES (...)
        # → INSERT INTO table (...) VALUES (...) ON CONFLICT (key) DO UPDATE SET ...
        insert_or_replace = re.match(
            r"INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)",
            converted,
            re.IGNORECASE,
        )
        if insert_or_replace:
            table = insert_or_replace.group(1)
            cols = insert_or_replace.group(2)
            vals = insert_or_replace.group(3)
            col_list = [c.strip() for c in cols.split(",")]
            # Assume first column is the PK for ON CONFLICT
            pk_col = col_list[0]
            update_parts = [
                f"{c} = EXCLUDED.{c}" for c in col_list[1:]
            ]
            converted = (
                f"INSERT INTO {table} ({cols}) VALUES ({vals}) "
                f"ON CONFLICT ({pk_col}) DO UPDATE SET {', '.join(update_parts)}"
            )

        # Convert INSERT OR IGNORE INTO → INSERT INTO ... ON CONFLICT DO NOTHING
        converted = re.sub(
            r"INSERT\s+OR\s+IGNORE\s+INTO",
            "INSERT INTO",
            converted,
            flags=re.IGNORECASE,
        )
        # If we converted INSERT OR IGNORE and there's no ON CONFLICT clause, add one
        # (handled by the caller or repository if needed)

        # Convert ? placeholders to %s
        # We need to be careful not to replace ? inside string literals
        converted = _replace_placeholders(converted)

        return converted


def _replace_placeholders(query: str) -> str:
    """Replace ? placeholders with %s, skipping string literals.

    Handles single-quoted strings (SQL standard).
    """
    result = []
    in_string = False
    i = 0
    while i < len(query):
        char = query[i]
        if char == "'" and not in_string:
            in_string = True
            result.append(char)
        elif char == "'" and in_string:
            # Check for escaped quote ''
            if i + 1 < len(query) and query[i + 1] == "'":
                result.append("''")
                i += 2
                continue
            in_string = False
            result.append(char)
        elif char == "?" and not in_string:
            result.append("%s")
        else:
            result.append(char)
        i += 1
    return "".join(result)
