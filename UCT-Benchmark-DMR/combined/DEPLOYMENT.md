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

## Local Development

```bash
cd UCT-Benchmark-DMR/combined
docker-compose up  # Starts PostgreSQL + backend + frontend
```
