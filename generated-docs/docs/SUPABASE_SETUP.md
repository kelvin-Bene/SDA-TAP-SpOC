# Supabase Setup Guide

This guide explains how to configure UCT Benchmark to use Supabase (PostgreSQL) as the database backend.

## Overview

UCT Benchmark supports two database backends:
- **DuckDB** (default): Local file-based database, ideal for development
- **PostgreSQL/Supabase**: Cloud-hosted database, ideal for production

## Prerequisites

1. A Supabase account (https://supabase.com)
2. Python 3.12+
3. psycopg3 installed: `pip install "psycopg[binary,pool]>=3.1.0"`

## Step 1: Create a Supabase Project

1. Go to https://app.supabase.com
2. Click "New Project"
3. Choose your organization and enter:
   - **Project name**: `uct-benchmark` (or your preferred name)
   - **Database password**: Generate a strong password (save this!)
   - **Region**: Choose closest to your users
4. Click "Create new project"
5. Wait for the project to be provisioned (1-2 minutes)

## Step 2: Get Connection Details

1. In your Supabase dashboard, go to **Project Settings** > **Database**
2. Find the **Connection string** section
3. Copy the **URI** connection string (it looks like):
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
4. Replace `[YOUR-PASSWORD]` with the password you set during project creation

## Step 3: Configure Environment Variables

Create or update your `.env` file:

```env
# Database Configuration for Supabase
DATABASE_BACKEND=postgres
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Connection Pool Settings (optional, these are defaults)
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10
```

### Environment Variable Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_BACKEND` | Backend type: `duckdb` or `postgres` | `duckdb` |
| `DATABASE_URL` | PostgreSQL connection string | (required for postgres) |
| `DATABASE_PATH` | Path to DuckDB file | `./data/database/uct_benchmark.duckdb` |
| `DATABASE_POOL_MIN` | Minimum connection pool size | `2` |
| `DATABASE_POOL_MAX` | Maximum connection pool size | `10` |

## Step 4: Initialize the Database

The schema will be automatically created when you first start the application:

```bash
# Run the API server
DATABASE_BACKEND=postgres uvicorn backend_api.main:app --reload
```

Or initialize manually with Python:

```python
from uct_benchmark.database.connection import DatabaseManager

db = DatabaseManager(
    backend="postgres",
    database_url="postgresql://postgres:password@db.xxx.supabase.co:5432/postgres"
)
db.initialize()
```

## Step 5: Migrate Existing Data (Optional)

If you have existing data in a DuckDB database, use the migration script:

```bash
# Dry run (preview what will be migrated)
python scripts/migrate_to_supabase.py \
    --source ./data/database/uct_benchmark.duckdb \
    --target $DATABASE_URL \
    --dry-run

# Full migration
python scripts/migrate_to_supabase.py \
    --source ./data/database/uct_benchmark.duckdb \
    --target $DATABASE_URL

# Validate migration
python scripts/migrate_to_supabase.py \
    --validate \
    --source ./data/database/uct_benchmark.duckdb \
    --target $DATABASE_URL
```

## Supabase-Specific Configuration

### Connection Pooling

Supabase uses PgBouncer for connection pooling. By default, UCT Benchmark connects directly to PostgreSQL. For high-traffic production deployments, consider using the pooler connection string from Supabase.

### Row Level Security (RLS)

Supabase enables Row Level Security by default on new tables. The UCT Benchmark schema does not currently use RLS. If you need to enable it:

1. Go to **Authentication** > **Policies** in the Supabase dashboard
2. Create appropriate policies for your use case

### SSL Connections

Supabase requires SSL connections. The psycopg3 driver handles this automatically when using the provided connection string.

## Troubleshooting

### Connection Refused

**Problem**: Cannot connect to Supabase database

**Solutions**:
1. Verify your connection string is correct
2. Check that the password doesn't contain special characters that need URL encoding
3. Verify your IP isn't blocked (check Supabase Network settings)

### SSL Certificate Errors

**Problem**: SSL certificate verification fails

**Solution**: Add `sslmode=require` to your connection string:
```
postgresql://postgres:password@db.xxx.supabase.co:5432/postgres?sslmode=require
```

### Connection Pool Exhausted

**Problem**: "too many connections" error

**Solutions**:
1. Increase `DATABASE_POOL_MAX` (but stay within Supabase limits)
2. Use the Supabase connection pooler (Transaction mode)
3. Ensure connections are properly closed after use

### Slow Queries

**Problem**: Queries are slow on Supabase

**Solutions**:
1. Run `VACUUM ANALYZE` on tables:
   ```python
   db.vacuum()  # Runs VACUUM ANALYZE on all tables
   ```
2. Check for missing indexes
3. Consider upgrading your Supabase plan for more resources

## Switching Back to DuckDB

To switch back to DuckDB for local development:

```env
DATABASE_BACKEND=duckdb
DATABASE_PATH=./data/database/uct_benchmark.duckdb
# Comment out or remove DATABASE_URL
```

## Security Best Practices

1. **Never commit `.env` files** with real credentials
2. Use environment variables in production
3. Rotate database passwords periodically
4. Use the minimum required permissions
5. Enable Supabase's built-in monitoring

## Support

- Supabase Documentation: https://supabase.com/docs
- UCT Benchmark Issues: https://github.com/your-repo/issues
