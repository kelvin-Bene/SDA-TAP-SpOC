# Changelog

All notable changes to the UCT Benchmark Database Module.

## [1.0.0] - 2026-01-19

### Added

#### Database Module (`uct_benchmark/database/`)

- **`connection.py`** - DuckDB connection management
  - `DatabaseManager` class with thread-safe connection pooling
  - Support for file-based and in-memory databases
  - Automatic schema initialization
  - Backup and restore functionality
  - Connection context manager support
  - Database statistics and vacuum operations

- **`schema.py`** - Database schema definitions
  - `satellites` table for satellite catalog data
  - `observations` table for time-series observation data
  - `state_vectors` table for orbital state data
  - `element_sets` table for TLE data
  - `datasets` table with version tracking
  - `dataset_observations` junction table
  - `dataset_references` table for truth data
  - `event_types` and `events` tables for event labelling
  - `event_observations` junction table
  - Proper sequences for auto-incrementing IDs
  - Schema versioning via `_schema_metadata` table

- **`repository.py`** - Data access layer (Repository pattern)
  - `BaseRepository` abstract class
  - `SatelliteRepository` with CRUD operations
  - `ObservationRepository` with bulk insert and time-window queries
  - `StateVectorRepository` with epoch-based queries
  - `ElementSetRepository` for TLE management
  - `DatasetRepository` with version control and comparison
  - `EventRepository` for event labelling

- **`export.py`** - Export and import utilities
  - `export_dataset_to_json()` - Export to legacy JSON format
  - `export_observations_to_parquet()` - Parquet export with ZSTD compression
  - `import_dataset_from_json()` - Import existing JSON datasets
  - `import_parquet_to_database()` - Migrate Parquet data

- **`ingestion.py`** - Data ingestion pipeline
  - `DataIngestionPipeline` class for API integration
  - `IngestionReport` dataclass for tracking results
  - `ValidationError` for data validation failures
  - Support for UDL API ingestion
  - Data validation and normalization
  - Column name mapping for different data sources

- **`cli.py`** - Command-line interface
  - `init` - Initialize database schema
  - `status` - Show database statistics
  - `backup` - Create database backup
  - `restore` - Restore from backup
  - `export` - Export datasets to JSON/Parquet
  - `import` - Import data from files
  - `list` - List datasets with filtering
  - `verify` - Verify schema integrity
  - `vacuum` - Optimize database

- **`schema.sql`** - Standalone SQL reference file
  - Complete schema for external tools
  - Default event type seeding

#### Tests (`tests/`)

- **`test_database.py`** - Comprehensive unit tests
  - 43 test cases covering all repositories
  - Tests for DatabaseManager, all repositories, ingestion, export/import
  - Schema verification tests

### Technical Details

- **Schema Version**: 1.0.0
- **DuckDB Compatibility**: v1.4.1+
- **Python Compatibility**: 3.11+

### Architecture Decisions

1. **DuckDB over PostgreSQL/TimescaleDB**
   - Zero configuration required
   - Already a project dependency
   - Excellent for analytical queries
   - Cross-platform support

2. **Repository Pattern**
   - Clean separation of concerns
   - Easy to test and mock
   - Consistent API across data types

3. **Sequences for Auto-Increment**
   - DuckDB doesn't auto-increment like SQLite
   - Explicit sequences for state_vectors, element_sets, datasets, events

4. **Hybrid Storage Strategy**
   - DuckDB for complex queries and analytics
   - Parquet for bulk data and archival
   - JSON for API compatibility and human readability

### Known Issues

- Pytest tests may fail due to pre-existing circular import in `uct_benchmark/config/dataset_schema.py`
- This is unrelated to the database module implementation
- Standalone tests confirm all functionality works correctly

### Dependencies

No new dependencies added. Uses existing:
- `duckdb>=1.4.1`
- `pandas`
- `pyarrow` (for Parquet)

## Future Work

### Phase 2 (Planned)
- Add `use_database=True` flag to `generateDataset()`
- Automatic persistence during dataset generation
- Data migration utilities for existing files

### Phase 3 (Planned)
- Event detection hooks
- Query caching layer
- Automated daily backups
- Performance optimization
