# Changelog

All notable changes to the UCT Benchmark project.

## [2.0.2] - 2026-04-20

### Vision Alignment (Apr 16)

- **Composite score breakdown** (`f2fdd50`): ResultsPage shows Binary × w1 + State × w2 + Residual × w3 with per-component bars, state-source badge (Mahalanobis p-score vs. position-RMS heuristic), and fallback banner when Orekit unavailable. Closes the last gap from Lewis's Feb 19 "you lose points there" philosophy — users now *see* why a score dropped.
- **Leaderboard composite tooltip**: train/val/test split breakdown on hover, noting only test ranks count.
- **Rank ordering**: ResultsPage ORDER BY now mirrors `COALESCE(test_composite_score, composite_score, f1_score)`.
- **3D globe integration**: `OrbitViewer` on DatasetDetailPage (owner+admin gated per Louis's Apr 9 answer-key separation), ResultsPage (own-submissions), LandingPage hero (desktop-only static fixture). Backend: `GET /datasets/{id}/reference-orbits`, `GET /submissions/{id}/predictions` with Orekit + disk cache.
- **Event filter DB-first**: `generateDataset()` queries persisted events before TLE heuristic; new `EventRepository.find_events_in_window`.
- **Docs sync**: C/A object-filter thresholds (10 km / 10 m/s / 0.00833° per Louis's `UCT Labelling.xlsx`, Apr 8 recalibration) updated in `VISION_ALIGNMENT_AUDIT.md` and `TRANSCRIPT_ALIGNMENT_PLAN.md`.

### QA Prod Findings 2026-04-17 (`559db9d`, `21e4699`, `a5eda35`)

- **C1 (Critical, Fixed)**: evaluation pipeline failed on every post-Apr-9 dataset. Backend exposes `has_reference_orbits` via EXISTS subquery; frontend gates the Submit dropdown on the boolean instead of the date-only `EVAL_CUTOFF_MS` heuristic.
- **H1 (High, Fixed)**: `submission.error_message` now persisted on job failure so the ResultsPage banner surfaces the real error text.
- **L1 (Fixed)**: `WindowEvaluation` attribute typos (`avg_orbital_coverage` → `avg_coverage`, `avg_track_gap` → `avg_track_gap_periods`).
- **L4 (Fixed)**: `DatabaseJobManager.list_jobs` merges in-memory + DB rows for forensic visibility.
- **Backfill tool** (`a5eda35`): `scripts/backfill_dataset_references.py` to repair datasets missing reference rows without full regeneration.

See `docs/reports/QA_PROD_RUN_2026-04-17.md` for the full finding list + `## Resolution (2026-04-21)` section.

### Eval Pipeline Hardening — Chain of 8 Latent Bugs (Apr 17–18)

Surfaced by `scripts/seed_demo_submission.py` (new helper — see below) pushing farther through the pipeline than any prior real submission:

- `f62a197` guard `orbitAssociation` against infeasible cost matrix.
- `20295f2` guard empty-DataFrame sort after infeasible-matrix fallback.
- `d0a222d` fail-fast epoch sanity check on submission epochs.
- `3d328a3` / `092449e` rebuild SV-mode associated DataFrame via iloc-slice.
- `16db3b5` serialize stateMetrics + residualMetrics SV-mode pools.
- `6661622` serial cost-column computation in SV mode to unblock Orekit.
- `6d8ebdd` convert truth covariance from 21-element lower-triangular to 6×6.
- `c27ae8f` / `b35c2da` / `6f4a4f1` force float64 and guarantee 6×6 shape on truth, UCTP, and `associated_orbits` covariances.
- `f3d522b` convert NaN/Inf to null in results JSON serialization.

### Deploy Hygiene (Apr 17)

- `51b56ba` / `e959d09` / `d9c38c3` `orekit-data.zip` un-LFS'd + tracked normally so Railway Docker build can `COPY` it.
- `487f078` / `cc2b506` Railway CLI deploys stage frontend dir in `/tmp` with empty `.railwayignore` to escape repo-root `.gitignore`.
- `236dea0` disable CDN caching on SPA `index.html`.

### Frontend Globe Rescue (Apr 18–19)

- `5b4276e` / `41bcd74` Cesium entity graphics marshaling (revert plain-object props to `Graphics` class instances).
- `7cbf1bd` drop `creditContainer={undefined}` Viewer prop.
- **`12c2f2b` pin `resium` to `1.18.3`** — 1.18.4+ targets React 19 internals and silently crashes hidden behind ErrorBoundary/SVG fallback. Do not bump until the React 18 → 19 migration.

### Tooling

- **`scripts/seed_demo_submission.py`** (`0879bdd`): realistic demo submission helper — fetches truth state + observation IDs, adds Gaussian noise, builds a valid UCTP record, posts via authenticated API, polls to terminal. Produced submission 44 (`composite_score=1.0`) — first completed submission in prod history — and surfaced the 8-bug chain above.

### Testing

- `3ea3c64` backend regression coverage for QA C1, H1, L4.
- `84bd0d3` fix e2e M1/M2/M5/M6 + harden C1/H1 guardrails.
- `5c88360` / `c5f64af` / `dea79aa` / `40c4995` / `e814720` prod-spec flake hardening.

### Production Validation

After the v2.0.2 batch landed, end-to-end verification on the prod deploy:
- **79/79 e2e specs green** on desktop-auth + mobile-safari-auth.
- **First completed submission in prod history**: submission 44 against dataset 158, composite_score = 1.0.
- **Full flow confirmed**: generate → download → submit → evaluate → view results → leaderboard.

---

## [2.0.1] - 2026-04-09

### Vision Alignment
- **Answer-key separation**: Moved answer keys to separate download-protected endpoint per Louis's Apr 9 feedback
- **Field minimization**: Reduced dataset download payload to only fields needed by UCTP algorithms
- **HEO coverage scoring**: Fixed coverage threshold calculations for HEO regime
- **Regime classification**: Fixed combo regime pipeline for multi-regime datasets
- **Coverage thresholds**: Aligned with Louis's transcript specifications (LEO 0.0213%, MEO 0.0449%, GEO 41.656%, HEO 20%)
- **HAMR filtering**: Corrected High Area-to-Mass Ratio object filtering logic
- **Regime combo codes**: Exposed all 10 regime combination codes (LMO, LGO, LHO, MGO, MHO, GHO, LMG, LMH, LGH, MGH) in frontend UI and validator

### UCT Challenges (CTF Framework)
- **Physical noise pipeline** (`cfa687b`): Realistic noise models for simulated observations (challenge #4)
- **Orbit-association thresholds** (`53c41a3`): Tightened proximity thresholds (challenge #1)
- **Sensor calibration** (`b5a6ea0`): Synthetic per-sensor bias generator (challenge #10)
- **Train/test split** (`ccc10e7`): CTF train/validation/test dataset stratification (LLNL methodology)
- **Maneuvering-during-gap** (`f969b7e`): Challenge scenario + shared backend infrastructure

### Security & Testing
- Resolved 22 pre-existing test failures across the test suite
- Security hardening: SQL injection fixes, IDOR vulnerability closures, auth consolidation
- CI gating improvements and audit finding remediation
- Retired PATCH /feedback endpoint until cross-project schema sync

---

## [2.0.0] - 2026-04-05

### Major Release

#### Rebrand & UI Overhaul
- **Rebrand**: Renamed SpOC → UCT Benchmark, Space Operations Command → Combat Forces Command
- **Military-grade aesthetic**: USSF-aligned dark theme with professional space domain styling
- **CFC + SDA TAP Lab logos**: Replaced orbital icon in header with organizational branding
- **Landing page**: New default route with "Try Demo" button for unauthenticated users

#### Production Deployment
- Full production deployment on Railway with Docker containerization
- PostgreSQL/Supabase backend for multi-user production use
- NGINX reverse proxy with security headers and CSP
- GitHub Actions CI/CD auto-deploy on push to master

#### Features
- **Real dataset statistics charts** on dashboard
- **Bug report feedback widget** with browser context capture
- **Password visibility toggle** on login
- **App versioning**: Display version in UI, auto-include in bug reports
- **Dataset filter on leaderboard** page
- **Per-user API tokens**: Encrypted UDL/ESA credential storage
- **3-tier auth**: Admin, authenticated, and public access levels

#### Infrastructure
- Supabase/PostgreSQL migration with dual-backend support
- Database retry logic with connection recovery
- Rate limiting with slowapi
- Comprehensive audit logging (API calls, credential access, system events)
- Blake's branch integration: publisher, audit tables, config, status indicator

#### Bug Fixes (50+)
- Resilient pipeline: handle partial satellite data instead of crashing
- Timezone-aware datetime comparison in pipeline
- CORS middleware ordering fix
- Full SSOT alignment: 32 fixes across 6 phases
- Dataset download serialization (NaN, Infinity, Decimal, datetime)
- Credential source field mismatch fix
- React hooks ordering (useMemo above early returns)
- 36 bugs resolved from user feedback and QA reports

---

## [2.0.0-docs] - 2026-02-02

### Documentation Merge (from Kelvin's Branch)

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

## [2.0.0-supabase] - 2026-01-27

### Added (Supabase / PostgreSQL Migration)

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
