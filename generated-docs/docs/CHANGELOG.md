# Changelog

All notable changes to the UCT Benchmark project.

## [2.1.0] - 2026-02-02

### Merged from Kelvin's Branch

- **Repository reorganization**: Moved `docs/` to `generated-docs/docs/` for consistency
- **Security**: Removed hardcoded credentials from `start_supabase.bat`
- **Code Quality**: Null-safety fixes with `or` fallback pattern in datasets.py
- **Better logging**: Improved rollback error logging in workers.py
- **PostgreSQL**: Auto SSL detection for remote hosts, 60s socket timeout
- **Frontend**: Null-safety for submission results in RecentSubmissions and MySubmissionsPage
- **Testing**: Added skip conditions for orekit/jpype dependencies

### New Features

- **Data Source Status Indicator**: Shows credential configuration status in Dataset Generator UI
- **Pre-Generation Validation**: Checks required credentials before allowing dataset generation
- **Smart Defaults**: "Quick Test" preset works without UDL credentials (uses cached/sample data)
- **Toast Notifications**: Replaced `alert()` with consistent toast UI for errors and success messages
- **COMPLETE Enum**: Added `DatasetStatus.COMPLETE` for Supabase compatibility

### Documentation

- Added Credentials API documentation to BACKEND_API.md
- Added UCTP Lab API documentation to BACKEND_API.md
- Added AUTH_SETUP.md guide for authentication configuration
- Added UTILITIES.md (from Kelvin's branch)

---

## [2.0.0] - 2026-01-27

### Added

#### Supabase / PostgreSQL Migration

Full migration from DuckDB-only to dual-backend (DuckDB + PostgreSQL/Supabase) with feature-flagged auth, audit logging, and production data tracking.

**Database Abstraction Layer (`uct_benchmark/database/`)**
- `backend_interface.py` — `DatabaseBackendInterface` abstract base class with `execute()`, `executemany()`, `execute_df_insert()`, `connection()`, `initialize_schema()`, `close()`
- `duckdb_backend.py` — DuckDB implementation extracted from `connection.py`, implements the interface with thread-local connections and register/unregister bulk insert
- `postgres_backend.py` — PostgreSQL implementation using `psycopg_pool.ConnectionPool`, with placeholder conversion (`?` to `%s`), `INSERT OR REPLACE` to `ON CONFLICT DO UPDATE`, `JSON` to `JSONB`
- `schema_postgres.py` — PostgreSQL-adapted schema (v2.0.0) with JSONB, TIMESTAMPTZ, 6 new production tables
- `connection.py` — Refactored `DatabaseManager` to delegate to backend interface via `_resolve_backend()` factory; public API unchanged

**Backend Auth Module (`backend_api/auth/`)**
- `middleware.py` — `verify_jwt()` decodes Supabase JWTs using `python-jose` HS256
- `dependencies.py` — FastAPI dependencies: `get_current_user()`, `require_auth()`, `require_admin()`
- `models.py` — Pydantic models: `LoginRequest`, `SignupRequest`, `UserProfile`, `TokenResponse`
- `routers/auth.py` — Auth endpoints: `/signup`, `/login`, `/logout`, `/me`, `PATCH /me`

**Audit & Logging (`backend_api/middleware/`, `backend_api/services/`)**
- `middleware/audit.py` — `AuditMiddleware` captures POST/PUT/PATCH/DELETE to `api_call_log`
- `middleware/query_logging.py` — `QueryLoggingMiddleware` logs slow requests (>500ms) to `system_log`
- `services/audit_service.py` — `log_api_call()`, `log_audit_event()`, `log_credential_access()`, `log_system_event()`

**Database-backed Job Manager (`backend_api/jobs/`)**
- `db_job_manager.py` — `DatabaseJobManager` persists jobs in the `jobs` table for PostgreSQL mode; same API as in-memory `JobManager`
- `__init__.py` — `init_job_manager()` selects backend based on `DB_BACKEND` config

**Centralized Configuration (`backend_api/config.py`)**
- `AppConfig` dataclass with `DatabaseBackend` enum (`duckdb` | `postgres`)
- Reads: `DB_BACKEND`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `DATABASE_URL`, `PG_POOL_MIN/MAX`, `AUTH_ENABLED`, `CORS_ORIGINS`
- Singleton pattern with `get_config()` / `reset_config()`

**PostgreSQL Schema — 6 New Production Tables**
- `users` — UUID PK, `auth_user_id` UNIQUE for Supabase Auth, email, username, organization, role, timestamps
- `audit_log` — action, resource_type, resource_id, details JSONB, ip_address
- `api_call_log` — method, path, status_code, duration_ms, request/response body size
- `query_log` — query_hash, query_text, duration_ms, rows_affected, source
- `credential_access_log` — service_name, action, source, success
- `system_log` — level, component, message, details JSONB

**SQL Migration**
- `backend_api/db/migrations/001_initial_schema.sql` — Full 26-table PostgreSQL migration with indexes, foreign keys, RLS policies, seed data

**Data Migration Script**
- `scripts/migrate_duckdb_to_postgres.py` — CLI script to migrate existing DuckDB data to PostgreSQL with `--batch-size`, `--dry-run`, `--verify`, FK-safe table ordering, JSON-to-JSONB conversion, sequence reset

**Frontend Supabase Integration**
- `frontend/src/lib/supabase.ts` — Conditional Supabase client (null when not configured)
- `frontend/src/hooks/useAuth.ts` — Login/signup/logout with Supabase SDK + API fallback
- `frontend/src/hooks/useRealtimeJobs.ts` — Supabase Realtime subscriptions for job progress
- `frontend/src/components/auth/AuthProvider.tsx` — Syncs Supabase auth state with Zustand store
- `frontend/src/components/auth/ProtectedRoute.tsx` — Route guard controlled by `VITE_AUTH_ENABLED`
- Updated `App.tsx`, `LoginPage.tsx`, `ProfilePage.tsx`, `api/client.ts`

**Tests (89 new tests)**
- `test_config.py` (8) — Config singleton, env var parsing, defaults
- `test_auth_middleware.py` (12) — JWT verification, auth dependencies, role guards
- `test_audit_service.py` (17) — All 4 logging functions, DB unavailable handling
- `test_db_job_manager.py` (34) — Full CRUD, persistence, factory, filters
- `test_query_logging.py` (6) — Slow request logging, threshold, skip conditions
- `tests/test_data_migration.py` (32) — Migration script: JSON conversion, table ordering, batch processing

### Changed
- `pyproject.toml` — Added: `psycopg[binary]>=3.1.0`, `psycopg-pool>=3.2.0`, `python-jose[cryptography]>=3.3.0`
- `frontend/package.json` — Added: `@supabase/supabase-js@^2.45.0`
- `.env.example` — Added DB_BACKEND, Supabase, PostgreSQL, and auth sections
- `backend_api/main.py` — Auth router, CORS from config, audit middleware registration
- `backend_api/routers/__init__.py` — Added `auth` module

### Architecture Decisions
- **Feature-flagged**: `DB_BACKEND=duckdb` (default) preserves all existing behavior; `DB_BACKEND=postgres` enables Supabase/PostgreSQL
- **AUTH_ENABLED=false** (default): All endpoints work without tokens; `true` requires valid Supabase JWT
- **Backend interface pattern**: All database access goes through `DatabaseBackendInterface`, enabling runtime backend switching
- **Placeholder conversion**: `?` to `%s` at runtime in PostgreSQL backend; safe because no SQL uses `?` inside string literals
- **Audit never breaks requests**: All logging functions swallow exceptions

---

## [1.2.0] - 2026-01-28

### Fixed

- **Critical bug in `readData.py:28`**: Dataset `obTime` was incorrectly set from `ref_obs["obTime"]` instead of `dataset["obTime"]`, causing data corruption
- **Critical bug in `readData.py:31`**: The `uctp_output_path` parameter was ignored; function always read from hardcoded `./data/uctp_output.json`
- **Typo in `binaryMetrics.py:112`**: Column name "Specifcity" corrected to "Specificity"
- **Silent exceptions** in `dataManipulation.py` and `workers.py` now log warnings with context

### Added

- **New utility module `uct_benchmark/utils/orbital.py`**: Consolidated `determine_orbital_regime()` function (was duplicated in `apiIntegration.py` and `dataManipulation.py`)
- **New utility module `uct_benchmark/utils/datetime_utils.py`**: Consolidated datetime parsing with `parse_datetime()` and `ensure_datetime_column()` functions
- **Shared API response handler `_check_api_response()`** in `apiIntegration.py` for consistent error handling
- **Column constants** (`STATE_COLUMNS`, `POSITION_COLUMNS`, `VELOCITY_COLUMNS`) in `stateMetrics.py`
- **New tests**: `test_read_data.py`, `test_orbital_utils.py`, `test_datetime_utils.py`
- **Test for Specificity spelling** in `test_evaluation.py`

### Changed

- **`generateCov.py`**: Replaced `print()` with `logger.warning()` for error logging
- **Error handling improved**: Silent `except: continue` blocks now log warnings with satellite/row context
- **Function naming**: `_supressWarn()` renamed to `_suppress_warnings()` (backward-compatible alias retained)

### Removed

- **Unused import**: `urllib3` removed from `binaryMetrics.py`
- **Dead code**: Commented imports and code removed from `Evaluation.py`
- **Duplicate encoding declaration** in `generateCov.py` (was `# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-`)

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

### Completed in v2.0.0
- ~~Data migration utilities for existing files~~ (see `scripts/migrate_duckdb_to_postgres.py`)
- ~~Query caching layer~~ (see `QueryCache` in API and query logging in middleware)

### Planned
- Add `use_database=True` flag to `generateDataset()` for automatic persistence
- Event detection hooks
- Automated daily backups
- Performance optimization for bulk PostgreSQL inserts
- Supabase Realtime for live leaderboard updates
- Row-Level Security (RLS) policy enforcement per user role
