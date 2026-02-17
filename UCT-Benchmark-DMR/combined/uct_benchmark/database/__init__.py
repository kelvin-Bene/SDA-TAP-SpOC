"""
Database and data storage layer for UCT Benchmark.

This module provides:
- Database adapter pattern supporting DuckDB and PostgreSQL
- Connection management for both backends
- Schema definitions for observations, state vectors, TLEs, and datasets
- Repository pattern for data access
- Data ingestion pipeline from external APIs
- Export utilities for JSON/Parquet formats

Usage:
    from uct_benchmark.database import DatabaseManager

    # DuckDB (default, for local development)
    db = DatabaseManager()
    db.initialize()

    # PostgreSQL/Supabase (for production)
    db = DatabaseManager(
        backend="postgres",
        database_url="postgresql://user:pass@host:5432/db"
    )
    db.initialize()

    # Access data through repositories
    observations = db.observations.get_by_satellite_time_window(
        sat_no=25544,
        start_time=datetime(2025, 1, 1),
        end_time=datetime(2025, 1, 7)
    )
"""

from .adapters import (
    DatabaseAdapter,
    DuckDBAdapter,
    create_adapter,
    create_test_adapter,
    get_database_backend,
)
from .connection import DatabaseManager, get_db_path
from .export import (
    export_dataset_to_json,
    export_observations_to_parquet,
    import_dataset_from_json,
)
from .ingestion import DataIngestionPipeline, IngestionReport
from .migration import DataMigration, MigrationReport, migrate_existing_data
from .repository import (
    BaseRepository,
    DatasetRepository,
    ElementSetRepository,
    EventRepository,
    ObservationRepository,
    SatelliteRepository,
    StateVectorRepository,
)
from .schema import (
    SCHEMA_VERSION,
    get_schema_version,
    initialize_schema,
    verify_schema,
)

__all__ = [
    # Adapters
    "DatabaseAdapter",
    "DuckDBAdapter",
    "create_adapter",
    "create_test_adapter",
    "get_database_backend",
    # Connection management
    "DatabaseManager",
    "get_db_path",
    # Repositories
    "BaseRepository",
    "SatelliteRepository",
    "ObservationRepository",
    "StateVectorRepository",
    "ElementSetRepository",
    "DatasetRepository",
    "EventRepository",
    # Schema
    "initialize_schema",
    "verify_schema",
    "get_schema_version",
    "SCHEMA_VERSION",
    # Export/Import
    "export_dataset_to_json",
    "export_observations_to_parquet",
    "import_dataset_from_json",
    # Ingestion
    "DataIngestionPipeline",
    "IngestionReport",
    # Migration
    "DataMigration",
    "MigrationReport",
    "migrate_existing_data",
]
