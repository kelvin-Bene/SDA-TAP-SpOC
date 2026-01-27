"""
DuckDB connection management for UCT Benchmark.

Provides thread-safe connection pooling and database lifecycle management.
"""

import shutil
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import duckdb

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
    Manages DuckDB database connections and lifecycle.

    Provides:
    - Thread-safe connection management
    - Schema initialization
    - Backup/restore functionality
    - Connection pooling for concurrent access

    Usage:
        db = DatabaseManager()
        db.initialize()  # Create tables if they don't exist

        # Use repositories
        obs = db.observations.get_by_satellite_time_window(...)

        # Or direct SQL
        with db.connection() as conn:
            result = conn.execute("SELECT * FROM satellites").fetchdf()
    """

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        read_only: bool = False,
        in_memory: bool = False,
    ):
        """
        Initialize the database manager.

        Args:
            db_path: Path to the DuckDB file. If None, uses default path.
            read_only: If True, open database in read-only mode.
            in_memory: If True, use an in-memory database (ignores db_path).
        """
        self.in_memory = in_memory
        self.read_only = read_only

        if in_memory:
            self.db_path = ":memory:"
        else:
            self.db_path = Path(db_path) if db_path else get_db_path()
            # Ensure parent directory exists
            if isinstance(self.db_path, Path):
                self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._local = threading.local()
        self._lock = threading.Lock()
        self._initialized = False
        # Shared connection for in-memory databases (not thread-local)
        self._shared_connection: Optional[duckdb.DuckDBPyConnection] = None

        # Lazy-loaded repositories
        self._satellites: Optional["SatelliteRepository"] = None
        self._observations: Optional["ObservationRepository"] = None
        self._state_vectors: Optional["StateVectorRepository"] = None
        self._element_sets: Optional["ElementSetRepository"] = None
        self._datasets: Optional["DatasetRepository"] = None
        self._events: Optional["EventRepository"] = None

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create a connection.

        For in-memory databases, uses a shared connection across all threads
        to ensure data persists. For file-based databases, uses thread-local
        connections for better concurrency.
        """
        # For in-memory databases, use a single shared connection
        # because each new connection to :memory: creates a new empty database
        if self.in_memory:
            if self._shared_connection is None:
                config = {}
                if self.read_only:
                    config["access_mode"] = "read_only"
                self._shared_connection = duckdb.connect(":memory:", config=config)
            return self._shared_connection

        # For file-based databases, use thread-local connections
        if not hasattr(self._local, "connection") or self._local.connection is None:
            config = {}
            if self.read_only:
                config["access_mode"] = "read_only"

            self._local.connection = duckdb.connect(
                str(self.db_path) if isinstance(self.db_path, Path) else self.db_path,
                config=config,
            )
        return self._local.connection

    @contextmanager
    def connection(self):
        """
        Context manager for database connections.

        Yields:
            DuckDB connection object

        Example:
            with db.connection() as conn:
                result = conn.execute("SELECT * FROM satellites").fetchdf()
        """
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            raise

    def execute(self, query: str, params: tuple = ()) -> duckdb.DuckDBPyRelation:
        """
        Execute a SQL query.

        Args:
            query: SQL query string
            params: Query parameters for prepared statements

        Returns:
            DuckDB relation object
        """
        return self._get_connection().execute(query, params)

    def executemany(self, query: str, params_list: list) -> None:
        """
        Execute a SQL query with multiple parameter sets.

        Args:
            query: SQL query string with placeholders
            params_list: List of parameter tuples
        """
        self._get_connection().executemany(query, params_list)

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
            result = self.execute(
                "SELECT name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
            return len(result) > 0
        except Exception:
            return False

    def close(self) -> None:
        """Close database connections."""
        # Close shared connection for in-memory databases
        if self._shared_connection is not None:
            self._shared_connection.close()
            self._shared_connection = None

        # Close thread-local connection for file-based databases
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    def backup(self, backup_path: Optional[Path] = None) -> Path:
        """
        Create a backup of the database.

        Args:
            backup_path: Optional custom backup path. If None, uses default backup directory.

        Returns:
            Path to the backup file
        """
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

        Args:
            backup_path: Path to the backup file
        """
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
        self.execute("VACUUM")

    def get_statistics(self) -> dict:
        """
        Get database statistics.

        Returns:
            Dictionary with table row counts and database size
        """
        stats = {}

        # Get row counts for each table
        tables = self.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()

        for (table_name,) in tables:
            count = self.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            stats[table_name] = count

        # Get database file size
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
