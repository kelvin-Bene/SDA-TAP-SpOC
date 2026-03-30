"""
PostgreSQL database adapter implementation.

Provides PostgreSQL-specific implementation of the DatabaseAdapter interface
using psycopg2 for Supabase/PostgreSQL connectivity.
"""

import os
from contextlib import contextmanager
from typing import Any, Generator, List, Optional, Tuple

import pandas as pd
from loguru import logger

from .base import DatabaseAdapter

# psycopg2 imports — battle-tested PostgreSQL driver
try:
    import psycopg2
    import psycopg2.extras

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    psycopg2 = None


class PostgresAdapter(DatabaseAdapter):
    """
    PostgreSQL implementation of DatabaseAdapter using psycopg2.

    Supports:
    - Supabase connection pooler (Supavisor) with dotted usernames
    - Automatic retry on stale connections
    - Transaction management
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        min_connections: int = 2,
        max_connections: int = 10,
        connect_timeout: int = 10,
    ):
        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. "
                "Install with: pip install psycopg2-binary"
            )

        self.database_url = database_url or os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError(
                "database_url must be provided or DATABASE_URL environment variable must be set"
            )

        self.connect_timeout = connect_timeout
        self._connection = None

        # Build DSN with sslmode for Supabase compatibility
        self._dsn = self.database_url
        if "sslmode" not in self._dsn:
            sep = "&" if "?" in self._dsn else "?"
            self._dsn += f"{sep}sslmode=require"

        # Log connection target (without password)
        from urllib.parse import urlparse
        parsed = urlparse(self.database_url)
        logger.info(
            f"PostgresAdapter configured: host={parsed.hostname} "
            f"port={parsed.port} user={parsed.username} db={parsed.path}"
        )

    def _create_connection(self):
        """Create a new database connection."""
        conn = psycopg2.connect(
            self._dsn,
            connect_timeout=self.connect_timeout,
            options="-c statement_timeout=60000",  # 60s query timeout
        )
        conn.autocommit = False
        logger.debug("New PostgreSQL connection created")
        return conn

    def connect(self) -> None:
        """Establish a database connection."""
        if self._connection is None or self._connection.closed:
            self._connection = self._create_connection()

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None and not self._connection.closed:
            self._connection.close()
        self._connection = None

    def is_connected(self) -> bool:
        """Check if the adapter has an active connection."""
        return self._connection is not None and not self._connection.closed

    def _get_connection(self):
        """Get the current connection, creating one if needed."""
        if self._connection is None or self._connection.closed:
            self.connect()
        return self._connection

    def _drop_connection(self):
        """Safely close and discard the current connection."""
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
        self._connection = None

    def _retry_on_error(self, fn):
        """
        Retry a database operation once on connection errors.

        Drops the stale connection and retries with a fresh one.
        """
        for attempt in range(2):
            try:
                return fn()
            except (psycopg2.InterfaceError, psycopg2.OperationalError,
                    psycopg2.DatabaseError, OSError) as e:
                if attempt == 0:
                    logger.debug(f"DB error on attempt 0, reconnecting: {e}")
                    self._drop_connection()
                    continue
                raise

    @contextmanager
    def connection(self) -> Generator[Any, None, None]:
        """Context manager for database connections."""
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise

    def execute(self, query: str, params: Tuple = ()) -> Any:
        """
        Execute a SQL query with automatic retry on connection failure.

        Args:
            query: SQL query string with %s placeholders
            params: Query parameters

        Returns:
            Cursor object
        """
        converted_query = self.convert_placeholders(query)

        def _do():
            conn = self._get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(converted_query, params)
            else:
                cursor.execute(converted_query)
            conn.commit()
            return cursor

        return self._retry_on_error(_do)

    def executemany(self, query: str, params_list: List[Tuple], batch_size: int = 500) -> None:
        """
        Execute a SQL query with multiple parameter sets using batched multi-row inserts.

        For INSERT statements, uses multi-row VALUES for better performance.
        Each batch is retried once on connection errors.
        """
        if not params_list:
            return

        converted_query = self.convert_placeholders(query)
        normalized_query = " ".join(converted_query.split())
        query_upper = normalized_query.upper()

        if query_upper.startswith("INSERT"):
            import re
            match = re.match(
                r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)(.*)",
                normalized_query,
                re.IGNORECASE,
            )
            if match:
                table = match.group(1)
                columns = match.group(2)
                placeholders = match.group(3)
                conflict_clause = match.group(4).strip()
                num_placeholders = placeholders.count("%s")
                row_placeholder = "(" + ", ".join(["%s"] * num_placeholders) + ")"

                total = len(params_list)
                for batch_start in range(0, total, batch_size):
                    batch = params_list[batch_start:batch_start + batch_size]
                    if not batch:
                        continue
                    values_clause = ", ".join([row_placeholder] * len(batch))
                    batch_query = f"INSERT INTO {table} ({columns}) VALUES {values_clause} {conflict_clause}"
                    flat_params = []
                    for params in batch:
                        flat_params.extend(params)

                    def _do_batch(q=batch_query, p=tuple(flat_params)):
                        conn = self._get_connection()
                        cursor = conn.cursor()
                        cursor.execute(q, p)
                        conn.commit()

                    self._retry_on_error(_do_batch)
                return

        # Fallback: execute one by one
        def _do_fallback():
            conn = self._get_connection()
            cursor = conn.cursor()
            for params in params_list:
                cursor.execute(converted_query, params)
            conn.commit()

        self._retry_on_error(_do_fallback)

    def fetchone(self, query: str, params: Tuple = ()) -> Optional[Tuple]:
        """Execute a query and return a single row."""
        converted_query = self.convert_placeholders(query)

        def _do():
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(converted_query, params if params else None)
            result = cursor.fetchone()
            conn.commit()
            return result

        return self._retry_on_error(_do)

    def fetchall(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """Execute a query and return all rows."""
        converted_query = self.convert_placeholders(query)

        def _do():
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(converted_query, params if params else None)
            result = cursor.fetchall()
            conn.commit()
            return result

        return self._retry_on_error(_do)

    def fetchdf(self, query: str, params: Tuple = ()) -> pd.DataFrame:
        """Execute a query and return results as a DataFrame."""
        converted_query = self.convert_placeholders(query)

        def _do():
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(converted_query, params if params else None)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            conn.commit()
            return pd.DataFrame(rows, columns=columns)

        return self._retry_on_error(_do)

    def bulk_insert_df(
        self,
        table: str,
        df: pd.DataFrame,
        columns: List[str],
        on_conflict: Optional[str] = None,
        conflict_columns: Optional[List[str]] = None,
        batch_size: int = 500,
    ) -> int:
        """Bulk insert data from a DataFrame using batched multi-row inserts."""
        if df.empty:
            return 0

        insert_df = df[columns].copy()
        columns_str = ", ".join(columns)

        # Build conflict clause
        conflict_clause = ""
        if on_conflict and conflict_columns:
            conflict_cols = ", ".join(conflict_columns)
            if on_conflict == "nothing":
                conflict_clause = f" ON CONFLICT ({conflict_cols}) DO NOTHING"
            elif on_conflict == "update":
                update_cols = [c for c in columns if c not in conflict_columns]
                if update_cols:
                    update_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
                    conflict_clause = f" ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_clause}"
                else:
                    conflict_clause = f" ON CONFLICT ({conflict_cols}) DO NOTHING"

        rows = [tuple(row) for row in insert_df.itertuples(index=False, name=None)]
        total_rows = len(rows)
        inserted = 0

        for batch_start in range(0, total_rows, batch_size):
            batch = rows[batch_start:batch_start + batch_size]
            if not batch:
                continue

            row_placeholder = "(" + ", ".join(["%s"] * len(columns)) + ")"
            values_clause = ", ".join([row_placeholder] * len(batch))
            query = f"INSERT INTO {table} ({columns_str}) VALUES {values_clause}{conflict_clause}"
            params = []
            for row in batch:
                params.extend(row)

            def _do_batch(q=query, p=tuple(params)):
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(q, p)
                conn.commit()

            self._retry_on_error(_do_batch)
            inserted += len(batch)

        return inserted

    def get_tables(self) -> List[str]:
        """Get list of all tables in the database."""
        result = self.fetchall(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        return [row[0] for row in result]

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        result = self.fetchone(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (table_name,),
        )
        return result[0] > 0 if result else False

    def get_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        result = self.fetchone(f"SELECT COUNT(*) FROM {table_name}")
        return result[0] if result else 0

    @property
    def backend_name(self) -> str:
        return "postgres"

    @property
    def placeholder(self) -> str:
        return "%s"

    @property
    def schema_name(self) -> str:
        return "public"

    # PostgreSQL-specific methods

    def execute_returning(self, query: str, params: Tuple = ()) -> Optional[Tuple]:
        """Execute an INSERT/UPDATE with RETURNING clause."""
        return self.fetchone(query, params)

    def begin_transaction(self) -> Any:
        """Begin a manual transaction."""
        return self._get_connection()

    def commit_transaction(self, conn: Any) -> None:
        """Commit a manual transaction."""
        conn.commit()

    def rollback_transaction(self, conn: Any) -> None:
        """Rollback a manual transaction."""
        conn.rollback()

    def get_server_version(self) -> str:
        """Get the PostgreSQL server version."""
        result = self.fetchone("SELECT version()")
        return result[0] if result else "unknown"

    def vacuum_analyze(self, table_name: Optional[str] = None) -> None:
        """Run VACUUM ANALYZE on a table or the entire database."""
        conn = self._get_connection()
        old_autocommit = conn.autocommit
        conn.autocommit = True
        cursor = conn.cursor()
        if table_name:
            cursor.execute(f"VACUUM ANALYZE {table_name}")
        else:
            cursor.execute("VACUUM ANALYZE")
        conn.autocommit = old_autocommit
