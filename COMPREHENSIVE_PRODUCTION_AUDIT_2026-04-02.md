# UCT Benchmark (SpOC) - Comprehensive Production Readiness Audit

**Date:** 2026-04-02
**Auditor:** Claude Opus 4.6 (8-agent parallel audit)
**Scope:** Security, Auth, Backend, Frontend, Database, CI/CD, Documentation, Vision Alignment, Best Practices

---

## Executive Summary

| Audit Area | Grade | Critical | High | Medium | Low |
|---|---|---|---|---|---|
| Security & Auth | **D** | 6 | 9 | 9 | 7 |
| Backend Code | **C** | 1 | 4 | 4 | 1 |
| Frontend Code | **C+** | 0 | 2 | 3 | 5 |
| Database & Schema | **D+** | 3 | 5 | 6 | 3 |
| CI/CD & Deployment | **D** | 6 | 8 | 4 | 0 |
| Documentation | **C-** | 2 | 4 | 4 | 3 |
| Vision Alignment | **B** | 0 | 2 | 3 | 0 |
| **TOTALS** | | **18** | **34** | **33** | **19** |

**Overall Production Readiness: ~45%** -- The core domain logic is strong (evaluation metrics, data pipeline, scoring), but security, database integrity, deployment reliability, and documentation have significant gaps that must be addressed before a production showcase.

---

## SECTION 1: CRITICAL FINDINGS (Must Fix Before Production)

These 18 findings represent risks of data loss, security bypass, or application failure.

### SEC-01: SQL Injection in postgres_adapter.py
- **File:** `uct_benchmark/database/adapters/postgres_adapter.py:377-379, 417-425`
- **Issue:** `get_row_count()` and `vacuum_analyze()` use f-string interpolation for table names: `f"SELECT COUNT(*) FROM {table_name}"`. `bulk_insert_df()` (line 309-340) also interpolates table/column names.
- **Impact:** Full SQL injection if any user input reaches these methods.
- **Fix:** Add a whitelist validation function that checks table names against `information_schema.tables`.

### SEC-02: Development Auth Bypass One Env Var Away
- **File:** `backend_api/middleware/auth.py:72-88`
- **Issue:** When `ENVIRONMENT=development` and no `SUPABASE_JWT_SECRET` is set, auth is entirely bypassed returning a stub user. One misconfigured environment variable in production = complete auth bypass.
- **Fix:** Add a hard guard: refuse to start if `ENVIRONMENT=development` and `DATABASE_BACKEND=postgres`.

### SEC-03: Plaintext Token Storage Without ENCRYPTION_KEY
- **File:** `backend_api/auth.py` (crypto module)
- **Issue:** When `DATABASE_BACKEND` is not postgres/supabase, API tokens (UDL/ESA) are stored in plaintext. `encrypt_token()` falls through to `return plaintext`.
- **Fix:** Require `ENCRYPTION_KEY` for all backends or refuse to store tokens.

### SEC-04: No Row-Level Security in PostgreSQL
- **File:** `uct_benchmark/database/schema_postgres.sql` (entire file)
- **Issue:** Zero `ENABLE ROW LEVEL SECURITY` or `CREATE POLICY` statements. If Supabase PostgREST is enabled, any authenticated user can bypass all app-level access controls.
- **Fix:** Add RLS policies for `datasets`, `submissions`, `submission_results`, `feedback`, and `profiles`.

### SEC-05: IDOR via NULL user_id in Submissions
- **File:** `backend_api/routers/submissions.py:281`
- **Issue:** `WHERE s.user_id IS NULL` condition means any submission without a user_id is accessible to ALL authenticated users.
- **Fix:** Remove the `IS NULL` fallback or require all submissions to have a user_id.

### SEC-06: Leaderboard Exposes All Users' Submission Data
- **File:** `backend_api/routers/leaderboard.py` (entire file)
- **Issue:** No user-scoping on any leaderboard endpoint. Combined with IDOR above, enables data harvesting.
- **Fix:** Evaluate if this is intended behavior; if not, add user filtering options.

### BE-01: Non-Admin Users Can NEVER See Their Own Jobs
- **File:** `backend_api/routers/jobs.py:33, 111`
- **Issue:** Job ownership checks `job.metadata.get("user_id") != user.id`, but neither `submit_dataset_generation` nor `submit_evaluation` stores `user_id` in job metadata. `None != user.id` is always True, so non-admin users get 404 on ALL their jobs.
- **Impact:** UI job progress polling is completely broken for regular users.
- **Fix:** Add `"user_id": user.id` to job metadata in both `submit_dataset_generation` and `submit_evaluation`.

### DB-01: No Foreign Key Constraints in Base Schema
- **File:** `uct_benchmark/database/schema_postgres.sql`, `schema.py`
- **Issue:** FK relationships are documented as comments only. Migration 003 adds 5 of ~15 needed FKs. Orphan records can accumulate silently.
- **Fix:** Add all FK constraints with proper ON DELETE actions.

### DB-02: Orphan Records - No Cascade Deletes
- **File:** `uct_benchmark/database/schema_postgres.sql`
- **Issue:** Deleting a dataset leaves orphaned `dataset_observations`, `submissions`, `submission_results`, `jobs`, etc.
- **Fix:** Add `ON DELETE CASCADE` for child tables, `ON DELETE SET NULL` where appropriate.

### DB-03: Feedback Schema Mismatch (app_version column)
- **File:** `uct_benchmark/database/schema.py` vs `schema_postgres.sql`
- **Issue:** `app_version` column exists in PostgreSQL schema but not DuckDB schema. `feedback.py:142` inserts into it. DuckDB tests must manually add it.
- **Fix:** Add `app_version VARCHAR(50)` to `FEEDBACK_TABLE` in `schema.py`.

### CD-01: No Concurrency Control on Deploy Workflow
- **File:** `.github/workflows/deploy.yml`
- **Issue:** Two simultaneous pushes to master can trigger parallel deploys, causing inconsistent backend/frontend versions or concurrent migrations.
- **Fix:** Add `concurrency: { group: deploy-production, cancel-in-progress: false }`.

### CD-02: Database Migrations Run Without Locking
- **File:** `UCT-Benchmark-DMR/combined/start.py:25`
- **Issue:** `alembic upgrade head` runs during container startup with no advisory lock. Multiple replicas = concurrent migration execution = potential data corruption.
- **Fix:** Add `SELECT pg_advisory_lock(12345)` before migration in `alembic/env.py`.

### CD-03: Migration Failure Silently Swallowed
- **File:** `UCT-Benchmark-DMR/combined/start.py:30-36`
- **Issue:** If `alembic upgrade head` fails, the error is printed but the app starts anyway, serving requests against the wrong schema.
- **Fix:** `sys.exit(1)` on non-zero migration returncode.

### CD-04: Dual Migration Systems (Alembic + Raw SQL)
- **File:** `alembic/versions/` + `migrations/`
- **Issue:** Alembic and raw SQL migrations exist with overlapping version numbers (both have 003, 004). No coordination between them.
- **Fix:** Consolidate into Alembic only; archive raw SQL files.

### CD-05: Deploy Verification is Non-Blocking
- **File:** `.github/workflows/deploy.yml`
- **Issue:** Both backend and frontend verification steps use `continue-on-error: true`. A completely broken deploy shows as successful CI.
- **Fix:** Remove `continue-on-error` or add a mandatory health check gate.

### CD-06: No Staging Environment
- **File:** `.github/workflows/deploy.yml`
- **Issue:** Changes go directly from master push to production. No staging gate, no PR-required deployment.
- **Fix:** Add a staging deploy step or require PR approvals before merge to master.

---

## SECTION 2: HIGH SEVERITY FINDINGS (Should Fix Before Production)

### Security & Auth (9 findings)

| ID | Finding | File | Fix |
|---|---|---|---|
| SEC-07 | Missing security headers in docker nginx.conf | `frontend/nginx.conf` | Copy headers from `nginx.conf.template` |
| SEC-08 | Rate limiting bypass via X-Forwarded-For spoofing | `middleware/rate_limit.py:23-29` | Validate proxy depth or use Railway's IP |
| SEC-09 | In-memory rate limiter doesn't scale | `feedback.py:31-53` | Use Redis or database-backed rate limiting |
| SEC-10 | Missing limit/offset validation on feedback list | `feedback.py:200-202` | Clamp `limit` to max 100 |
| SEC-11 | Error messages leak internal details | `datasets.py:623`, `submissions.py:389` | Return generic error messages |
| SEC-12 | JWT algorithm confusion risk (ES256/HS256 fallback) | `auth.py:104-152` | Remove HS256 fallback entirely |
| SEC-13 | No account lockout after failed logins | Auth system | Add rate limiting on auth/verify |
| SEC-14 | Missing content-type validation for uploads | `submissions.py:354-359` | Validate magic bytes, not just MIME |
| SEC-15 | Dataset download without ownership check | `datasets.py:936-967` | Add user_id filter or document as intended |

### Backend Code (4 findings)

| ID | Finding | File | Fix |
|---|---|---|---|
| BE-02 | `db._connection.rollback()` accesses nonexistent attribute | `workers.py:557` | Use `db.execute("ROLLBACK")` or adapter method |
| BE-03 | DuckDB incompatible SQL (`%s` placeholders, `ILIKE`, `INTERVAL`) | `workers.py:512`, `results.py:95`, `datasets.py:60` | Add dialect-aware query builder |
| BE-04 | Dual auth user classes (CurrentUser vs AuthUser) | `auth.py` vs `middleware/auth.py` | Consolidate into one user model |
| BE-05 | Download endpoint loads all observations into memory | `datasets.py:985` | Use streaming response with cursor |

### Database (5 findings)

| ID | Finding | File | Fix |
|---|---|---|---|
| DB-04 | Naive TIMESTAMP (no timezone) in base schema | `schema_postgres.sql` | Change to TIMESTAMPTZ in base schema |
| DB-05 | No CHECK constraints anywhere | All schemas | Add status, progress, confidence constraints |
| DB-06 | Missing NOT NULL on required fields | Multiple tables | Add NOT NULL where code treats as required |
| DB-07 | FK migration 003 may fail on existing orphan data | `alembic/versions/003` | Add cleanup queries before FK creation |
| DB-08 | Missing composite indexes for leaderboard/filtering | Schema | Add 12 recommended indexes (see DB audit) |

### CI/CD (8 findings)

| ID | Finding | File | Fix |
|---|---|---|---|
| CD-07 | No pip dependency caching | `deploy.yml` | Add `actions/cache` for pip |
| CD-08 | Legacy pipeline tests never fail the build | `deploy.yml:29-34` | Make blocking or explicitly document |
| CD-09 | E2E tests entirely non-blocking | `e2e.yml` | Make blocking after stabilization |
| CD-10 | Security scans non-blocking | `security.yml` | Make HIGH/CRITICAL findings blocking |
| CD-11 | No automatic rollback mechanism | Deployment | Add rollback documentation and automation |
| CD-12 | Frontend deployed even if backend verification fails | `deploy.yml` | Add dependency gate |
| CD-13 | Backups only in GitHub artifacts (30-day retention) | `backup.yml` | Add S3/durable storage |
| CD-14 | No alerting on deploy/backup failure | All workflows | Add Slack/email notifications |

### Frontend (2 findings)

| ID | Finding | File | Fix |
|---|---|---|---|
| FE-01 | Legacy code endpoint uses raw `fetch`, bypassing auth | `DatasetGeneratorPage.tsx:491` | Use `apiClient` instead of `fetch` |
| FE-02 | MyDatasetsPage fetches ALL datasets, not user-scoped | `MyDatasetsPage.tsx:31` | Filter by current user_id |

### Documentation (4 findings)

| ID | Finding | File | Fix |
|---|---|---|---|
| DOC-01 | BACKEND_API.md auth endpoints are wrong | `docs/technical/BACKEND_API.md` | Rewrite with actual endpoints |
| DOC-02 | API_INTEGRATION.md code examples are stale | `docs/API_INTEGRATION.md` | Update to match actual client.ts |
| DOC-03 | reports/CHANGELOG.md missing v2.0.0 entry | `docs/reports/CHANGELOG.md` | Sync with root CHANGELOG |
| DOC-04 | ARCHITECTURE.md and DATABASE.md describe DuckDB-only | `docs/technical/` | Update for dual-backend |

### Vision Alignment (2 findings)

| ID | Finding | File | Fix |
|---|---|---|---|
| VA-01 | No composite scoring for leaderboard | `backend_api/routers/leaderboard.py` | Implement weighted composite metric per Louis's spec |
| VA-02 | Orekit not available in production (Railway) | Deployment | Java/Orekit needed for state metrics & residuals |

---

## SECTION 3: MEDIUM SEVERITY FINDINGS (Fix Soon After Launch)

### Security (9)
- Supabase token stored in localStorage (XSS vulnerable)
- No CSRF tokens (mitigated by Bearer-only auth)
- Temp file cleanup race condition in report generation
- OpenAPI/Swagger docs exposed in development mode
- CORS defaults overly permissive when env var missing
- Missing authorization on some dataset operations
- CSP allows `unsafe-inline` for styles
- `allow_credentials=True` with permissive CORS
- Missing `autocomplete` attributes on password fields

### Backend (4)
- Unbounded memory growth in feedback rate limiter
- Double JWT validation per request (two auth systems)
- Tests use DuckDB but production uses PostgreSQL
- `create_test_app()` mutates global singleton

### Frontend (3)
- DatasetFilters slider uses `defaultValue` (won't reset on clear)
- DatasetPreviewDialog shows hardcoded mock statistics
- `__APP_VERSION__` may be undefined if Vite config missing

### Database (6)
- JSON vs JSONB mismatch between schemas
- Missing `app_version` in DuckDB schema
- Inconsistent column naming (`ob_time` vs `obs_time`)
- Missing UNIQUE on `datasets.code`
- PostgreSQL fallback init wrong parameter count
- N+1 query in dataset version tree

### CI/CD (4)
- Docker image not multi-stage build
- No container image scanning
- Nginx missing proxy buffer settings
- No structured log aggregation

### Documentation (4)
- CONFIGURATION.md missing v2.0.0 env vars
- LIMITATIONS.md not in mkdocs nav
- INTEGRATED_ROADMAP phases outdated
- full-system-pipeline.md says 4 workers (actual is 1)

### Vision (3)
- Event-based dataset filtering not implemented
- Target object percentage not enforced
- Tier 3/4 simulation only partially integrated

---

## SECTION 4: FRONTEND SPECIFIC ISSUES

### UX Issues
1. No auto-refresh for in-progress submissions on MySubmissionsPage
2. No pagination on DatasetBrowserPage
3. Leaderboard podium not mobile-responsive (`grid-cols-3` hardcoded)
4. "Notifications" and "Security" tabs show non-functional UI
5. No form dirty-state tracking on ProfilePage
6. "Change Avatar" button has no functionality
7. Coverage bar invisible for very small values (<0.02%)
8. File validation uses artificial delays (`await delay(300/400/500)`)

### Accessibility Issues
1. Sortable table headers not keyboard-accessible (missing `tabIndex`, `onKeyDown`)
2. No keyboard-accessible way to trigger Preview/Download on DatasetCard
3. Icon-only buttons missing `aria-label` attributes
4. Mobile sidebar overlay doesn't trap focus
5. Login error messages not announced to screen readers (missing `role="alert"`)
6. Podium section has no semantic markup for rankings
7. Slider missing `aria-label`
8. Color-only status indicators (colorblind inaccessible)

### Performance Concerns
1. Sidebar calls `useSubmissions()` on every page load
2. LeaderboardPage fetches ALL datasets just for dropdown
3. DatasetGeneratorPage is 700+ lines (should be split)
4. No `React.memo` usage anywhere
5. Cesium (1.4MB) in dependencies but `OrbitViewer` not referenced from any route
6. `transform.ts` exports are entirely dead code

### Code Quality
1. Duplicated download error handling in 3 pages
2. Duplicated `getRankIcon` in 2 files
3. Hardcoded announcement content in DashboardPage
4. `usePolling.ts` hook defined but never used
5. Inconsistent date formatting functions
6. "Documentation" appears twice in sidebar nav

---

## SECTION 5: TEST COVERAGE GAPS

| Gap | Severity | Current State |
|---|---|---|
| No tests for submission creation (POST /submissions/) | HIGH | Zero coverage |
| No tests for dataset creation (POST /datasets/) | HIGH | Zero coverage |
| No integration tests for evaluation pipeline | HIGH | Zero coverage |
| No tests for feedback endpoints | HIGH | Zero coverage |
| No tests for auth token validation/rejection | HIGH | Zero coverage |
| No tests for dataset download | MEDIUM | Zero coverage |
| Job ownership test only uses admin users | HIGH | Bug #BE-01 uncaught |
| Tests use DuckDB but prod uses PostgreSQL | HIGH | SQL dialect bugs uncaught |
| `test_list_jobs_invalid_type_filter` asserts wrong status | MEDIUM | Test is incorrect |
| `test_list_results_zero_limit` may be unreliable | LOW | Boundary condition |

---

## SECTION 6: VISION ALIGNMENT SUMMARY

**Overall: 78% aligned with Louis's vision**

### Fully Implemented (correct)
- All 19 evaluation metrics (8 binary, 6 state, residual modes)
- All 6 core algorithms (Jonker-Volgenant, DormandPrince853, Monte Carlo, etc.)
- All 13 configuration constants (LEO/MEO/GEO thresholds, etc.)
- 16-character dataset code system with 10 fields
- Tier 1-5 classification system
- Web platform (13 pages, exceeding original desktop GUI vision)
- UDL API integration for data ingestion

### Missing/Partial
1. **Composite leaderboard scoring** -- Ranks by F1 only, not weighted composite of binary + state + residual
2. **Orekit in production** -- Java/Orekit needed for state metrics and residuals
3. **Event-based filtering** -- DB infrastructure exists but no event data source
4. **Non-optical sensor support** -- Optical-only in practice
5. **Target percentage enforcement** -- Schema supports it but pipeline doesn't enforce

### Positive Deviations
- Desktop GUI replaced with React web app (addresses Louis's "remote server" goal)
- PDF-only reports expanded to PDF + JSON + web visualization
- Single UDL data source expanded to UDL + Space-Track + CelesTrak

---

## SECTION 7: DOCUMENTATION HEALTH

**Overall accuracy: ~70%**

| Status | Count |
|---|---|
| Accurate (no issues) | 18 docs |
| Partially outdated | 15 docs |
| Significantly outdated | 8 docs |
| Missing topics | 5 |
| Cross-doc inconsistencies | 10 |

### Critical Doc Issues
1. **BACKEND_API.md** documents auth endpoints that don't exist (`/login`, `/logout`, `/refresh`)
2. **API_INTEGRATION.md** has stale code examples using localStorage auth
3. **ARCHITECTURE.md** and **DATABASE.md** describe DuckDB-only (prod uses PostgreSQL)
4. **Schema version** documented as 1.0.0 (actual: 1.6.0)

### Missing Documentation
1. Production deployment guide (Railway, env vars, start.py)
2. Authentication & authorization architecture
3. Feedback system API documentation
4. Alembic migration guide
5. Complete API reference (only ~40% of endpoints documented)

---

## SECTION 8: OWASP TOP 10 COMPLIANCE

| Category | Status | Key Issues |
|---|---|---|
| A01: Broken Access Control | **FAIL** | IDOR via NULL user_id, no RLS, missing ownership checks |
| A02: Cryptographic Failures | **PARTIAL** | Plaintext tokens possible, localStorage for sessions |
| A03: Injection | **PARTIAL** | SQL injection in postgres_adapter (f-strings), routers OK |
| A04: Insecure Design | **PASS** | Architecture is sound, Supabase delegation correct |
| A05: Security Misconfiguration | **FAIL** | Dev bypass risk, missing headers, exposed docs |
| A06: Vulnerable Components | **UNKNOWN** | No dependency audit in CI (scans are non-blocking) |
| A07: Auth Failures | **PARTIAL** | No lockout, HS256 fallback risk, dev bypass |
| A08: Data Integrity | **PASS** | File validation, Fernet encryption, Alembic |
| A09: Logging & Monitoring | **PARTIAL** | Audit logging exists, missing security alerting |
| A10: SSRF | **PASS** | No user-supplied URLs fetched server-side |

---

## SECTION 9: PRIORITIZED ACTION PLAN

### Phase 0: Emergency Fixes (Before any demo)
1. Fix job ownership bug (BE-01) -- users can't see their own job progress
2. Fix MyDatasetsPage showing all users' datasets (FE-02)
3. Fix legacy endpoint auth bypass (FE-01)

### Phase 1: Security Hardening (1-2 days)
4. Sanitize SQL in postgres_adapter.py (SEC-01)
5. Guard against dev auth bypass in production (SEC-02)
6. Require ENCRYPTION_KEY for all backends (SEC-03)
7. Add RLS policies in Supabase (SEC-04)
8. Fix IDOR in submissions (SEC-05)
9. Copy security headers to docker nginx.conf (SEC-07)
10. Consolidate dual auth system (BE-04)

### Phase 2: Database Integrity (1-2 days)
11. Add all foreign key constraints (DB-01)
12. Add cascade deletes (DB-02)
13. Fix schema mismatches (DB-03)
14. Add CHECK constraints (DB-05)
15. Add recommended indexes (DB-08)
16. Add NOT NULL constraints (DB-06)

### Phase 3: Deployment Reliability (1 day)
17. Add deploy concurrency control (CD-01)
18. Add migration locking (CD-02)
19. Make migration failure fatal (CD-03)
20. Consolidate migration systems (CD-04)
21. Add deploy failure alerting (CD-14)
22. Document rollback procedure (CD-11)

### Phase 4: Documentation (1-2 days)
23. Rewrite BACKEND_API.md with actual endpoints
24. Update API_INTEGRATION.md code examples
25. Update ARCHITECTURE.md and DATABASE.md for PostgreSQL
26. Create auth architecture documentation
27. Create production deployment guide
28. Sync changelogs

### Phase 5: Vision Alignment (2-3 days)
29. Implement composite leaderboard scoring
30. Evaluate Orekit deployment options (Docker sidecar?)
31. Enforce target percentage in pipeline

### Phase 6: Polish (ongoing)
32. Fix frontend UX issues (pagination, mobile, accessibility)
33. Add missing tests (submissions, datasets, feedback, auth)
34. Implement proper connection pooling
35. Add container image scanning to CI
36. Set up external uptime monitoring

---

## APPENDIX: Best Practices Checklist

A complete 159-item best practices checklist (researched from 60+ authoritative 2025-2026 sources) has been saved to:
`PRODUCTION_BEST_PRACTICES_AUDIT_CHECKLIST.md`

Categories covered: FastAPI, React/TypeScript, PostgreSQL/Supabase, Docker, Railway, OWASP, CI/CD, REST API Design.

---

*Generated by 8-agent parallel audit on 2026-04-02. Each agent read every relevant file in the codebase.*
