# Database Migration Guide

This guide covers migrating UCT Benchmark data between DuckDB and PostgreSQL databases.

## Overview

UCT Benchmark uses a database adapter pattern that supports:
- **DuckDB**: Local, file-based database (default for development)
- **PostgreSQL**: Cloud-hosted database (for production, including Supabase)

## Migration Scenarios

### 1. DuckDB to PostgreSQL (Supabase)

Use this when deploying to production or sharing data across multiple instances.

```bash
# Step 1: Dry run to see what will be migrated
python scripts/migrate_to_supabase.py \
    --source ./data/database/uct_benchmark.duckdb \
    --target postgresql://user:pass@host:5432/db \
    --dry-run

# Step 2: Run the migration
python scripts/migrate_to_supabase.py \
    --source ./data/database/uct_benchmark.duckdb \
    --target postgresql://user:pass@host:5432/db

# Step 3: Validate the migration
python scripts/migrate_to_supabase.py \
    --validate \
    --source ./data/database/uct_benchmark.duckdb \
    --target postgresql://user:pass@host:5432/db
```

### 2. PostgreSQL to DuckDB (Local Backup)

For creating local backups or development copies:

```python
import pandas as pd
from uct_benchmark.database.connection import DatabaseManager

# Connect to PostgreSQL source
source = DatabaseManager(
    backend="postgres",
    database_url="postgresql://user:pass@host:5432/db"
)

# Connect to DuckDB target
target = DatabaseManager(db_path="./backup.duckdb")
target.initialize(force=True)  # Create fresh schema

# Migration order (respects foreign keys)
tables = [
    "satellites", "observations", "state_vectors", "element_sets",
    "datasets", "dataset_observations", "dataset_references",
    "event_types", "events", "event_observations",
    "submissions", "submission_results", "jobs", "_schema_metadata"
]

for table in tables:
    df = source.adapter.fetchdf(f"SELECT * FROM {table}")
    if not df.empty:
        target.adapter.bulk_insert_df(
            table=table,
            df=df,
            columns=list(df.columns),
        )
        print(f"Migrated {len(df)} rows from {table}")

source.close()
target.close()
```

## Migration Script Options

The `scripts/migrate_to_supabase.py` script supports these options:

| Option | Description |
|--------|-------------|
| `--source PATH` | Path to source DuckDB file |
| `--target URL` | PostgreSQL connection URL |
| `--dry-run` | Preview migration without changes |
| `--validate` | Compare source and target after migration |
| `--tables TABLE...` | Migrate specific tables only |

### Examples

```bash
# Migrate only satellites and observations
python scripts/migrate_to_supabase.py \
    --source ./data/db.duckdb \
    --target $DATABASE_URL \
    --tables satellites observations

# Validate specific tables
python scripts/migrate_to_supabase.py \
    --validate \
    --source ./data/db.duckdb \
    --target $DATABASE_URL \
    --tables datasets submissions
```

## Table Migration Order

Tables must be migrated in this order to respect foreign key relationships:

1. `satellites` - Base catalog
2. `observations` - References satellites
3. `state_vectors` - References satellites
4. `element_sets` - References satellites
5. `datasets` - Self-referential (parent_id)
6. `dataset_observations` - References datasets, observations
7. `dataset_references` - References datasets, satellites, state_vectors
8. `event_types` - Event type definitions
9. `events` - References event_types, satellites
10. `event_observations` - References events, observations
11. `submissions` - References datasets
12. `submission_results` - References submissions
13. `jobs` - Standalone
14. `_schema_metadata` - Schema version tracking

## Data Validation

After migration, validate data integrity:

```bash
# Full validation (counts + checksums)
python scripts/migrate_to_supabase.py \
    --validate \
    --source ./data/db.duckdb \
    --target $DATABASE_URL
```

### Manual Validation Queries

```sql
-- Compare row counts
SELECT 'satellites' as table_name, COUNT(*) as count FROM satellites
UNION ALL
SELECT 'observations', COUNT(*) FROM observations
UNION ALL
SELECT 'datasets', COUNT(*) FROM datasets;

-- Check for orphaned records
SELECT COUNT(*) FROM dataset_observations dso
WHERE NOT EXISTS (SELECT 1 FROM datasets d WHERE d.id = dso.dataset_id);
```

## Handling Large Migrations

For databases with millions of rows:

### 1. Batch Processing

The migration script processes data in batches (default: 10,000 rows). For very large tables, consider:

```python
# Custom batch size
BATCH_SIZE = 5000  # Reduce for limited memory
```

### 2. Parallel Migration

For independent tables, run migrations in parallel:

```bash
# Terminal 1
python scripts/migrate_to_supabase.py --source ./db.duckdb --target $URL --tables satellites

# Terminal 2
python scripts/migrate_to_supabase.py --source ./db.duckdb --target $URL --tables observations
```

### 3. Disable Constraints Temporarily

For PostgreSQL, you can temporarily disable triggers:

```sql
-- Before migration
ALTER TABLE observations DISABLE TRIGGER ALL;

-- After migration
ALTER TABLE observations ENABLE TRIGGER ALL;
```

## Rollback Procedures

### DuckDB Rollback

Simply restore from backup:

```bash
# Restore from backup
cp ./data/backups/uct_benchmark_20240101.duckdb ./data/database/uct_benchmark.duckdb
```

### PostgreSQL Rollback

1. Use Supabase's point-in-time recovery (if enabled)
2. Or restore from a pg_dump backup:

```bash
# Restore from SQL dump
psql $DATABASE_URL < backup.sql
```

## Troubleshooting

### "unique constraint violated"

**Cause**: Duplicate primary keys in source data

**Solution**: Use `ON CONFLICT DO NOTHING` (default behavior) or clean source data first

### "foreign key constraint violated"

**Cause**: Migrating tables out of order

**Solution**: Follow the migration order above, or disable constraints temporarily

### "connection timeout"

**Cause**: Network issues or large batch sizes

**Solution**:
1. Reduce batch size
2. Check network connectivity
3. Increase PostgreSQL connection timeout

### "out of memory"

**Cause**: Too many rows loaded at once

**Solution**:
1. Reduce BATCH_SIZE
2. Process tables one at a time
3. Use streaming queries for very large tables

## Schema Version Compatibility

The migration script automatically:
1. Creates the schema if it doesn't exist
2. Preserves schema version information
3. Does not modify existing data (uses ON CONFLICT DO NOTHING)

Check schema versions after migration:

```sql
SELECT * FROM _schema_metadata WHERE key = 'version';
```

## Best Practices

1. **Always backup before migration**
   ```bash
   # DuckDB backup
   cp ./data/db.duckdb ./data/db.duckdb.backup

   # PostgreSQL backup
   pg_dump $DATABASE_URL > backup.sql
   ```

2. **Test with dry-run first**

3. **Validate after migration**

4. **Keep source data until validated**

5. **Document any custom modifications**
