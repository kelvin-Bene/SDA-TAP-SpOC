"""
Database connection management for UCT Benchmark.

Provides thread-safe connection management and database lifecycle operations.
Supports both DuckDB (local development) and PostgreSQL (Supabase production)
through the adapter pattern.
"""

import shutil
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from .adapters import DatabaseAdapter, create_adapter

if TYPE_CHECKING:
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


class DatabaseManager:
    """
    Manages database connections and lifecycle.

    Provides:
    - Unified interface for DuckDB and PostgreSQL
    - Thread-safe connection management
    - Schema initialization
    - Backup/restore functionality (DuckDB only)
    - Repository access

    Usage:
        # DuckDB (default)
        db = DatabaseManager()
        db.initialize()

        # PostgreSQL/Supabase
        db = DatabaseManager(backend='postgres', database_url='postgresql://...')
        db.initialize()

        # Use repositories
        obs = db.observations.get_by_satellite_time_window(...)

        # Or direct SQL via adapter
        with db.connection() as conn:
            result = db.adapter.fetchdf("SELECT * FROM satellites")
    """

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        read_only: bool = False,
        in_memory: bool = False,
        backend: Optional[str] = None,
        database_url: Optional[str] = None,
        pool_min: Optional[int] = None,
        pool_max: Optional[int] = None,
    ):
        """
        Initialize the database manager.

        Args:
            db_path: Path to the DuckDB file. If None, uses default path. (DuckDB only)
            read_only: If True, open database in read-only mode. (DuckDB only)
            in_memory: If True, use an in-memory database. (DuckDB only)
            backend: Database backend ('duckdb' or 'postgres'). If None, auto-detects.
            database_url: PostgreSQL connection string. (PostgreSQL only)
            pool_min: Minimum connection pool size. (PostgreSQL only)
            pool_max: Maximum connection pool size. (PostgreSQL only)
        """
        # Store config for backup/restore
        self.in_memory = in_memory
        self.read_only = read_only

        # Determine db_path for DuckDB
        if in_memory:
            self.db_path: str | Path = ":memory:"
        elif db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = get_db_path()

        # Create the appropriate adapter
        self._adapter = create_adapter(
            backend=backend,
            db_path=self.db_path if not in_memory else None,
            in_memory=in_memory,
            read_only=read_only,
            database_url=database_url,
            pool_min=pool_min,
            pool_max=pool_max,
        )

        self._lock = threading.Lock()
        self._initialized = False

        # Lazy-loaded repositories
        self._satellites: Optional["SatelliteRepository"] = None
        self._observations: Optional["ObservationRepository"] = None
        self._state_vectors: Optional["StateVectorRepository"] = None
        self._element_sets: Optional["ElementSetRepository"] = None
        self._datasets: Optional["DatasetRepository"] = None
        self._events: Optional["EventRepository"] = None

    @property
    def adapter(self) -> DatabaseAdapter:
        """Get the underlying database adapter."""
        return self._adapter

    @property
    def backend(self) -> str:
        """Get the database backend name ('duckdb' or 'postgres')."""
        return self._adapter.backend_name

    @contextmanager
    def connection(self):
        """
        Context manager for database connections.

        Yields:
            Database connection object (backend-specific)

        Example:
            with db.connection() as conn:
                # Use connection directly (backend-specific)
                ...
        """
        with self._adapter.connection() as conn:
            yield conn

    def execute(self, query: str, params: tuple = ()) -> Any:
        """
        Execute a SQL query.

        Args:
            query: SQL query string (uses '?' placeholders)
            params: Query parameters for prepared statements

        Returns:
            Query result (backend-specific)
        """
        return self._adapter.execute(query, params)

    def executemany(self, query: str, params_list: list) -> None:
        """
        Execute a SQL query with multiple parameter sets.

        Args:
            query: SQL query string with placeholders
            params_list: List of parameter tuples
        """
        self._adapter.executemany(query, params_list)

    def initialize(self, force: bool = False) -> None:
        """
        Initialize the database schema.

        Creates all tables if they don't exist.

        Args:
            force: If True, drop and recreate all tables
        """
        from .schema import initialize_schema

        with self._lock:
            initialize_schema(self, force=force)
            self._initialized = True

    def is_initialized(self) -> bool:
        """Check if the database schema has been initialized."""
        if self._initialized:
            return True

        try:
            tables = self._adapter.get_tables()
            return len(tables) > 0
        except Exception:
            return False

    def close(self) -> None:
        """Close database connections."""
        self._adapter.close()

    def backup(self, backup_path: Optional[Path] = None) -> Path:
        """
        Create a backup of the database.

        Note: Only supported for DuckDB file-based databases.

        Args:
            backup_path: Optional custom backup path. If None, uses default backup directory.

        Returns:
            Path to the backup file

        Raises:
            ValueError: If using in-memory database or PostgreSQL
        """
        if self.backend != "duckdb":
            raise ValueError("Backup is only supported for DuckDB databases")

        if self.in_memory:
            raise ValueError("Cannot backup an in-memory database")

        if backup_path is None:
            backup_dir = self.db_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"uct_benchmark_{timestamp}.duckdb"

        # Close any open connections before backup
        self.close()

        # Copy the database file
        shutil.copy2(self.db_path, backup_path)

        return backup_path

    def restore(self, backup_path: Path) -> None:
        """
        Restore the database from a backup.

        Note: Only supported for DuckDB file-based databases.

        Args:
            backup_path: Path to the backup file

        Raises:
            ValueError: If using in-memory database or PostgreSQL
            FileNotFoundError: If backup file doesn't exist
        """
        if self.backend != "duckdb":
            raise ValueError("Restore is only supported for DuckDB databases")

        if self.in_memory:
            raise ValueError("Cannot restore to an in-memory database")

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Close any open connections
        self.close()

        # Restore from backup
        shutil.copy2(backup_path, self.db_path)

    def vacuum(self) -> None:
        """Optimize the database by reclaiming unused space."""
        if self.backend == "duckdb":
            self._adapter.vacuum()
        else:
            self._adapter.vacuum_analyze()

    def get_statistics(self) -> dict:
        """
        Get database statistics.

        Returns:
            Dictionary with table row counts and database size
        """
        stats = {}

        # Get row counts for each table
        tables = self._adapter.get_tables()
        for table_name in tables:
            stats[table_name] = self._adapter.get_row_count(table_name)

        # Get database file size (DuckDB only)
        if self.backend == "duckdb" and hasattr(self._adapter, "get_file_size_mb"):
            file_size = self._adapter.get_file_size_mb()
            if file_size is not None:
                stats["_file_size_mb"] = file_size

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

    # Legacy DuckDB-specific access for backward compatibility
    def _get_connection(self):
        """
        Get the underlying DuckDB connection.

        Deprecated: Use adapter methods or connection() context manager instead.
        This method exists for backward compatibility with existing repository code.
        """
        if self.backend == "duckdb":
            return self._adapter._get_connection()
        else:
            raise NotImplementedError(
                "_get_connection() is only available for DuckDB. "
                "Use adapter methods for portable code."
            )

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        if self.backend == "duckdb":
            return f"DatabaseManager(backend='duckdb', db_path={self.db_path!r}, read_only={self.read_only})"
        else:
            return f"DatabaseManager(backend='postgres')"
