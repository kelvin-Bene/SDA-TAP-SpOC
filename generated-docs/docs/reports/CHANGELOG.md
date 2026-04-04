# Changelog

All notable changes to the UCT Benchmark project.

## [1.2.0] - 2026-01-25

### Added

#### Dataset Management
- **Dataset Deletion** (`c8346b5`): Added ability to delete datasets from the system
- **Future Date Prevention** (`4f5913c`): Prevent dataset generation with dates in the future

#### Bug Fixes
- **INT32 Overflow Fix** (`030ac86`): Fixed INT32 overflow and NaN values in trackId database persistence

#### UI Improvements
- **Professional Redesign** (`49248db`): Redesigned frontend with professional space-themed UI
  - Dark theme optimized for satellite tracking domain
  - Improved navigation and user experience
  - Better data visualization components

### Changed
- Updated documentation to match actual implementation status
- Fixed Python version requirement references (now 3.12+)
- Corrected configuration file references (`settings.py` instead of `config.py`)

---

## [1.1.0] - 2026-01-19

### Added

#### UCT Benchmarking Enhancements

**API Enhancements (`uct_benchmark/api/apiIntegration.py`)**
- `QueryCache` class with TTL-based caching (default 15 min, max 1000 entries)
- `smart_query()` function with count-first strategy for large datasets
- `get_batch_size_for_regime()` for adaptive batch sizing by orbital regime
- New service wrappers: `queryRadarObservations()`, `queryRFObservations()`, `queryConjunctions()`, `queryManeuvers()`, `querySensorCalibration()`
- `pullComprehensiveData()` for parallel multi-service queries using asyncio
- `addManeuverFlags()` to flag observations near detected maneuvers
- API call logging with `_log_api_call()` and `get_api_metrics()`

**Downsampling Improvements (`uct_benchmark/data/dataManipulation.py`)**
- `determine_orbital_regime()` classifies LEO/MEO/GEO/HEO based on orbital elements
- `identify_tracks()` groups observations using 90-minute gap criterion
- `thin_within_tracks()` preserves first/last observations for OD quality
- `DOWNSAMPLING_PROFILES` with regime-specific parameters
- `compute_3d_coverage()` uses arc-length instead of 2D polygon area
- `downsample_by_regime()` and `downsample_preserve_tracks()` functions

**Simulation Enhancements (NEW files)**
- `uct_benchmark/simulation/atmospheric.py`:
  - `apply_atmospheric_refraction()` using Bennett's formula with corrections
  - `compute_velocity_aberration()` for classical aberration correction
  - `compute_observer_velocity()` for Earth rotation effects
- `uct_benchmark/simulation/noise_models.py`:
  - `OpticalNoiseModel`, `RadarNoiseModel`, `RFNoiseModel` dataclasses
  - Pre-defined models for GEODSS, SBSS, Commercial EO, Radar
  - `simulate_magnitude()` with Lambertian phase function
  - `is_satellite_illuminated()` for eclipse detection

**Dataset Configuration System (NEW files)**
- `uct_benchmark/config/__init__.py` - Module exports
- `uct_benchmark/config/dataset_schema.py`:
  - `EnhancedDatasetCode` class for new code format: `{OBJ}_{REG}_{EVT}_{SEN}_{QTY}_{WIN}_{VER}`
  - `load_dataset_config()` and `save_dataset_config()` for YAML support
  - `generate_dataset_metadata()` with config hash and processing stats
  - `verify_reproducibility()` for dataset verification

**Logging & Monitoring (NEW file)**
- `uct_benchmark/logging_config.py`:
  - `setup_logging()` with file rotation and retention
  - `MetricsCollector` class for API calls and processing statistics
  - `PerformanceTimer` context manager

**Configuration Dataclasses (`uct_benchmark/config.py`)**
- `APIConfig`, `DownsampleConfig`, `SimulationConfig`, `DatasetConfig`, `LoggingConfig`
- `DatasetMetrics` for run tracking
- `DOWNSAMPLING_PROFILES` dict with LEO/MEO/GEO/HEO parameters
- `SENSOR_NOISE_MODELS` dict with sensor characteristics

**Tests**
- `tests/test_api_enhancements.py` - Caching, regime detection, metrics
- `tests/test_downsampling_enhancements.py` - Track ID, preservation, coverage
- `tests/test_simulation_enhancements.py` - Refraction, aberration, noise, photometry
- `tests/test_dataset_config.py` - YAML loading, metadata generation

**Documentation**
- `docs/IMPLEMENTATION_DETAILS.md` - Comprehensive implementation details
- Updated `README.md` with usage examples

---

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

---

## Related Documentation

- [Project Status](../planning/PROJECT_STATUS.md)
- [Database Architecture](../technical/DATABASE.md)
- [Architecture Overview](../technical/ARCHITECTURE.md)
