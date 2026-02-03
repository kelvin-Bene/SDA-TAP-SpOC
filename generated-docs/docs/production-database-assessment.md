# Production Database & Data Tracking Assessment Report

**UCT Benchmark / SDA-TAP-SPOC Platform**
**Date:** January 2026
**Status:** Research Assessment (Documentation Only)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Audit](#2-current-architecture-audit)
3. [DuckDB Limitations for Production Hosting](#3-duckdb-limitations-for-production-hosting)
4. [PostgreSQL Assessment](#4-postgresql-assessment)
5. [Supabase Assessment](#5-supabase-assessment)
6. [Other Options](#6-other-options)
7. [Cost Comparison Matrix](#7-cost-comparison-matrix)
8. [Migration Complexity Assessment](#8-migration-complexity-assessment)
9. [Production Readiness -- New Tables Required](#9-production-readiness----new-tables-required)
10. [Dataset Generation Provenance Deep-Dive](#10-dataset-generation-provenance-deep-dive)
11. [Recommendation](#11-recommendation)

---

## 1. Executive Summary

The UCT Benchmark platform currently uses DuckDB as its sole database, embedded in-process within a FastAPI backend. While DuckDB has served well for single-user development and analytical workloads, it is architecturally unsuitable for a multi-user hosted production environment. Key findings:

- **DuckDB enforces single-writer process access** -- two concurrent dataset generations block each other, and running multiple uvicorn workers or separate ingestion scripts is unsupported.
- **No network server mode exists** -- the database must live on the same machine as the application server, preventing horizontal scaling.
- **Zero user tracking infrastructure** -- no `users` table, no `created_by` fields, no audit logging, no query tracking, and no credential usage audit trail.
- **External API call metrics are in-memory only** -- the `MetricsCollector` stores call history in a Python list that is lost on restart.
- **The query cache is in-memory with a 15-minute TTL** -- no persistent caching layer.

**Recommended path forward:** Migrate to **PostgreSQL** as the primary database, using either **Supabase** (if built-in auth and real-time are valued) or **Neon** (if serverless autoscaling and database branching are priorities). Both options are PostgreSQL-compatible, and the existing DuckDB SQL was deliberately written in a PostgreSQL-compatible dialect, minimizing translation effort.

Regardless of database choice, six new tables must be added for production readiness: `users`, `audit_log`, `api_call_log`, `query_log`, `credential_access_log`, and `system_log`.

---

## 2. Current Architecture Audit

### 2.1 Database Schema: 20 Tables

The schema is defined in `uct_benchmark/database/schema.py` (936 lines, schema version `1.3.0`). The 20 tables are:

| # | Table | Purpose |
|---|---|---|
| 1 | `data_sources` | Provenance tracking (UDL, SatNOGS, GCAT, etc.) |
| 2 | `satellites` | NORAD catalog with physical properties |
| 3 | `observations` | Observation records (RA/Dec, radar, sensor metadata) |
| 4 | `state_vectors` | J2000 ECI position/velocity with covariance |
| 5 | `element_sets` | TLE/orbital elements |
| 6 | `datasets` | Benchmark dataset records with generation params |
| 7 | `dataset_observations` | Junction: dataset <-> observation mapping |
| 8 | `dataset_references` | Junction: dataset <-> satellite truth data |
| 9 | `submissions` | Algorithm submission tracking |
| 10 | `submission_results` | Evaluation metrics (F1, position RMS, etc.) |
| 11 | `jobs` | Background job tracking |
| 12 | `validation_measurements` | ILRS laser ranging ground truth |
| 13 | `event_types` | Event classification lookup |
| 14 | `events` | Orbital event labels (maneuver, proximity, etc.) |
| 15 | `event_observations` | Junction: event <-> observation mapping |
| 16 | `uctp_runs` | UCTP Algorithm Lab run history |
| 17 | `uctp_models` | ML model registry |
| 18 | `uctp_api_connections` | API connection health checks |
| 19 | `credentials` | Fernet-encrypted credential storage |
| 20 | `_schema_metadata` | Schema version tracking |

**JSON columns** (12 total): `state_vectors.covariance`, `datasets.generation_params`, `datasets.downsampling_config`, `datasets.simulation_config`, `dataset_references.grouped_obs_ids`, `jobs.result`, `jobs.metadata`, `submission_results.raw_results`, `uctp_runs.config`, `uctp_models.training_dataset_ids`, `uctp_models.training_config`, `uctp_api_connections.metadata`.

### 2.2 DatabaseManager: Threading Model

`uct_benchmark/database/connection.py` (364 lines):

- **Thread-local connections** via `threading.local()` at line 100
- **Global lock** via `threading.Lock()` at line 101
- Schema initialization acquires the lock (`connection.py:195-197`)
- File-based databases use thread-local connections (`connection.py:131-141`)
- In-memory databases use a single shared connection (`connection.py:122-129`)
- Connection is `duckdb.connect(file_path)` -- embedded, no network protocol

### 2.3 Repository Pattern: Raw SQL, No ORM

`uct_benchmark/database/repository.py` (1618 lines) contains 6 repository classes:

1. `SatelliteRepository` -- CRUD + bulk upsert
2. `ObservationRepository` -- time-window queries, bulk insert via DataFrame `register()`/`unregister()`
3. `StateVectorRepository` -- epoch-based queries, bulk insert via DataFrame `register()`
4. `ElementSetRepository` -- TLE management, bulk insert via DataFrame `register()`
5. `DatasetRepository` -- version control, observation linking, comparison tools
6. `EventRepository` -- event labelling and observation linking

All queries use raw SQL with `?` placeholders. No SQLAlchemy, no ORM. Bulk inserts use DuckDB's `register("temp_df", dataframe)` pattern (`repository.py:391-406`).

### 2.4 Background Job Execution

`backend_api/jobs/workers.py` (703 lines):

- `ThreadPoolExecutor(max_workers=4)` at line 54
- Two worker functions: `run_dataset_generation` and `run_evaluation_pipeline`
- Workers access the database via `get_db()` singleton from `backend_api/database.py`
- Job progress updates written directly to the database from background threads

### 2.5 No User System

- **Zero `created_by` fields** across all 20 tables
- **No `users` table** in `schema.py`
- The FastAPI backend has no authentication middleware
- Frontend auth (if any) is client-side stubs only
- The `events` table has a `labelled_by VARCHAR(100)` field (line 463), but it's a free-text string, not a foreign key to a users table

### 2.6 No Audit Logging

- All logging goes through **loguru** to console/file output
- `backend_api/database.py:133` prints to stdout: `print(f"Database initialized at: {db.db_path}")`
- No persistent database-backed audit trail
- No record of who created, modified, or deleted any resource
- No tracking of which API endpoints were called, by whom, or when

### 2.7 No Query Tracking

- API responses include paginated data, but pagination parameters are not stored
- No record of what data a user retrieved or which page they viewed
- After a response is sent, the query details are lost

### 2.8 No External API Call Persistence

Two separate in-memory tracking systems exist:

1. **`_api_call_metrics` dict** in `apiIntegration.py:74-79` -- keeps last 100 calls in a Python list, reset on process restart
2. **`MetricsCollector` class** in `logging_config.py:105` -- collects `_api_calls` as an in-memory list, used during dataset generation runs

Neither persists to the database. The `MetricsCollector.log_api_call()` method (`logging_config.py:118-142`) appends to `self._api_calls: List[Dict]`, which is lost when the object is garbage-collected.

### 2.9 No Credential Usage Audit

`backend_api/services/credential_service.py` (323 lines):

- `CredentialService.resolve()` (line 267) returns credentials via the fallback chain: DB (encrypted) -> `.env` -> None
- **No logging of who accessed credentials**, when, or for what purpose
- `save_credentials()` (line 190) and `delete_credentials()` (line 229) modify credential storage without audit records
- Workers resolve credentials at `workers.py:97-106` with no tracking

### 2.10 In-Memory Query Cache

`apiIntegration.py:143-189`:

- `QueryCache` class with `max_size=1000` and `ttl_seconds=900` (15 minutes, configured in `settings.py:226-227`)
- Global instance `_query_cache` at line 187
- MD5-based cache keys from service name + params
- No persistent cache -- all entries lost on restart
- No cache hit/miss metrics persisted

---

## 3. DuckDB Limitations for Production Hosting

DuckDB is an excellent embedded analytical database for single-user, single-process workloads. However, its architecture has fundamental constraints that make it unsuitable for a hosted multi-user web application.

| Limitation | Evidence from Codebase | Production Impact |
|---|---|---|
| **Single-writer process** | `threading.Lock()` at `connection.py:101`; DuckDB docs: "Writing to DuckDB from multiple processes is not supported automatically and is not a primary design goal" | Two concurrent dataset generations or any two write operations from separate processes block each other |
| **No network server mode** | Embedded in-process via `duckdb.connect(file_path)` at `connection.py:137-140` | DB must live on the same machine as the app server; no remote connections possible |
| **No multi-process access** | File-level locking; `DataMigration` and other scripts create separate `DatabaseManager` instances | Cannot run multiple uvicorn workers (`--workers N`), separate ingestion scripts, or analytics queries alongside the web server |
| **No built-in auth/roles** | Anyone with filesystem access to `uct_benchmark.duckdb` has full read/write access | No database-level access control; security relies entirely on OS filesystem permissions |
| **No horizontal scaling** | No read replicas, no distributed queries, no sharding | A single server is the performance ceiling |
| **Backup = file copy** | `shutil.copy2()` at `connection.py:247`; requires closing all connections first (`connection.py:244`) | No WAL-based backup, no point-in-time recovery, no streaming replication; backup requires downtime |
| **Network filesystem unreliable** | DuckDB docs: "It is not recommended to run DuckDB in read-write mode on network-attached storage (NAS)" including NFS, SMB, Samba | Cloud deployment with EBS, EFS, or any network-attached storage risks data corruption or spurious errors |

### DuckDB's Own Documentation Confirms These Are Architectural Constraints

From the [DuckDB Concurrency Documentation](https://duckdb.org/docs/stable/connect/concurrency):

> "Writing to DuckDB from multiple processes is not supported automatically and is not a primary design goal."

> "DuckDB is optimized for bulk operations, so executing many small transactions is not a primary design goal."

> "It is not recommended to run DuckDB in read-write mode on network-attached storage (NAS)."

The documentation explicitly suggests using PostgreSQL or MySQL for multi-process OLTP workloads, with DuckDB as an analytical complement:

> "Do multi-process transactions on a MySQL, PostgreSQL, or SQLite database, and use DuckDB's MySQL, PostgreSQL, or SQLite extensions to execute analytical queries on that data periodically."

### What DuckDB IS Good For

DuckDB excels at:
- Local development and testing (fast, zero-config)
- Analytical queries on large datasets (columnar storage, vectorized execution)
- Offline batch processing and data science workflows
- Embedded analytics in desktop or CLI applications

The MotherDuck blog ["15+ Companies Using DuckDB in Production"](https://motherduck.com/blog/15-companies-duckdb-in-prod/) documents production use cases, but notably they are all **analytical/ETL workloads**, not multi-user web application backends.

---

## 4. PostgreSQL Assessment

PostgreSQL is the natural migration target because DuckDB's SQL dialect was deliberately designed for PostgreSQL compatibility.

### 4.1 Self-Hosted vs Managed

| Approach | Pros | Cons |
|---|---|---|
| **Self-hosted** (VM + apt install) | Full control, lowest cost ($20/mo VM) | Requires DevOps: backups, upgrades, monitoring, HA setup |
| **AWS RDS** | Multi-AZ HA, automated backups, PITR | Higher cost ($70-200/mo), AWS lock-in |
| **Google Cloud SQL** | Strong GCP integration, automated maintenance | No free tier, $30-150/mo |
| **Azure Flexible Server** | Cheapest managed option ($20/mo entry) | Smaller community, fewer extensions |
| **DigitalOcean Managed DB** | Simple pricing, good for small teams | Fewer enterprise features |

### 4.2 Connection Pooling

The current `DatabaseManager` uses thread-local DuckDB connections. For PostgreSQL, connection pooling is critical:

- **PgBouncer**: External pooler, works with any PostgreSQL client. Best for connection multiplexing.
- **asyncpg pool**: Native Python async pool. Best for FastAPI's async architecture.
- **psycopg3 async pool**: Newer alternative with async support and pipeline mode.

Recommendation: Use `asyncpg` with its built-in connection pool for FastAPI, with PgBouncer as an optional external layer for connection multiplexing at scale.

### 4.3 JSON/JSONB Support

All 12 JSON columns in the current schema map directly to PostgreSQL's `JSONB` type, which provides:
- Binary storage (faster reads than text JSON)
- GIN indexing for key/value lookups
- Partial updates via `jsonb_set()`
- Full-text search within JSON documents

### 4.4 PostGIS (Optional)

The observations table stores RA/Dec coordinates and the state vectors table stores ECI position vectors. PostGIS would enable:
- Spatial indexing on celestial coordinates
- Efficient range queries for satellite coverage analysis
- Geospatial aggregations for sensor field-of-view calculations

This is optional and can be added as an extension after migration.

### 4.5 Row-Level Security (RLS)

PostgreSQL's RLS policies would enable future multi-tenancy:
- Per-user data isolation without application-level filtering
- Organization-level access control
- Read-only vs read-write policies per table

### 4.6 Schema Compatibility

DuckDB's SQL was deliberately designed for PostgreSQL compatibility. Key translations needed:

| DuckDB Feature | PostgreSQL Equivalent | Effort |
|---|---|---|
| `JSON` type | `JSONB` (recommended) | Search-and-replace |
| `?` placeholders | `$1, $2` (asyncpg) or `%s` (psycopg3) | Systematic replacement |
| `INSERT OR IGNORE` | `INSERT ... ON CONFLICT DO NOTHING` | Already used in most places |
| `INSERT OR REPLACE` | `INSERT ... ON CONFLICT DO UPDATE` | Minor syntax change |
| `RETURNING id` | `RETURNING id` | Identical |
| `CREATE SEQUENCE` | `CREATE SEQUENCE` or `SERIAL`/`BIGSERIAL` | Identical or simplified |
| `EXTRACT(EPOCH FROM ...)` | `EXTRACT(EPOCH FROM ...)` | Identical |
| CTEs (`WITH RECURSIVE`) | CTEs (`WITH RECURSIVE`) | Identical |
| Window functions (`LAG`, `PARTITION BY`) | Window functions | Identical |

---

## 5. Supabase Assessment

[Supabase](https://supabase.com) is an open-source Firebase alternative built on PostgreSQL. It provides a hosted PostgreSQL database with additional platform services.

### 5.1 PostgreSQL Underneath

Supabase databases are standard PostgreSQL instances. You can:
- Connect with any `psql` client or PostgreSQL driver
- Use `pg_dump`/`pg_restore` for migrations
- Run any PostgreSQL extension (PostGIS, pgvector, etc.)
- Use the direct connection string from FastAPI (bypassing the Supabase REST API entirely)

### 5.2 Built-In Auth

This is the most significant advantage for this project. Supabase Auth solves the user tracking gap immediately:
- Email/password, magic link, social providers (Google, GitHub, etc.)
- JWT-based authentication compatible with FastAPI middleware
- User management dashboard
- Multi-factor authentication (MFA)
- Up to 50,000 MAUs on the free tier, 100,000 on Pro

### 5.3 Row-Level Security

RLS policies tied to the authenticated user's JWT:
- Per-user data isolation at the database level
- Policies like: "Users can only see datasets they created"
- Enforced even for direct SQL connections

### 5.4 Real-Time Subscriptions

WebSocket-based push notifications for database changes:
- Job progress updates pushed to the frontend (replaces current polling)
- Dataset status changes broadcast to connected clients
- Up to 200 concurrent connections on free tier, 500 on Pro

### 5.5 File Storage

S3-compatible object storage:
- Submission file uploads
- Dataset export files (JSON, Parquet)
- 1 GB free, 100 GB on Pro

### 5.6 Pricing

| Tier | Monthly Cost | Database Storage | Auth MAUs | Notes |
|---|---|---|---|---|
| **Free** | $0 | 500 MB | 50,000 | 2 projects, auto-pause after 1 week idle |
| **Pro** | $25 | 8 GB | 100,000 | Email support, 7-day backup retention |
| **Team** | $599 | 8 GB + overage | 100,000 | SOC 2, SSO, priority support with SLAs |
| **Enterprise** | Custom | Up to 60 TB | Custom | 24/7 support, HIPAA, BYO Cloud |

### 5.7 FastAPI Compatibility

Since FastAPI IS the API layer, the Supabase auto-generated REST APIs are redundant. The recommended integration pattern:
- Use the direct PostgreSQL connection string with `asyncpg`
- Use Supabase Auth for JWT-based authentication
- Use Supabase Realtime for WebSocket push (optional)
- Ignore the Supabase REST/GraphQL APIs

### 5.8 Limitations

- Auto-generated REST APIs redundant with FastAPI (adds confusion, not value)
- Complex PostgreSQL issues may get limited support from Supabase's infrastructure team
- Vendor lock-in for Auth and Realtime features (though the database itself is portable)
- Free tier auto-pauses after 1 week of inactivity

### 5.9 YC Adoption

Approximately 55-59% of YC W25 batch companies use Supabase, and over 1,000 YC companies total have used the platform. This indicates strong ecosystem momentum and community support.

**Security caveat:** A recent audit of 107 YC startups using Supabase found that 71 had misconfigured Row-Level Security, exposing 20.1M database rows to anonymous access. RLS configuration is critical and must not be overlooked.

---

## 6. Other Options

### 6.1 Neon (Serverless PostgreSQL)

[Neon](https://neon.com) is a serverless PostgreSQL platform (acquired by Databricks in May 2025) with unique capabilities:

**Key Features:**
- **Database branching**: Create instant, copy-on-write database clones for dev/staging/prod. Only divergent data costs extra storage.
- **Auto-suspend**: Scale to zero when idle, reducing costs for low-traffic periods.
- **Serverless autoscaling**: Automatically adjusts CPU/memory based on workload (up to 16 CU autoscaling, 56 CU fixed).

**Pricing:**

| Tier | Monthly Cost | Storage | Compute | Key Features |
|---|---|---|---|---|
| **Free** | $0 | 0.5 GB | 100 CU-hours | 10 branches, auto-suspend |
| **Launch** | Usage-based | $0.35/GB | $0.106/CU-hr | 16 CU max, 7-day PITR |
| **Scale** | Usage-based | $0.35/GB | $0.222/CU-hr | 56 CU max, 30-day PITR, SOC 2, 99.95% SLA |

**Strong contender because:**
- Branch-based dev/staging/prod eliminates the need for separate database instances
- Auto-suspend reduces costs during development phases
- Standard PostgreSQL -- no proprietary extensions or lock-in
- $0.35/GB storage is competitive with managed PostgreSQL providers

**Limitation:** No built-in auth (would need to build user system separately or integrate a third-party auth provider).

### 6.2 TimescaleDB

PostgreSQL extension for time-series data. Relevant for the `observations` table which is heavily time-indexed:
- **Hypertables** automatically partition by time
- **Continuous aggregates** for pre-computed rollups (e.g., observation counts per hour)
- **Compression** for historical data (10-20x space savings)

**Recommendation:** Consider as an add-on extension to whatever PostgreSQL provider is chosen. The `observations` and `state_vectors` tables would benefit from hypertable partitioning.

### 6.3 CockroachDB

Distributed SQL database with PostgreSQL wire compatibility:
- Automatic sharding and replication
- Multi-region deployment
- Strong consistency

**Assessment:** Overkill for this project's scale. The added complexity of distributed SQL is not justified when a single PostgreSQL instance can handle the workload. Revisit only if the platform needs multi-region deployment or handles millions of concurrent users.

### 6.4 PlanetScale

MySQL-based serverless database:
- No `RETURNING` clause support (used extensively in current schema)
- No CTEs in older versions (used for recursive dataset version queries)
- MySQL syntax incompatible with existing PostgreSQL-compatible SQL

**Assessment:** Incompatible. Would require rewriting all SQL queries. Not recommended.

### 6.5 Hybrid DuckDB + PostgreSQL

Use PostgreSQL for OLTP/web operations and DuckDB for offline analytics:
- PostgreSQL serves the FastAPI backend (user-facing reads/writes)
- DuckDB connects to PostgreSQL via the `postgres` extension for analytical queries
- Batch analytics (coverage analysis, observation statistics) run in DuckDB

**Assessment:** Viable but adds operational complexity. The DuckDB analytical advantages are most relevant for large-scale offline processing. For the current dataset sizes, PostgreSQL alone is sufficient. Consider this architecture only when analytical query performance becomes a bottleneck.

---

## 7. Cost Comparison Matrix

| Provider | Free Tier | Entry Paid | Production | Auth Included | Key Trade-Off |
|---|---|---|---|---|---|
| **Self-hosted** | $0 + ops | $20/mo VM | $100/mo HA | No | Full control vs DevOps burden |
| **AWS RDS** | None | $70/mo | $200/mo Multi-AZ | No | Enterprise features vs cost |
| **Google Cloud SQL** | None | $30/mo | $150/mo HA | No | GCP integration |
| **Azure Flexible** | None | $20/mo | $120/mo HA | No | Cheapest managed option |
| **DigitalOcean** | None | $15/mo | $80/mo HA | No | Simple, affordable |
| **Supabase** | 500 MB free | $25/mo Pro | $599/mo Team | **Yes** | Auth + Storage included vs vendor coupling |
| **Neon** | 0.5 GB free | ~$19/mo | ~$69/mo | No | Serverless + branching vs no auth |

**Notes on cost estimates:**
- "Entry Paid" assumes a small database (< 10 GB) with low traffic
- "Production" assumes HA/multi-AZ, automated backups, and moderate traffic
- Supabase Pro includes 8 GB storage, auth, and real-time; the jump to Team ($599) is steep
- Neon pricing is usage-based; $19/mo assumes ~180 CU-hours + 5 GB storage on Launch tier
- Self-hosted costs assume a single VM; HA requires at least 2 VMs + load balancer

---

## 8. Migration Complexity Assessment

### 8.1 Schema Translation: Minimal

DuckDB SQL is deliberately PostgreSQL-compatible. The main changes:

| Change | Scope | Complexity |
|---|---|---|
| `JSON` -> `JSONB` | 12 columns | Search-and-replace |
| `?` -> `$1,$2` (asyncpg) or `%s` (psycopg3) | All queries in `repository.py` | Systematic, ~80 queries |
| `INSERT OR IGNORE` -> `ON CONFLICT DO NOTHING` | Already done in most places | Verify only |
| `INSERT OR REPLACE` -> `ON CONFLICT DO UPDATE` | `schema.py:710` (schema metadata) | 1-2 occurrences |
| `INTEGER PRIMARY KEY DEFAULT nextval(...)` -> `SERIAL` or `BIGSERIAL` | 11 sequences | Simplification |
| `BOOLEAN DEFAULT FALSE` | Identical syntax | No change |
| `DECIMAL(p,s)` | Identical syntax | No change |
| `VARCHAR(n)` | Identical syntax | No change |
| `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | Identical syntax | No change |

### 8.2 Connection Rewrite

The `DatabaseManager` class must change from thread-local DuckDB connections to an async connection pool:

**Current** (`connection.py`):
```python
self._local = threading.local()
self._lock = threading.Lock()
# ...
self._local.connection = duckdb.connect(str(self.db_path))
```

**Target**:
```python
self._pool = await asyncpg.create_pool(dsn=connection_string, min_size=5, max_size=20)
# ...
async with self._pool.acquire() as conn:
    result = await conn.fetch(query, *params)
```

This is the single largest code change -- `DatabaseManager` and all repository methods must become `async`.

### 8.3 Repository Compatibility

The raw SQL repository pattern survives migration. Methods become `async` but the SQL structure remains:

**Current**:
```python
def get(self, sat_no: int) -> Optional[pd.Series]:
    df = self.to_dataframe("SELECT * FROM satellites WHERE sat_no = ?", (sat_no,))
    return df.iloc[0] if len(df) > 0 else None
```

**Target**:
```python
async def get(self, sat_no: int) -> Optional[dict]:
    row = await self.fetchone("SELECT * FROM satellites WHERE sat_no = $1", sat_no)
    return dict(row) if row else None
```

### 8.4 Bulk Insert

DuckDB's `register()` pattern for DataFrame ingestion must change:

**Current** (`repository.py:391-406`):
```python
conn.register("temp_obs_df", insert_df)
conn.execute("INSERT INTO observations (...) SELECT ... FROM temp_obs_df")
conn.unregister("temp_obs_df")
```

**Target** (PostgreSQL `COPY` protocol):
```python
await conn.copy_records_to_table('observations', records=records, columns=columns)
```

Or using `execute_values()` with psycopg3 for smaller batches.

### 8.5 Testing

**Current**: In-memory DuckDB (`DatabaseManager(in_memory=True)`)

**Target options**:
- **Test containers**: Spin up a real PostgreSQL container per test suite (most accurate)
- **Neon branches**: Create a branch per test run (if using Neon)
- **SQLite fallback**: Not recommended (too many syntax differences)

### 8.6 Migration Effort Summary

| Component | Files Affected | Estimated Difficulty |
|---|---|---|
| Schema translation | `schema.py` | Low -- mostly search-and-replace |
| Placeholder syntax | `repository.py`, `workers.py`, `credential_service.py` | Low -- systematic replacement |
| DatabaseManager async rewrite | `connection.py` | Medium -- architectural change |
| Repository async conversion | `repository.py` | Medium -- 6 classes, ~40 methods |
| FastAPI dependency injection | `backend_api/database.py` | Low -- swap `get_db()` for async pool |
| Bulk insert rewrite | `repository.py` (3 bulk_insert methods) | Medium -- different protocol |
| Worker thread model | `workers.py` | Medium -- may need async task queue |
| Test infrastructure | All test files | Medium -- container or branch setup |

---

## 9. Production Readiness -- New Tables Required

Regardless of database choice, the following tables must be added for production readiness.

### 9.1 `users` Table

Basic user tracking and authentication support.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(100),
    role VARCHAR(20) NOT NULL DEFAULT 'user',  -- admin, user, viewer
    password_hash VARCHAR(255),                 -- bcrypt or argon2
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

**Impact on existing tables** -- add `created_by UUID REFERENCES users(id)` to:
- `datasets` -- who triggered generation
- `submissions` -- who submitted the algorithm
- `uctp_runs` -- who started the UCTP run
- `credentials` -- who last modified credentials (separate from the service definition)

### 9.2 `audit_log` Table

Full mutation audit trail for every create, update, and delete operation.

```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(10) NOT NULL,               -- CREATE, UPDATE, DELETE
    resource_type VARCHAR(50) NOT NULL,        -- datasets, submissions, credentials, etc.
    resource_id VARCHAR(100) NOT NULL,         -- ID of the affected resource
    details JSONB,                              -- old/new values, change diff
    ip_address INET,
    user_agent TEXT,
    request_method VARCHAR(10),                -- GET, POST, PUT, DELETE
    request_path VARCHAR(500),
    response_status SMALLINT,
    duration_ms INTEGER
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_action ON audit_log(action);
```

**Implementation:** FastAPI middleware wrapping every mutating request. Before/after snapshots stored in `details` JSONB column.

### 9.3 `api_call_log` Table

Persistent external API call tracking, replacing the in-memory `MetricsCollector._api_calls` list and `_api_call_metrics` dict.

```sql
CREATE TABLE api_call_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    service_name VARCHAR(50) NOT NULL,         -- UDL, ESA, SpaceTrack, SatNOGS, GCAT, ILRS
    endpoint VARCHAR(500),
    request_params JSONB,
    response_status SMALLINT,
    response_size_bytes INTEGER,
    records_returned INTEGER,
    duration_ms INTEGER,
    error_message TEXT,
    job_id VARCHAR(100),                       -- References jobs(id)
    user_id UUID REFERENCES users(id),
    credential_source VARCHAR(20)              -- database, environment, none
);

CREATE INDEX idx_api_call_timestamp ON api_call_log(timestamp);
CREATE INDEX idx_api_call_service ON api_call_log(service_name);
CREATE INDEX idx_api_call_job ON api_call_log(job_id);
```

**Integration:** Replace `_api_call_metrics["call_history"].append(call_record)` in `apiIntegration.py:110` and `MetricsCollector._api_calls.append()` in `logging_config.py:137` with database inserts.

### 9.4 `query_log` Table

Read query and pagination tracking to enable answering: "What exact data did someone see on page 3?"

```sql
CREATE TABLE query_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID REFERENCES users(id),
    endpoint VARCHAR(500) NOT NULL,
    query_params JSONB,                        -- filters, search terms
    result_count INTEGER,
    page_offset INTEGER,
    page_limit INTEGER,
    duration_ms INTEGER,
    cache_hit BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_query_timestamp ON query_log(timestamp);
CREATE INDEX idx_query_user ON query_log(user_id);
CREATE INDEX idx_query_endpoint ON query_log(endpoint);
```

**Implementation:** FastAPI middleware or dependency that logs every GET request with pagination parameters.

### 9.5 `credential_access_log` Table

Audit trail for all credential operations.

```sql
CREATE TABLE credential_access_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    service_name VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,               -- resolve, save, delete, validate
    source VARCHAR(20),                        -- database, environment, none
    user_id UUID REFERENCES users(id),
    success BOOLEAN NOT NULL,
    error_message TEXT,
    ip_address INET
);

CREATE INDEX idx_cred_access_timestamp ON credential_access_log(timestamp);
CREATE INDEX idx_cred_access_service ON credential_access_log(service_name);
CREATE INDEX idx_cred_access_user ON credential_access_log(user_id);
```

**Integration:** Modify `CredentialService.resolve()` (`credential_service.py:267`), `save_credentials()` (line 190), and `delete_credentials()` (line 229) to insert audit records.

### 9.6 `system_log` Table

Persistent structured logging for errors and warnings, replacing console-only loguru output.

```sql
CREATE TABLE system_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    level VARCHAR(10) NOT NULL,                -- ERROR, WARNING, INFO
    message TEXT NOT NULL,
    module VARCHAR(100),
    function_name VARCHAR(100),
    line_number INTEGER,
    exception TEXT,
    extra JSONB                                -- structured context data
);

CREATE INDEX idx_syslog_timestamp ON system_log(timestamp);
CREATE INDEX idx_syslog_level ON system_log(level);
CREATE INDEX idx_syslog_module ON system_log(module);
```

**Implementation:** Custom loguru sink that writes ERROR and WARNING level messages to the database. INFO and DEBUG continue to console/file only to avoid excessive database writes.

---

## 10. Dataset Generation Provenance Deep-Dive

### 10.1 What IS Tracked Today

The `datasets.generation_params` JSON column stores generation configuration. From `workers.py:308-336`, the `generateDataset()` call receives:

- **Regime**: Orbital regime (LEO, MEO, GEO, HEO)
- **Tier**: T1-T5
- **Object count**: Number of satellites requested
- **Satellites**: List of NORAD IDs (auto-selected or specified)
- **Timeframe**: Duration in days
- **End time**: "now" or specific datetime
- **Search strategy**: hybrid, windowed, etc.
- **Window size**: In minutes
- **Downsampling config**: target_coverage, target_gap, max_obs_per_sat, preserve_tracks, seed
- **Simulation config**: apply_noise, sensor_model, max_synthetic_ratio, seed
- **Enrichment report**: enriched_count, skipped_count, hamr_detected (from `workers.py:178-180`)

The `datasets` table also stores:
- `observation_count`, `satellite_count`, `avg_coverage`
- `status` (created -> processing -> available -> failed)
- `time_window_start`, `time_window_end`
- `downsampling_applied`, `simulation_applied`, `simulated_obs_count`

### 10.2 What's Missing for Full Reproducibility

| Missing Element | Why It Matters | Where to Add |
|---|---|---|
| **`created_by` user** | No record of who triggered generation | `datasets.created_by UUID` |
| **Every external API call** (URLs, params, response sizes, timestamps) | Cannot trace which UDL/ESA/SpaceTrack calls produced the data | `api_call_log` table linked to `jobs.id` |
| **Raw API response checksums** | Cannot verify data integrity or detect API changes | `api_call_log.response_checksum` field |
| **Credential source used** | Was the DB-encrypted or env-variable credential used? | `api_call_log.credential_source` field |
| **Exact software version / git commit hash** | Cannot reproduce results with a different code version | `datasets.generation_params.git_commit` |
| **Python version and key dependency versions** | Package updates may change numerical results | `datasets.generation_params.environment` |
| **Orekit data version** | Orekit's Earth orientation and gravity models affect propagation | `datasets.generation_params.orekit_version` |
| **Random seed used for satellite selection** | Auto-selection uses `random.shuffle()` at `workers.py:141` without a fixed seed | `datasets.generation_params.selection_seed` |
| **API rate limit pauses** | `dt=0.5` delay is applied but actual wait times not recorded | `api_call_log` timestamps |
| **Cache hits during generation** | If cached data was used, the API call log is incomplete | `api_call_log` or separate cache hit log |

### 10.3 Provenance Improvement Roadmap

1. **Immediate**: Add `created_by` to `datasets` table and populate from authenticated user
2. **Short-term**: Persist all API call records to `api_call_log` during dataset generation
3. **Medium-term**: Capture git commit hash and environment info in `generation_params`
4. **Long-term**: Implement full data lineage tracking with checksums for API responses

---

## 11. Recommendation

### Primary Recommendation: Supabase (PostgreSQL)

For the UCT Benchmark / SDA-TAP-SPOC platform, **Supabase** is the recommended production database platform, with the following rationale:

| Factor | Assessment |
|---|---|
| **Migration effort** | Low -- DuckDB SQL is PostgreSQL-compatible; schema translation is mostly search-and-replace |
| **User system gap** | Supabase Auth solves the most critical production gap immediately (no custom auth code needed) |
| **Cost** | $25/mo Pro tier covers 8 GB database + auth + storage + real-time -- competitive for an all-in-one platform |
| **Vendor lock-in** | Moderate -- database is standard PostgreSQL (portable), but Auth and Realtime features create soft lock-in |
| **FastAPI compatibility** | Use direct PostgreSQL connection string; ignore Supabase REST APIs |
| **Real-time capabilities** | WebSocket subscriptions replace job polling -- direct improvement to user experience |
| **SDA domain needs** | PostgreSQL handles the observation/satellite data model well; JSONB covers complex generation params |
| **Scaling path** | Pro -> Team -> Enterprise covers growth from development through production |
| **Community** | 55%+ of YC W25 companies use Supabase; strong ecosystem and documentation |

### Alternative Recommendation: Neon

If built-in auth is not a priority (e.g., the team plans to implement auth separately), **Neon** is a strong alternative:
- Database branching eliminates the need for separate dev/staging/prod databases
- Auto-suspend reduces costs during development phases
- Usage-based pricing is more predictable at low scale
- Standard PostgreSQL with no proprietary extensions

### What NOT to Do

- **Do not continue with DuckDB for production** -- the single-writer, single-process architecture is a hard blocker for multi-user web deployment.
- **Do not choose PlanetScale** -- MySQL incompatibility with existing SQL would require a full rewrite.
- **Do not choose CockroachDB** -- distributed SQL is unnecessary complexity at this scale.
- **Do not attempt a hybrid DuckDB + PostgreSQL architecture initially** -- the added operational complexity is not justified until analytical performance becomes a bottleneck.

### Implementation Priority

1. Add the 6 production tracking tables (Section 9) -- these are needed regardless of database choice
2. Implement user authentication and `created_by` tracking
3. Migrate schema from DuckDB to PostgreSQL (on chosen platform)
4. Convert `DatabaseManager` to async connection pool
5. Convert repositories to async methods
6. Add audit logging middleware to FastAPI
7. Persist API call metrics to database
8. Add credential access logging

---

## References

### DuckDB Documentation
- [DuckDB Concurrency](https://duckdb.org/docs/stable/connect/concurrency) -- Single-writer process model, multi-process limitations, network filesystem warnings
- [DuckDB Environment](https://duckdb.org/docs/stable/guides/performance/environment) -- Storage recommendations, NAS warnings

### Production Use Cases
- [15+ Companies Using DuckDB in Production (MotherDuck)](https://motherduck.com/blog/15-companies-duckdb-in-prod/) -- All analytical/ETL workloads, not multi-user web backends

### Provider Comparisons
- [Best PostgreSQL Hosting Providers (Northflank)](https://northflank.com/blog/best-postgresql-hosting-providers)
- [PostgreSQL Hosting Pricing Comparison (Bytebase)](https://www.bytebase.com/blog/postgres-hosting-options-pricing-comparison/)
- [Top Managed PostgreSQL Services Compared (Seenode)](https://seenode.com/blog/top-managed-postgresql-services-compared)

### Supabase
- [Supabase Official Pricing](https://supabase.com/pricing)
- [Supabase Review 2026 (Hackceleration)](https://hackceleration.com/supabase-review/)
- [PostgreSQL vs Supabase Deployment Guide (Leanware)](https://www.leanware.co/insights/postgresql-vs-supabase-deployment-guide-startups)
- [FastAPI + Supabase Stack Discussion (HN)](https://news.ycombinator.com/item?id=42353177)
- [1000 YC Founders Choose Supabase](https://supabase.com/blog/1000-yc-companies)

### Neon
- [Neon Official Pricing](https://neon.com/pricing)
- [Neon Plans Documentation](https://neon.com/docs/introduction/plans)
- [Neon Serverless Postgres Pricing 2026](https://vela.simplyblock.io/articles/neon-serverless-postgres-pricing-2026/)

---

## Codebase Files Referenced

| File | Lines | Description |
|---|---|---|
| `uct_benchmark/database/schema.py` | 936 | All 20 table definitions, schema version 1.3.0 |
| `uct_benchmark/database/connection.py` | 364 | DatabaseManager with thread-local connections and threading.Lock |
| `uct_benchmark/database/repository.py` | 1618 | 6 repository classes, all raw SQL |
| `backend_api/database.py` | 140 | FastAPI singleton + lifespan manager |
| `backend_api/services/credential_service.py` | 323 | Fernet encryption, env fallback, resolve chain |
| `backend_api/jobs/workers.py` | 703 | ThreadPoolExecutor, dataset generation, evaluation |
| `uct_benchmark/api/apiIntegration.py` | ~2600 | External API calls, in-memory metrics, query cache |
| `uct_benchmark/logging_config.py` | ~400 | MetricsCollector with in-memory _api_calls list |
| `uct_benchmark/settings.py` | 608 | Configuration dataclasses, cache TTL defaults |
