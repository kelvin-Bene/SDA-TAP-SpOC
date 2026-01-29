"""
PostgreSQL database adapter implementation.

Provides PostgreSQL-specific implementation of the DatabaseAdapter interface
using pg8000 for direct Supabase/PostgreSQL connectivity.
"""

import os
from contextlib import contextmanager
from typing import Any, Generator, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

import pandas as pd

from .base import DatabaseAdapter

# pg8000 imports - pure Python PostgreSQL driver
try:
    import pg8000
    import pg8000.native

    PG8000_AVAILABLE = True
except ImportError:
    PG8000_AVAILABLE = False
    pg8000 = None


class PostgresAdapter(DatabaseAdapter):
    """
    PostgreSQL implementation of DatabaseAdapter.

    Supports:
    - Connection pooling for concurrent access
    - Direct PostgreSQL/Supabase connectivity
    - Transaction management
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        min_connections: int = 2,
        max_connections: int = 10,
        connect_timeout: int = 10,
    ):
        """
        Initialize the PostgreSQL adapter.

        Args:
            database_url: PostgreSQL connection string.
                          If None, reads from DATABASE_URL environment variable.
            min_connections: Minimum number of connections in pool.
            max_connections: Maximum number of connections in pool.
            connect_timeout: Connection timeout in seconds.
        """
        if not PG8000_AVAILABLE:
            raise ImportError(
                "pg8000 is required for PostgreSQL support. "
                "Install with: pip install pg8000"
            )

        self.database_url = database_url or os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError(
                "database_url must be provided or DATABASE_URL environment variable must be set"
            )

        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connect_timeout = connect_timeout

        self._connection: Optional[pg8000.Connection] = None

        # Parse connection string
        parsed = urlparse(self.database_url)
        self._host = parsed.hostname or "localhost"
        self._port = parsed.port or 5432
        self._database = parsed.path.lstrip("/") if parsed.path else "postgres"
        self._user = parsed.username or "postgres"
        self._password = parsed.password or ""

        # Parse query params for SSL mode
        query_params = parse_qs(parsed.query)
        self._ssl_context = None

        # Determine if SSL should be used
        # For remote hosts (especially Supabase), default to SSL
        is_remote = self._host not in ("localhost", "127.0.0.1", "::1")
        sslmode = query_params.get("sslmode", ["require" if is_remote else "disable"])[0]

        if sslmode in ("require", "verify-ca", "verify-full", "prefer"):
            import ssl
            self._ssl_context = ssl.create_default_context()
            # Supabase pooler uses a certificate that may not validate normally
            # Disable hostname check and cert verification for compatibility
            self._ssl_context.check_hostname = False
            self._ssl_context.verify_mode = ssl.CERT_NONE

    def _create_connection(self) -> pg8000.Connection:
        """Create a new database connection."""
        import socket as sock_module

        # Set a global socket timeout for read/write operations
        # This prevents timeouts during long-running queries with Supabase
        sock_module.setdefaulttimeout(60)  # 60 second timeout for all socket operations

        kwargs = {
            "host": self._host,
            "port": self._port,
            "database": self._database,
            "user": self._user,
            "password": self._password,
            "timeout": self.connect_timeout,
        }
        if self._ssl_context:
            kwargs["ssl_context"] = self._ssl_context
        return pg8000.connect(**kwargs)

    def connect(self) -> None:
        """Establish a database connection."""
        if self._connection is None:
            self._connection = self._create_connection()

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def is_connected(self) -> bool:
        """Check if the adapter has an active connection."""
        return self._connection is not None

    def _get_connection(self) -> pg8000.Connection:
        """Get the current connection, creating one if needed."""
        if self._connection is None:
            self.connect()
        return self._connection

    @contextmanager
    def connection(self) -> Generator[Any, None, None]:
        """
        Context manager for database connections.

        Yields:
            pg8000 Connection object
        """
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise

    def execute(self, query: str, params: Tuple = ()) -> Any:
        """
        Execute a SQL query.

        Args:
            query: SQL query string with %s placeholders
            params: Query parameters

        Returns:
            Cursor object
        """
        converted_query = self.convert_placeholders(query)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(converted_query, params)
        conn.commit()
        return cursor

    def executemany(self, query: str, params_list: List[Tuple], batch_size: int = 500) -> None:
        """
        Execute a SQL query with multiple parameter sets using batched multi-row inserts.

        For INSERT statements, uses multi-row VALUES for much better performance.
        Falls back to individual execution for non-INSERT queries.

        Args:
            query: SQL query string with placeholders
            params_list: List of parameter tuples
            batch_size: Number of rows per batch (default 500)
        """
        if not params_list:
            return

        converted_query = self.convert_placeholders(query)
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if this is an INSERT statement that can be batched
        # Normalize whitespace for easier parsing
        normalized_query = " ".join(converted_query.split())
        query_upper = normalized_query.upper()

        if query_upper.startswith("INSERT"):
            # Parse the INSERT query to extract table, columns, and conflict clause
            import re

            # Match: INSERT INTO table (cols) VALUES (%s, %s, ...) [ON CONFLICT ...]
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

                # Count number of placeholders per row
                num_placeholders = placeholders.count("%s")
                row_placeholder = "(" + ", ".join(["%s"] * num_placeholders) + ")"

                # Process in batches
                total = len(params_list)
                for batch_start in range(0, total, batch_size):
                    batch_end = min(batch_start + batch_size, total)
                    batch = params_list[batch_start:batch_end]

                    if not batch:
                        continue

                    values_clause = ", ".join([row_placeholder] * len(batch))
                    batch_query = f"INSERT INTO {table} ({columns}) VALUES {values_clause} {conflict_clause}"

                    # Flatten params
                    flat_params = []
                    for params in batch:
                        flat_params.extend(params)

                    cursor.execute(batch_query, tuple(flat_params))
                    conn.commit()
                return

        # Fallback: execute one by one for non-INSERT queries
        for params in params_list:
            cursor.execute(converted_query, params)
        conn.commit()

    def fetchone(self, query: str, params: Tuple = ()) -> Optional[Tuple]:
        """
        Execute a query and return a single row.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Single row as tuple, or None if no results
        """
        converted_query = self.convert_placeholders(query)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(converted_query, params)
        return cursor.fetchone()

    def fetchall(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """
        Execute a query and return all rows.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of tuples
        """
        converted_query = self.convert_placeholders(query)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(converted_query, params)
        return cursor.fetchall()

    def fetchdf(self, query: str, params: Tuple = ()) -> pd.DataFrame:
        """
        Execute a query and return results as a DataFrame.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            pandas DataFrame with query results
        """
        converted_query = self.convert_placeholders(query)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(converted_query, params)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=columns)

    def bulk_insert_df(
        self,
        table: str,
        df: pd.DataFrame,
        columns: List[str],
        on_conflict: Optional[str] = None,
        conflict_columns: Optional[List[str]] = None,
        batch_size: int = 500,
    ) -> int:
        """
        Bulk insert data from a DataFrame using batched multi-row inserts.

        Uses multi-row INSERT statements for much better performance over network
        connections. Commits after each batch to avoid transaction timeouts.

        Args:
            table: Target table name
            df: DataFrame with data to insert
            columns: List of columns to insert
            on_conflict: Conflict resolution ('nothing', 'update', or None)
            conflict_columns: Columns that define uniqueness for conflict resolution
            batch_size: Number of rows per INSERT statement (default 500)

        Returns:
            Number of rows inserted
        """
        if df.empty:
            return 0

        # Filter to requested columns
        insert_df = df[columns].copy()

        conn = self._get_connection()
        cursor = conn.cursor()

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

        # Convert DataFrame to list of tuples
        rows = [tuple(row) for row in insert_df.itertuples(index=False, name=None)]
        total_rows = len(rows)
        inserted = 0

        # Process in batches for better performance
        for batch_start in range(0, total_rows, batch_size):
            batch_end = min(batch_start + batch_size, total_rows)
            batch = rows[batch_start:batch_end]

            if not batch:
                continue

            # Build multi-row VALUES clause
            # Each row: (%s, %s, %s, ...)
            row_placeholder = "(" + ", ".join(["%s"] * len(columns)) + ")"
            values_clause = ", ".join([row_placeholder] * len(batch))

            query = f"INSERT INTO {table} ({columns_str}) VALUES {values_clause}{conflict_clause}"

            # Flatten the batch into a single params list
            params = []
            for row in batch:
                params.extend(row)

            cursor.execute(query, tuple(params))
            conn.commit()  # Commit each batch to avoid long transactions
            inserted += len(batch)

        return inserted

    def get_tables(self) -> List[str]:
        """
        Get list of all tables in the database.

        Returns:
            List of table names
        """
        result = self.fetchall(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        return [row[0] for row in result]

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists.

        Args:
            table_name: Name of the table

        Returns:
            True if the table exists
        """
        result = self.fetchone(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
            """,
            (table_name,),
        )
        return result[0] > 0 if result else False

    def get_row_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.

        Args:
            table_name: Name of the table

        Returns:
            Number of rows
        """
        result = self.fetchone(f"SELECT COUNT(*) FROM {table_name}")
        return result[0] if result else 0

    @property
    def backend_name(self) -> str:
        """Return the name of the database backend."""
        return "postgres"

    @property
    def placeholder(self) -> str:
        """Return the placeholder style for PostgreSQL."""
        return "%s"

    @property
    def schema_name(self) -> str:
        """Return the default schema name for PostgreSQL."""
        return "public"

    # PostgreSQL-specific methods

    def execute_returning(self, query: str, params: Tuple = ()) -> Optional[Tuple]:
        """
        Execute an INSERT/UPDATE with RETURNING clause.

        Args:
            query: SQL query with RETURNING clause
            params: Query parameters

        Returns:
            The returned row, or None
        """
        return self.fetchone(query, params)

    def begin_transaction(self) -> Any:
        """
        Begin a manual transaction.

        Returns:
            Connection with active transaction
        """
        conn = self._get_connection()
        return conn

    def commit_transaction(self, conn: Any) -> None:
        """
        Commit a manual transaction.

        Args:
            conn: Connection from begin_transaction
        """
        conn.commit()

    def rollback_transaction(self, conn: Any) -> None:
        """
        Rollback a manual transaction.

        Args:
            conn: Connection from begin_transaction
        """
        conn.rollback()

    def get_server_version(self) -> str:
        """
        Get the PostgreSQL server version.

        Returns:
            Version string
        """
        result = self.fetchone("SELECT version()")
        return result[0] if result else "unknown"

    def vacuum_analyze(self, table_name: Optional[str] = None) -> None:
        """
        Run VACUUM ANALYZE on a table or the entire database.

        Args:
            table_name: Optional table name. If None, analyzes all tables.
        """
        conn = self._get_connection()
        # VACUUM cannot run inside a transaction block
        conn.autocommit = True
        cursor = conn.cursor()
        if table_name:
            cursor.execute(f"VACUUM ANALYZE {table_name}")
        else:
            cursor.execute("VACUUM ANALYZE")
        conn.autocommit = False
