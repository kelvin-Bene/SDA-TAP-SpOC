"""
Database connection management for UCT Benchmark.

Provides thread-safe connection pooling and database lifecycle management.
Supports both DuckDB (default) and PostgreSQL (Supabase) backends via
the DB_BACKEND feature flag.
"""

import shutil
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

import pandas as pd

if TYPE_CHECKING:
    from .backend_interface import DatabaseBackendInterface
    from .repository import (
        DatasetRepository,
        ElementSetRepository,
        EventRepository,
        ObservationRepository,
        SatelliteRepository,
        StateVectorRepository,
    )

# Default database paths
DEFAULT_DB_NAME = "uct_benchmark.duckdb"


def get_db_path(db_name: Optional[str] = None) -> Path:
    """
    Get the default database file path.

    Uses the DATA_DIR from config if available, otherwise uses a local directory.

    Args:
        db_name: Optional custom database name

    Returns:
        Path to the database file
    """
    try:
        from uct_benchmark.settings import DATA_DIR

        base_dir = DATA_DIR / "database"
    except ImportError:
        base_dir = Path(__file__).parent.parent.parent / "data" / "database"

    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / (db_name or DEFAULT_DB_NAME)


def _resolve_backend(
    backend: Optional[str],
    db_path: Optional[str | Path],
    read_only: bool,
    in_memory: bool,
) -> "DatabaseBackendInterface":
    """Create the appropriate backend based on configuration.

    Args:
        backend: Explicit backend name ("duckdb" or "postgres"), or None to auto-detect
        db_path: Database file path (DuckDB only)
        read_only: Open in read-only mode (DuckDB only)
        in_memory: Use in-memory database (DuckDB only)

    Returns:
        A DatabaseBackendInterface implementation
    """
    if backend is None:
        try:
            from backend_api.config import get_config

            backend = get_config().db_backend.value
        except Exception:
            backend = "duckdb"

    if backend == "postgres":
        from backend_api.config import get_config

        from .postgres_backend import PostgresBackend

        config = get_config()
        if not config.postgres_url:
            raise ValueError(
                "PostgreSQL backend selected but DATABASE_URL / SUPABASE_DB_URL is not set. "
                "Set the DATABASE_URL environment variable to your PostgreSQL connection string."
            )
        return PostgresBackend(
            connection_url=config.postgres_url,
            min_size=config.postgres_pool_min,
            max_size=config.postgres_pool_max,
        )
    else:
        from .duckdb_backend import DuckDBBackend

        return DuckDBBackend(db_path=db_path, read_only=read_only, in_memory=in_memory)


class DatabaseManager:
    """
    Manages database connections and lifecycle.

    Supports both DuckDB (default, local development) and PostgreSQL
    (production, Supabase) backends. The backend is selected via the
    DB_BACKEND environment variable or the `backend` constructor parameter.

    Provides:
    - Thread-safe connection management
    - Schema initialization
    - Backup/restore functionality (DuckDB only)
    - Connection pooling for concurrent access
    - Backend-agnostic bulk insert via bulk_insert_df()

    Usage:
        db = DatabaseManager()          # DuckDB (default)
        db = DatabaseManager(backend="postgres")  # PostgreSQL
        db.initialize()

        # Use repositories
        obs = db.observations.get_by_satellite_time_window(...)

        # Or direct SQL
        result = db.execute("SELECT * FROM satellites").fetchdf()
    """

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        read_only: bool = False,
        in_memory: bool = False,
        backend: Optional[str] = None,
    ):
        """
        Initialize the database manager.

        Args:
            db_path: Path to the DuckDB file. If None, uses default path. Ignored for PostgreSQL.
            read_only: If True, open database in read-only mode. DuckDB only.
            in_memory: If True, use an in-memory database. DuckDB only.
            backend: Explicit backend ("duckdb" or "postgres"). If None, reads DB_BACKEND env var.
        """
        self.in_memory = in_memory
        self.read_only = read_only
        self._backend_name = backend

        # Resolve the backend implementation
        self._backend: "DatabaseBackendInterface" = _resolve_backend(
            backend=backend,
            db_path=db_path,
            read_only=read_only,
            in_memory=in_memory,
        )

        # Set db_path for backward compatibility
        if hasattr(self._backend, "db_path"):
            self.db_path = self._backend.db_path
        else:
            self.db_path = "<postgres>"

        self._lock = threading.Lock()
        self._initialized = False

        # Lazy-loaded repositories
        self._satellites: Optional["SatelliteRepository"] = None
        self._observations: Optional["ObservationRepository"] = None
        self._state_vectors: Optional["StateVectorRepository"] = None
        self._element_sets: Optional["ElementSetRepository"] = None
        self._datasets: Optional["DatasetRepository"] = None
        self._events: Optional["EventRepository"] = None

    def _get_connection(self):
        """Get a raw connection from the backend.

        For DuckDB: returns a thread-local DuckDB connection.
        For PostgreSQL: not recommended — use execute() or connection() instead.
        """
        if hasattr(self._backend, "_get_connection"):
            return self._backend._get_connection()
        raise NotImplementedError(
            "Direct connection access is not supported for the PostgreSQL backend. "
            "Use db.execute() or db.connection() instead."
        )

    @contextmanager
    def connection(self):
        """
        Context manager for database connections.

        Yields:
            Database connection object

        Example:
            with db.connection() as conn:
                result = conn.execute("SELECT * FROM satellites").fetchdf()
        """
        with self._backend.connection() as conn:
            yield conn

    def execute(self, query: str, params: tuple = ()) -> Any:
        """
        Execute a SQL query.

        Args:
            query: SQL query string (use ? placeholders — automatically
                   converted to %s for PostgreSQL)
            params: Query parameters for prepared statements

        Returns:
            Result object with fetchone(), fetchall(), fetchdf() methods
        """
        return self._backend.execute(query, params)

    def executemany(self, query: str, params_list: list) -> None:
        """
        Execute a SQL query with multiple parameter sets.

        Args:
            query: SQL query string with placeholders
            params_list: List of parameter tuples
        """
        self._backend.executemany(query, params_list)

    def bulk_insert_df(
        self,
        table: str,
        df: pd.DataFrame,
        columns: List[str],
        conflict_clause: str = "",
    ) -> int:
        """
        Bulk insert from a DataFrame using the backend-optimal method.

        For DuckDB: uses register/unregister pattern.
        For PostgreSQL: uses executemany with ON CONFLICT support.

        Args:
            table: Target table name
            df: DataFrame containing the data
            columns: Column names to insert
            conflict_clause: ON CONFLICT clause

        Returns:
            Number of rows inserted
        """
        return self._backend.execute_df_insert(table, df, columns, conflict_clause)

    def initialize(self, force: bool = False) -> None:
        """
        Initialize the database schema.

        Creates all tables if they don't exist.

        Args:
            force: If True, drop and recreate all tables
        """
        with self._lock:
            self._backend.initialize_schema(force=force)
            self._initialized = True

    def is_initialized(self) -> bool:
        """Check if the database schema has been initialized."""
        if self._initialized:
            return True
        return self._backend.is_initialized()

    def close(self) -> None:
        """Close database connections."""
        self._backend.close()

    def backup(self, backup_path: Optional[Path] = None) -> Path:
        """
        Create a backup of the database (DuckDB only).

        Args:
            backup_path: Optional custom backup path.

        Returns:
            Path to the backup file
        """
        if not hasattr(self._backend, "db_path"):
            raise ValueError("Backup is only supported for the DuckDB backend")

        if self.in_memory:
            raise ValueError("Cannot backup an in-memory database")

        if backup_path is None:
            backup_dir = self.db_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"uct_benchmark_{timestamp}.duckdb"

        self.close()
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    def restore(self, backup_path: Path) -> None:
        """
        Restore the database from a backup (DuckDB only).

        Args:
            backup_path: Path to the backup file
        """
        if not hasattr(self._backend, "db_path"):
            raise ValueError("Restore is only supported for the DuckDB backend")

        if self.in_memory:
            raise ValueError("Cannot restore to an in-memory database")

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        self.close()
        shutil.copy2(backup_path, self.db_path)

    def vacuum(self) -> None:
        """Optimize the database by reclaiming unused space."""
        self.execute("VACUUM")

    def get_statistics(self) -> dict:
        """
        Get database statistics.

        Returns:
            Dictionary with table row counts and database size
        """
        stats = {}
        schema = self._backend.schema_name if hasattr(self._backend, "schema_name") else "main"

        tables = self.execute(
            f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}'"
        ).fetchall()

        for (table_name,) in tables:
            count = self.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            stats[table_name] = count

        if not self.in_memory and isinstance(self.db_path, Path):
            if self.db_path.exists():
                stats["_file_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)

        return stats

    # Repository accessors (lazy loading)
    @property
    def satellites(self) -> "SatelliteRepository":
        """Get the satellite repository."""
        if self._satellites is None:
            from .repository import SatelliteRepository

            self._satellites = SatelliteRepository(self)
        return self._satellites

    @property
    def observations(self) -> "ObservationRepository":
        """Get the observation repository."""
        if self._observations is None:
            from .repository import ObservationRepository

            self._observations = ObservationRepository(self)
        return self._observations

    @property
    def state_vectors(self) -> "StateVectorRepository":
        """Get the state vector repository."""
        if self._state_vectors is None:
            from .repository import StateVectorRepository

            self._state_vectors = StateVectorRepository(self)
        return self._state_vectors

    @property
    def element_sets(self) -> "ElementSetRepository":
        """Get the element set repository."""
        if self._element_sets is None:
            from .repository import ElementSetRepository

            self._element_sets = ElementSetRepository(self)
        return self._element_sets

    @property
    def datasets(self) -> "DatasetRepository":
        """Get the dataset repository."""
        if self._datasets is None:
            from .repository import DatasetRepository

            self._datasets = DatasetRepository(self)
        return self._datasets

    @property
    def events(self) -> "EventRepository":
        """Get the event repository."""
        if self._events is None:
            from .repository import EventRepository

            self._events = EventRepository(self)
        return self._events

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        return f"DatabaseManager(db_path={self.db_path!r}, read_only={self.read_only})"
