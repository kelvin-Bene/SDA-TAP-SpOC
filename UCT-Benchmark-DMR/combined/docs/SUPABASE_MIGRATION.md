# Supabase Migration Guide

This document describes the migration from DuckDB-only to a dual-backend architecture supporting both DuckDB (local development) and PostgreSQL/Supabase (production).

## Overview

The migration is fully feature-flagged. Setting `DB_BACKEND=duckdb` (the default) preserves all existing behavior. Setting `DB_BACKEND=postgres` activates the PostgreSQL backend, audit logging, and database-backed job persistence.

Authentication is independently controlled via `AUTH_ENABLED`. When `false` (default), all endpoints work without tokens.

## Quick Start

### Local Development (DuckDB, no changes needed)

```bash
# Nothing changes — DuckDB is the default
python -m uvicorn backend_api.main:app --reload
```

### Production (PostgreSQL/Supabase)

1. **Set environment variables** (copy from `.env.example`):

```bash
DB_BACKEND=postgres
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
AUTH_ENABLED=true
```

2. **Run the SQL migration** against your Supabase database:

```bash
# Via Supabase SQL editor or psql:
psql $DATABASE_URL -f backend_api/db/migrations/001_initial_schema.sql
```

3. **Migrate existing DuckDB data** (optional):

```bash
python scripts/migrate_duckdb_to_postgres.py \
  --duckdb-path ./data/uct_benchmark.duckdb \
  --postgres-url $DATABASE_URL \
  --verify
```

4. **Configure the frontend**:

```bash
# frontend/.env.local
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_AUTH_ENABLED=true
```

5. **Start the application**:

```bash
python -m uvicorn backend_api.main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

## Architecture

### Database Abstraction Layer

```
DatabaseManager
  └── _backend: DatabaseBackendInterface
        ├── DuckDBBackend      (DB_BACKEND=duckdb)
        └── PostgresBackend    (DB_BACKEND=postgres)
```

All existing code calls `db.execute(query, params)` unchanged. The backend interface handles:
- **Placeholder conversion**: `?` (DuckDB) to `%s` (PostgreSQL)
- **SQL dialect**: `INSERT OR REPLACE` to `ON CONFLICT DO UPDATE`
- **Schema**: `main` (DuckDB) to `public` (PostgreSQL)
- **Types**: `JSON` to `JSONB`, `TIMESTAMP` to `TIMESTAMPTZ`
- **Bulk insert**: DuckDB `register/unregister` to PostgreSQL `executemany`

### Authentication Flow

```
Request → [Authorization: Bearer <JWT>]
  → require_auth() dependency
    → AUTH_ENABLED=false? → return anonymous admin
    → AUTH_ENABLED=true?  → verify_jwt() → return payload or 401
```

Dependencies available for FastAPI routes:
- `get_current_user()` — Returns user dict or `None` (never raises)
- `require_auth()` — Returns user dict or raises `401`
- `require_admin()` — Returns admin user or raises `403`

### Audit Logging

When `DB_BACKEND=postgres`, the following is automatically logged:
- **API calls**: All mutation requests (POST/PUT/PATCH/DELETE) via `AuditMiddleware`
- **Slow queries**: Requests exceeding 500ms via `QueryLoggingMiddleware`
- **Credential access**: All resolve/save/delete operations via `audit_service`
- **System events**: Startup, errors, and operational events

All logging functions swallow exceptions — audit failures never break requests.

### Job Persistence

When `DB_BACKEND=postgres`, jobs are stored in the `jobs` database table instead of in-memory. This means:
- Jobs survive server restarts
- Multiple server instances share the same job state
- Job history is queryable via SQL

## New Database Tables

| Table | Purpose |
|-------|---------|
| `users` | User profiles linked to Supabase Auth |
| `audit_log` | CRUD operation audit trail |
| `api_call_log` | HTTP request metrics |
| `query_log` | Slow query tracking |
| `credential_access_log` | Credential resolve/save/delete events |
| `system_log` | Application-level events |

Existing tables (`datasets`, `submissions`, `uctp_runs`) gain a `created_by UUID` column referencing `users`.

## Environment Variables

| Variable | Default | Required For |
|----------|---------|-------------|
| `DB_BACKEND` | `duckdb` | Always |
| `DATABASE_URL` | — | PostgreSQL mode |
| `SUPABASE_URL` | — | PostgreSQL mode |
| `SUPABASE_ANON_KEY` | — | PostgreSQL mode |
| `SUPABASE_SERVICE_ROLE_KEY` | — | PostgreSQL mode |
| `SUPABASE_JWT_SECRET` | — | Auth enabled |
| `AUTH_ENABLED` | `false` | Auth feature |
| `PG_POOL_MIN` | `2` | PostgreSQL tuning |
| `PG_POOL_MAX` | `10` | PostgreSQL tuning |
| `CORS_ORIGINS` | localhost defaults | CORS configuration |
| `CREDENTIAL_ENCRYPTION_KEY` | — | Encrypted credential storage |
| `VITE_SUPABASE_URL` | — | Frontend auth |
| `VITE_SUPABASE_ANON_KEY` | — | Frontend auth |
| `VITE_AUTH_ENABLED` | `false` | Frontend auth guards |

## Data Migration Script

```bash
# Dry run (reads DuckDB, prints what would be migrated)
python scripts/migrate_duckdb_to_postgres.py \
  --duckdb-path ./data/uct_benchmark.duckdb \
  --postgres-url $DATABASE_URL \
  --dry-run

# Full migration with verification
python scripts/migrate_duckdb_to_postgres.py \
  --duckdb-path ./data/uct_benchmark.duckdb \
  --postgres-url $DATABASE_URL \
  --batch-size 5000 \
  --verify
```

The script:
- Migrates 20 tables in FK-safe dependency order
- Converts JSON string columns to JSONB-compatible dicts
- Uses `ON CONFLICT DO NOTHING` for idempotent re-runs
- Resets PostgreSQL sequences after migration
- Verifies row counts match between source and destination

## Testing

```bash
# Run all new tests
python -m pytest backend_api/tests/test_config.py \
  backend_api/tests/test_auth_middleware.py \
  backend_api/tests/test_audit_service.py \
  backend_api/tests/test_db_job_manager.py \
  backend_api/tests/test_query_logging.py \
  tests/test_data_migration.py -v

# Run full backend suite
python -m pytest backend_api/tests/ -v
```

All 89 new tests pass. Zero regressions to existing tests.
