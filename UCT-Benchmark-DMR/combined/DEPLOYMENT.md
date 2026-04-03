# UCT Benchmark Deployment Guide

## Architecture

```
GitHub (master branch)  ──→  Railway Production Environment
GitHub (dev branch)     ──→  Railway Demo Environment
```

### Production
- **Backend**: Java 17 + Python 3.12 (Orekit orbital mechanics)
- **Database**: Supabase PostgreSQL
- **Auth**: Supabase JWKS (ES256) JWT validation
- **Frontend**: nginx with reverse proxy to backend

### Demo
- **Backend**: Python 3.12 only (no Java/Orekit, lighter image)
- **Database**: DuckDB (local, ephemeral)
- **Auth**: Disabled (DEMO_MODE=true)
- **Frontend**: nginx with reverse proxy to backend (Railway internal networking)

## GitHub Secrets Required

Set these in GitHub repo → Settings → Secrets and variables → Actions:

| Secret | Description | Example |
|--------|-------------|---------|
| `RAILWAY_TOKEN_PROD` | Railway project token scoped to production | (generate from Railway dashboard) |
| `RAILWAY_TOKEN_DEMO` | Railway project token scoped to demo | `d683b67f-...` |
| `PROD_BACKEND_URL` | Production backend public URL | `https://backend-production-4b02.up.railway.app/api/v1` |
| `VITE_SUPABASE_URL` | Supabase project URL | `https://csuqtcizjfsmkoeevyau.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key | (from Supabase dashboard → API) |

## Railway Environment Variables

### Production Backend
| Variable | Value |
|----------|-------|
| `DATABASE_BACKEND` | `postgres` |
| `DATABASE_URL` | `postgresql://...` (Supabase connection string) |
| `SUPABASE_URL` | `https://csuqtcizjfsmkoeevyau.supabase.co` |
| `CORS_ORIGINS` | `https://frontend-production-6d80.up.railway.app` |
| `LOG_LEVEL` | `INFO` |

### Production Frontend
| Variable | Value |
|----------|-------|
| `BACKEND_URL` | `http://backend.railway.internal:8000` |

### Demo Backend
| Variable | Value |
|----------|-------|
| `DATABASE_BACKEND` | `duckdb` |
| `DEMO_MODE` | `true` |
| `CORS_ORIGINS` | `https://frontend-demo-1542.up.railway.app` |
| `RAILWAY_DOCKERFILE_PATH` | `Dockerfile.demo` |
| `LOG_LEVEL` | `INFO` |

### Demo Frontend
| Variable | Value |
|----------|-------|
| `BACKEND_URL` | `http://backend.railway.internal:8000` |
| `VITE_DEMO_MODE` | `true` |

## Branch Strategy

- `master` → triggers production deploy on push
- `dev` → triggers demo deploy on push
- Feature branches → no auto-deploy, merge to `dev` for testing, then to `master` for release

## CI/CD Pipeline (GitHub Actions)

On push to `master` or `dev`:
1. **Test** — pytest (backend) + tsc type check (frontend)
2. **Deploy Backend** — `railway up --service backend --environment <env>`
3. **Deploy Frontend** — `npm run build` → `railway up --service frontend --environment <env>`

## Database Migrations

Migrations are managed with Alembic and only target PostgreSQL (not DuckDB).

### First-time setup (existing database)
```bash
# Mark the existing database as up-to-date with the initial schema
DATABASE_URL=postgresql://... alembic stamp head
```

### Running migrations
```bash
# Apply pending migrations
DATABASE_URL=postgresql://... alembic upgrade head

# Check current version
DATABASE_URL=postgresql://... alembic current
```

### Creating new migrations
```bash
# After modifying schema_postgres.sql, create a migration
DATABASE_URL=postgresql://... alembic revision -m "description of change"
# Then edit the generated file to add upgrade/downgrade logic
```

## Rollback Procedure

### Quick Rollback via Railway Dashboard

1. Open the Railway dashboard for the affected service (backend or frontend).
2. Navigate to **Deployments** and find the last known-good deployment.
3. Click the three-dot menu on that deployment and select **Redeploy**.
4. Monitor the service health endpoint (`/health`) to confirm recovery.

### Rollback via Railway CLI

```bash
# List recent deployments for the backend service
railway status --service backend

# Redeploy the previous version
railway redeploy --service backend
```

### Database Migration Rollback (Alembic)

If a deployment included a database migration that needs to be reverted:

```bash
# Check current migration version
DATABASE_URL=postgresql://... alembic current

# Downgrade by one revision
DATABASE_URL=postgresql://... alembic downgrade -1

# Downgrade to a specific revision
DATABASE_URL=postgresql://... alembic downgrade <revision_id>

# View migration history to find target revision
DATABASE_URL=postgresql://... alembic history
```

**Important:** Always roll back the application code *before* rolling back the
database schema, since the newer code may depend on the newer schema.

### Post-Rollback Checklist

- [ ] Verify `/health` endpoint returns 200
- [ ] Check database connectivity via health endpoint
- [ ] Confirm frontend loads and can reach the backend API
- [ ] Review application logs for errors (`railway logs --service backend`)
- [ ] Notify the team about the rollback and root cause

## Local Development

```bash
cd UCT-Benchmark-DMR/combined
docker-compose up  # Starts PostgreSQL + backend + frontend
```

## v2.0.0 Platform Features

### Authentication (Supabase JWT)
- **Production**: ES256 asymmetric key verification via JWKS endpoint at `SUPABASE_URL/.well-known/jwks.json`
- **Development**: Auth disabled when `ENVIRONMENT=development` (blocked if `SUPABASE_URL` is set)
- **HS256 fallback**: Available in non-production environments only when `ALLOW_HS256_FALLBACK=true`
- Roles managed via `app_metadata.role` (server-side only, not user-editable)

### Rate Limiting
- Implemented via slowapi with per-IP limits
- Uses rightmost X-Forwarded-For IP (appended by trusted proxy)
- Key limits: 10/minute on dataset listing, 5/minute on feedback submission, 5/minute on report generation

### Security Headers (nginx)
- Content-Security-Policy with Cesium and Supabase domains whitelisted
- Strict-Transport-Security (HSTS) with 1-year max-age
- X-Frame-Options: DENY, X-Content-Type-Options: nosniff
- Permissions-Policy: camera, microphone, geolocation disabled

### Encrypted Token Storage
- User API tokens (UDL, ESA) encrypted at rest using Fernet symmetric encryption
- `ENCRYPTION_KEY` required for PostgreSQL backend; plaintext allowed only for DuckDB dev
- Generate key: `python -c "from backend_api.utils.crypto import generate_key; print(generate_key())"`

### Feedback System
- Users can submit bug reports with description, screenshot (base64), and page URL
- Admin dashboard for reviewing and resolving feedback
- Rate limited to 5 submissions per minute

### Sentry Integration
- Backend: Initialized in `backend_api/main.py` with `SENTRY_DSN`
- Frontend: Initialized in `main.tsx` with `VITE_SENTRY_DSN`
- Captures unhandled exceptions, performance traces, and session replays

### Database Backups
- Automated daily backups at 2:00 UTC via GitHub Actions
- `pg_dump` with gzip compression, uploaded as GitHub artifacts
- 30-day retention with restore verification
- Manual trigger available via `workflow_dispatch`

### Monitoring
- `/health` endpoint checks database connectivity and disk space
- Structured audit logging for sensitive operations (token changes, admin actions)
- Request correlation IDs via middleware
