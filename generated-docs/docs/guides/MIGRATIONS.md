# Database Migrations Guide

## Overview

The UCT Benchmark project uses Alembic for PostgreSQL schema migrations. Migrations are applied automatically on deployment via `start.py`, but can also be run manually.

DuckDB does not use Alembic -- its schema is managed directly by `uct_benchmark/database/schema.py`.

## Alembic Setup

The Alembic configuration is located at `UCT-Benchmark-DMR/combined/`:

```
alembic/
├── env.py              # Alembic environment configuration
├── alembic.ini         # Configuration file (uses DATABASE_URL env var)
└── versions/           # Migration scripts
    ├── 001_initial_schema.py
    ├── 002_add_submissions_user_id.py
    ├── 003_add_foreign_keys.py
    └── 004_timestamp_to_timestamptz.py
```

## Migration History

### 001: Initial Schema Baseline

- **Type**: No-op baseline
- **Purpose**: Establishes Alembic version tracking on an existing database
- **Notes**: Does not create tables -- they already exist from `schema_postgres.sql`. Run `alembic stamp head` to mark an existing database as up-to-date.

### 002: Add User ID to Submissions

- **Type**: Schema change
- **Changes**:
  - Adds `user_id` column (VARCHAR 255, nullable) to `submissions` table
  - Creates index `idx_submissions_user` on `submissions.user_id`
- **Purpose**: Enable ownership-based access control (IDOR protection)

### 003: Add Foreign Key Constraints

- **Type**: Schema change
- **Changes**: Adds CASCADE foreign keys:
  - `dataset_observations.dataset_id` -> `datasets.id`
  - `dataset_references.dataset_id` -> `datasets.id`
  - `submissions.dataset_id` -> `datasets.id`
  - `submission_results.submission_id` -> `submissions.id`
  - `non_reference_observations.dataset_id` -> `datasets.id`
- **Purpose**: Referential integrity with cascading deletes

### 004: Timestamp to Timestamptz

- **Type**: Schema change
- **Changes**: Converts all `TIMESTAMP` columns to `TIMESTAMPTZ` across all tables (satellites, observations, state_vectors, element_sets, datasets, submissions, submission_results, events, feedback, profiles, breakup_events, non_reference_observations, _schema_metadata)
- **Purpose**: Proper timezone handling -- prevents timezone bugs from `datetime.utcnow()` vs `datetime.now(timezone.utc)`

## Running Migrations

### Automatic (on deployment)

Migrations run automatically when `start.py` detects `DATABASE_URL`:

```bash
python start.py
# Output: "Running database migrations..."
# Output: "Database migrations complete."
```

### Manual

```bash
# Apply all pending migrations
python -m alembic upgrade head

# Apply up to a specific revision
python -m alembic upgrade 003

# Check current revision
python -m alembic current

# Show migration history
python -m alembic history
```

## Rolling Back

```bash
# Revert the last migration
python -m alembic downgrade -1

# Revert to a specific revision
python -m alembic downgrade 002

# Revert all migrations (back to empty)
python -m alembic downgrade base
```

## Creating New Migrations

### Auto-generate from model changes

```bash
python -m alembic revision --autogenerate -m "description_of_change"
```

### Manual migration

```bash
python -m alembic revision -m "description_of_change"
```

Then edit the generated file in `alembic/versions/` to add the `upgrade()` and `downgrade()` functions.

### Migration Best Practices

1. **Always include a `downgrade()` function** -- needed for rollbacks
2. **Test migrations on a copy of production data** before deploying
3. **Use sequential numeric prefixes** (001, 002, ...) for clarity
4. **Keep migrations small and focused** -- one logical change per migration
5. **Never modify an already-deployed migration** -- create a new one instead

## DuckDB Note

DuckDB (the local development backend) does not use Alembic. Its schema is defined in `uct_benchmark/database/schema.py` and applied directly when `DatabaseManager` initializes. If you add new tables or columns, you need to update both:

1. `schema.py` (for DuckDB)
2. `schema_postgres.sql` + a new Alembic migration (for PostgreSQL)

## Related Documentation

- [Database Architecture](../technical/DATABASE.md) - Schema and adapter pattern
- [Deployment](DEPLOYMENT.md) - Production deployment guide
- [Configuration](../technical/CONFIGURATION.md) - Environment variables
