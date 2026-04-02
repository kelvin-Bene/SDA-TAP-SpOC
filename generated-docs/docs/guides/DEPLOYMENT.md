# Deployment Guide

## Overview

The UCT Benchmark platform is deployed on Railway with a PostgreSQL/Supabase database backend. This guide covers the production deployment process, required configuration, and operational procedures.

## Railway Setup

The application runs as a single Railway service with the following components:

- **Backend**: FastAPI application served by Uvicorn
- **Frontend**: Static React build served by nginx (separate service or container)
- **Database**: Supabase-hosted PostgreSQL (external)

### Service Configuration

Railway uses the `start.py` script as the entry point. The startup flow is:

```
start.py
  1. Validate critical environment variables
  2. Run Alembic database migrations (if DATABASE_URL is set)
  3. Start Uvicorn with backend_api.main:app
```

## Required Environment Variables

Set these in the Railway service settings:

### Database

| Variable | Value | Description |
|----------|-------|-------------|
| `DATABASE_BACKEND` | `postgres` | Use PostgreSQL instead of DuckDB |
| `DATABASE_URL` | `postgresql://...` | Supabase direct connection string (not pooler) |
| `ENCRYPTION_KEY` | `<fernet-key>` | Fernet key for encrypting stored API tokens |

Generate an encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Authentication

| Variable | Value | Description |
|----------|-------|-------------|
| `SUPABASE_URL` | `https://<project>.supabase.co` | Enables ES256 JWKS JWT verification |
| `SUPABASE_JWT_SECRET` | `<jwt-secret>` | Supabase JWT secret (fallback verification) |

### Application

| Variable | Value | Description |
|----------|-------|-------------|
| `CORS_ORIGINS` | `https://your-frontend-domain.com` | Comma-separated allowed origins |
| `PORT` | (set by Railway) | HTTP port -- Railway sets this automatically |
| `WEB_WORKERS` | `1` | Must be 1 -- JobManager uses in-memory state |
| `ENVIRONMENT` | `production` | Do NOT set to `development` in production |

### Optional

| Variable | Value | Description |
|----------|-------|-------------|
| `SENTRY_DSN` | `https://...@sentry.io/...` | Sentry error tracking |
| `TRUSTED_PROXY_DEPTH` | `1` | Number of trusted proxies for rate limiting |

## Start.py Flow

The `start.py` script performs the following steps on each deployment:

### 1. Configuration Validation

Checks that required variables are set and consistent:

- `DATABASE_URL` is required when `DATABASE_BACKEND=postgres`
- `ENCRYPTION_KEY` is required when `DATABASE_BACKEND=postgres`
- `CORS_ORIGINS` must not contain `*` (incompatible with credential-based auth)

If validation fails, the process exits with error messages.

### 2. Database Migrations

When `DATABASE_URL` is set, Alembic migrations run automatically:

```bash
python -m alembic upgrade head
```

This applies any pending migrations from `alembic/versions/`. If migrations fail, the process exits before starting the web server.

### 3. Uvicorn Startup

```bash
uvicorn backend_api.main:app --host 0.0.0.0 --port $PORT --workers $WEB_WORKERS
```

## Health Checks

The application exposes two health endpoints:

### `GET /`
Returns `{"status": "ok"}` -- basic liveness check.

### `GET /health`
Returns component-level health status:

```json
{
  "status": "healthy",
  "components": {
    "database": "connected",
    "disk_space": "ok"
  }
}
```

Returns HTTP 503 if the database is unreachable.

## Worker Limitations

The `WEB_WORKERS` setting **must remain at 1** in the current architecture. The `JobManager` stores job state in process memory (a Python dictionary). Multiple workers would cause:

- Job status polling returning 404 (different worker doesn't have the job)
- Lost job results
- Duplicate job execution

To scale beyond 1 worker, the JobManager must be migrated to a shared backend (Redis, Celery, or ARQ). The `start.py` script emits a warning if `WEB_WORKERS > 1`.

## Rollback Procedure

### Quick Rollback

Railway supports instant rollback to any previous deployment:

1. Go to the Railway dashboard
2. Navigate to the service's Deployments tab
3. Click on a previous successful deployment
4. Click "Rollback to this deployment"

### Database Rollback

If a migration needs to be reverted:

```bash
# Revert the last migration
python -m alembic downgrade -1

# Revert to a specific revision
python -m alembic downgrade 003
```

See [Migrations Guide](MIGRATIONS.md) for details.

## Production Security

The following security measures are active in production:

- **OpenAPI docs disabled**: `/docs`, `/redoc`, and `/openapi.json` return 404
- **Security headers**: HSTS, X-Frame-Options, Referrer-Policy, Permissions-Policy
- **Rate limiting**: Mutation endpoints are rate-limited (e.g., 10/min for submissions)
- **CORS enforcement**: Only explicitly listed origins are allowed
- **JWT verification**: ES256 JWKS with issuer and audience validation

## Related Documentation

- [Authentication](../technical/AUTHENTICATION.md) - JWT verification details
- [Migrations](MIGRATIONS.md) - Database migration guide
- [Configuration](../technical/CONFIGURATION.md) - Full environment variable reference
