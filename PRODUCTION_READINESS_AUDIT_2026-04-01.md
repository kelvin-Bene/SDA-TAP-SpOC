# UCT Benchmark -- Production Readiness Audit

**Date**: 2026-04-01
**Scope**: Full-stack audit (Security, Auth, Code Quality, Documentation, Alignment, Infrastructure, Database, Tests)
**Methodology**: 8 parallel deep-dive agents, each reading every relevant source file and cross-referencing against web best practices

---

## Executive Summary

**Overall Production Readiness: ~60% -- NOT ready for public demo without fixes**

The UCT Benchmark application has a solid foundation -- a working FastAPI backend, polished React frontend, Supabase integration, and a scientifically rigorous evaluation pipeline that is ~95% aligned with Louis's benchmarking documentation. However, the audit uncovered **critical security vulnerabilities, data integrity gaps, and infrastructure issues** that must be resolved before production exposure.

| Audit Area | Findings | Critical | High | Medium | Low | Health |
|---|---|---|---|---|---|---|
| Security & Auth | 23 | 3 | 6 | 8 | 6 | POOR |
| Vision Alignment | -- | -- | -- | -- | -- | 75% aligned |
| Documentation | 30+ files | 0 | 3 | 4 | 2 | PARTIAL |
| Backend Code | 32 | 5 | 7 | 10 | 10 | FAIR |
| Frontend Code | 30 | 4 | 7 | 11 | 10 | FAIR |
| Infrastructure | 24 | 1 | 4 | 9 | 9 | FAIR |
| Database | 28 | 4 | 12 | 9 | 3 | POOR |
| Test Coverage | 17 | 3 | 4 | 6 | 4 | POOR |
| **TOTALS** | **~184** | **20** | **43** | **57** | **44** | -- |

---

## TOP 20 MUST-FIX ISSUES (Ordered by Priority)

These are the issues that MUST be resolved before any production demo or public exposure.

### 1. IDOR: Any user can overwrite any submission's results
- **Severity**: CRITICAL | **Area**: Security
- **File**: `backend_api/routers/submissions.py:475-596`
- **Issue**: `POST /{submission_id}/results` has NO user ownership check. Any authenticated user can replace any other user's submission results.
- **Fix**: Add `WHERE id = ? AND user_id = ?` to the submission lookup.

### 2. IDOR: Entire results router has no user authorization
- **Severity**: CRITICAL | **Area**: Security
- **File**: `backend_api/routers/results.py` (all 6 endpoints)
- **Issue**: Any authenticated user can view ANY user's results, metrics, visualizations, and reports. No `user_id` filtering anywhere.
- **Fix**: Add `user_id` filtering to all queries. Allow admin bypass.

### 3. PostgreSQL init skips all inline migrations
- **Severity**: CRITICAL | **Area**: Database
- **File**: `uct_benchmark/database/schema.py:688-703`
- **Issue**: `_initialize_postgres_schema()` reads the SQL file but never calls `_migrate_to_1_2_0` through `_migrate_to_1_6_0`. Fresh PostgreSQL databases are missing dozens of columns.
- **Fix**: Add migration calls after SQL file execution, or update `schema_postgres.sql` to include all columns.

### 4. Missing `profiles` table schema definition
- **Severity**: CRITICAL | **Area**: Backend
- **File**: `uct_benchmark/database/schema.py` (missing), `backend_api/routers/auth.py:274-313` (uses it)
- **Issue**: The `profiles` table is never created by `initialize_schema()`. Every auth endpoint crashes on a fresh database with "relation profiles does not exist."
- **Fix**: Add `PROFILES_TABLE` to schema.py and include in initialization.

### 5. Zero Supabase Row Level Security (RLS) policies
- **Severity**: CRITICAL | **Area**: Database
- **File**: All schema files -- no `CREATE POLICY` anywhere
- **Issue**: No RLS policies exist. Any direct Supabase connection can read/write ALL tables without restriction.
- **Fix**: Add RLS policies for all user-owned tables (datasets, submissions, results, feedback).

### 6. No foreign key constraints on any table
- **Severity**: CRITICAL | **Area**: Database
- **File**: `uct_benchmark/database/schema.py` (all table definitions)
- **Issue**: Zero `FOREIGN KEY` constraints. Orphaned rows, dangling references, ability to delete datasets while submissions reference them.
- **Fix**: Add FK constraints with appropriate CASCADE/RESTRICT rules.

### 7. Dual auth systems with inconsistent admin checks
- **Severity**: HIGH | **Area**: Security + Backend
- **Files**: `backend_api/auth.py` (CurrentUser) vs `backend_api/middleware/auth.py` (AuthUser)
- **Issue**: Two different user models check admin status differently (`role == "admin"` vs `app_metadata.is_admin`). Different routers use different models.
- **Fix**: Consolidate into a single auth module and user class.

### 8. Database connection is NOT thread-safe (single connection shared)
- **Severity**: CRITICAL | **Area**: Database + Backend
- **File**: `uct_benchmark/database/adapters/postgres_adapter.py:65`
- **Issue**: PostgresAdapter uses a single `self._connection` shared across threads. Workers and API requests contend for the same connection. DuckDB adapter correctly uses `threading.local()` but PostgreSQL does not.
- **Fix**: Implement `psycopg2.pool.ThreadedConnectionPool` or use `threading.local()`.

### 9. Rate limiting can be bypassed via X-Forwarded-For spoofing
- **Severity**: HIGH | **Area**: Security
- **File**: `backend_api/middleware/rate_limit.py:16-28`
- **Issue**: Rate limiter trusts client-supplied `X-Forwarded-For` header. Attacker can send a different fake IP per request.
- **Fix**: Only trust the rightmost IP in the chain, or configure the proxy to strip client headers.

### 10. Alembic migrations never run on deploy
- **Severity**: HIGH | **Area**: Infrastructure
- **File**: `start.py`, `Dockerfile`
- **Issue**: Neither the startup script nor the Dockerfile runs `alembic upgrade head`. Schema changes require manual intervention.
- **Fix**: Add `alembic upgrade head` to `start.py` before uvicorn starts.

### 11. No automated database backups
- **Severity**: HIGH | **Area**: Infrastructure
- **File**: `scripts/backup_db.sh` (exists but never scheduled)
- **Issue**: Backup script exists but is never run automatically. No cron, no CI schedule, no Railway cron.
- **Fix**: Schedule via GitHub Actions cron or Railway cron service.

### 12. 80% of tests are NOT run in CI
- **Severity**: CRITICAL | **Area**: Testing
- **File**: `.github/workflows/deploy.yml`
- **Issue**: Only `test_auth.py` + `test_feedback.py` (47 tests) are blocking in CI. ~180+ other tests are either non-blocking or not run at all. Frontend tests are never executed.
- **Fix**: Add all `backend_api/tests/` to strict pytest run. Add `npm test -- --run` step.

### 13. Three competing migration systems
- **Severity**: HIGH | **Area**: Database
- **Files**: `alembic/versions/`, `migrations/*.sql`, `schema.py` inline migrations
- **Issue**: Alembic, raw SQL files, and inline Python migrations all overlap with no coordination. Impossible to know true schema state.
- **Fix**: Consolidate ALL migrations into Alembic.

### 14. All timestamps lack timezone (TIMESTAMP vs TIMESTAMPTZ)
- **Severity**: HIGH | **Area**: Database
- **File**: All table definitions
- **Issue**: Every `TIMESTAMP` column is without timezone. Interpretation depends on server timezone setting.
- **Fix**: Migrate all to `TIMESTAMPTZ`.

### 15. Dev auth bypass could leak to production
- **Severity**: MEDIUM | **Area**: Security
- **File**: `backend_api/middleware/auth.py:66-76`
- **Issue**: `ENVIRONMENT=development` completely bypasses auth with a stub user. If this env var leaks to production, all auth is disabled.
- **Fix**: Add guard: refuse dev mode if Supabase URL is configured.

### 16. Token refresh causes full page navigation (destroys form state)
- **Severity**: CRITICAL | **Area**: Frontend
- **File**: `frontend/src/api/client.ts:99-101, 113-115`
- **Issue**: Failed token refresh does `window.location.href = '/login'` -- even for background API calls. Users filling out forms lose all work.
- **Fix**: Use React Router `navigate()` or only redirect on user-initiated requests.

### 17. Single-worker bottleneck
- **Severity**: HIGH | **Area**: Infrastructure
- **File**: `start.py:9` (WEB_WORKERS=1)
- **Issue**: App is locked to 1 worker because JobManager is in-memory. Single crash loses all job state.
- **Fix**: Migrate to Redis/PostgreSQL-backed task queue.

### 18. CSP blocks Cesium 3D viewer
- **Severity**: MEDIUM | **Area**: Infrastructure
- **File**: `frontend/nginx.conf.template:15`
- **Issue**: CSP `connect-src` doesn't include `*.cesium.com`. OrbitViewer fails in production.
- **Fix**: Add `https://*.cesium.com` to CSP connect-src.

### 19. Documentation describes wrong auth architecture
- **Severity**: HIGH | **Area**: Documentation
- **Files**: `API_INTEGRATION.md`, `BACKEND_API.md`, `FRONTEND.md`
- **Issue**: Multiple docs describe localStorage-based auth. Actual code uses Supabase client-side auth with JWKS verification.
- **Fix**: Rewrite auth documentation sections.

### 20. `.env.example` leaks real Supabase project reference
- **Severity**: HIGH | **Area**: Security
- **File**: `.env.example:51`
- **Issue**: Contains the actual Supabase project ref `csuqtcizjfsmkoeevyau` which is committed to git.
- **Fix**: Replace with placeholder `[YOUR-PROJECT-REF]`.

---

## DETAILED AUDIT RESULTS BY AREA

---

## A. Security & Authentication Audit

### Authentication Flow Issues
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| S1 | CRITICAL | `submissions.py:475` | IDOR: No user check on upload_results |
| S2 | CRITICAL | `results.py` (all) | IDOR: No user filtering on any results endpoint |
| S3 | HIGH | `middleware/auth.py:38-44` | Dual role trust model -- reads role from top-level JWT claim (user-modifiable) |
| S4 | HIGH | `auth.py` vs `middleware/auth.py` | Two different admin checks: `role == "admin"` vs `app_metadata.is_admin` |
| S5 | MEDIUM | `middleware/auth.py:66-76` | Dev bypass returns stub user -- could leak to production |
| S6 | LOW | `auth.py:133-136` | HS256 fallback is opt-in but weaker than ES256 |

### CORS & CSRF
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| S7 | HIGH | `main.py:72-80` | CORS defaults to localhost -- will break if CORS_ORIGINS not set in prod |
| S8 | MEDIUM | `main.py:248-254` | `allow_credentials=True` with broad methods widens attack surface |
| S9 | MEDIUM | Entire app | No CSRF protection (mitigated by Bearer token usage) |

### Rate Limiting
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| S10 | HIGH | `middleware/rate_limit.py:16-28` | X-Forwarded-For spoofing bypasses rate limits |
| S11 | MEDIUM | `routers/feedback.py:31-53` | In-process rate limiter bypassed with multiple workers |
| S12 | LOW | `routers/feedback.py:59-62` | Feedback limiter uses proxy IP, creating global limit |

### Input Validation
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| S13 | MEDIUM | `routers/results.py:47-97` | Unclamped limit/offset allows DoS via memory exhaustion |
| S14 | MEDIUM | `routers/datasets.py:218` | Sort direction interpolated in f-string (currently safe, fragile) |
| S15 | LOW | `routers/feedback.py:69-75` | Regex-based HTML sanitization is incomplete |

### Secrets & Data Exposure
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| S16 | CRITICAL | `.env` (local) | Live production credentials in plaintext (mitigated by .gitignore) |
| S17 | HIGH | `.env.example:51` | Real Supabase project ref committed to git |
| S18 | MEDIUM | `auth.py:46` | JWKS URL logged at startup |
| S19 | MEDIUM | `routers/datasets.py:614,641` | Error messages expose raw exception details |

### Session & Token Management
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| S20 | MEDIUM | `frontend/lib/supabase.ts:16` | Tokens in localStorage (accessible to XSS) |
| S21 | LOW | `api/client.ts:31-124` | Forced signout after 3 failed refreshes in 60s |

### Frontend Security
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| S22 | LOW | `LoginPage.tsx:225-229` | Password min length mismatch (placeholder: 6, validation: 8) |
| S23 | LOW | `stores/authStore.ts:35` | Client-side admin check bypassable (backend enforces independently) |

---

## B. Vision Alignment Audit

**Overall Alignment: ~75%**

### What is Well-Aligned (Strengths)
- **Evaluation pipeline: 95% aligned** -- All 19 metrics from Louis's benchmarking doc implemented correctly
- **Orbit association**: Uses `scipy.optimize.linear_sum_assignment` (Jonker-Volgenant) as specified
- **All orbital propagation algorithms** match spec: DormandPrince853, Holmes-Featherstone, NRLMSISE-00, Monte Carlo
- **16-character dataset code system**: Fully implemented with all 10 parameters
- **T1/T2 dataset generation**: Window selection, 3-stage downsampling, scoring all work
- **Web platform exceeds original scope**: React frontend with 13 pages vs original customtkinter concept

### Critical Gaps
| # | Feature | Alignment | Issue |
|---|---------|-----------|-------|
| V1 | Orekit in production | 60% | Java dependency marked optional -- T2/T3/T4 tiers will fail in web deployment |
| V2 | T3/T4 tier integration | 60% | Simulation code exists but web workflow integration incomplete |
| V3 | Event labeling | 15% | Infrastructure exists but no real event data source |
| V4 | Sensor diversity | Optical only | Intentional per Louis -- until pipeline proven |
| V5 | End-to-end PDF report | Unverified | Not verified to produce PDF report in production web deployment |
| V6 | Space-Track integration | Present | Code exists, but TLE querying not fully tested in web pipeline |

---

## C. Documentation Audit

### Summary Statistics
| Category | Count |
|----------|-------|
| Total docs audited | 30+ |
| ACCURATE | 14 |
| PARTIALLY ACCURATE | 13 |
| INACCURATE | 2 (API_INTEGRATION.md, BACKEND_API.md) |
| Orphaned from mkdocs nav | 8 |
| Non-existent files referenced | 4 (windowCheck.py, windowTools.py, Create_Dataset.py, MainMVP.py) |
| Critical undocumented topics | 9 |

### Key Issues
| # | Sev | Issue |
|---|-----|-------|
| D1 | HIGH | Auth architecture described as localStorage-based in 4 docs (actual: Supabase JWKS) |
| D2 | HIGH | 4 non-existent files referenced in ARCHITECTURE.md and PIPELINE.md |
| D3 | HIGH | 8 docs orphaned from mkdocs.yml navigation |
| D4 | MEDIUM | Frontend port inconsistency (5173 vs 3000) across docs |
| D5 | MEDIUM | Database described as DuckDB-only in some docs vs dual-backend in others |
| D6 | MEDIUM | Changelog split across two files with different content |

### Undocumented Topics
1. Deployment procedures (Railway, Docker, CI/CD)
2. Supabase authentication architecture
3. Feedback system
4. Rate limiting
5. Security headers
6. Sentry integration
7. Encrypted token storage
8. Audit logging
9. Request correlation IDs

---

## D. Backend Code Quality Audit

### Critical Issues
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| B1 | CRITICAL | `schema.py` | Missing `profiles` table -- auth crashes on fresh DB |
| B2 | CRITICAL | `submissions.py:475` | IDOR on upload_results |
| B3 | CRITICAL | `results.py` (all) | IDOR on all results endpoints |
| B4 | CRITICAL | `postgres_adapter.py:65` | Single non-thread-safe connection shared across threads |
| B5 | CRITICAL | `results.py:86` | `ILIKE` not supported on DuckDB -- crashes dataset filter |

### High Issues
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| B6 | HIGH | Multiple routers | PostgreSQL-specific `INTERVAL` syntax incompatible with DuckDB |
| B7 | HIGH | `results.py`, `feedback.py` | Unclamped limit/offset allows DoS |
| B8 | HIGH | `models/feedback.py:43` | FeedbackUpdate status has no enum validation |
| B9 | HIGH | `jobs/__init__.py:65` | In-memory job manager loses state on restart |
| B10 | HIGH | `main.py:180,236` | BaseHTTPMiddleware has known performance issues |
| B11 | HIGH | `submissions.py:170` | No cleanup for old uploaded files (disk exhaustion) |
| B12 | HIGH | `feedback.py:31-53` | Rate limiter memory leak (never cleans stale entries) |

### Medium Issues (10 findings)
- Dual auth systems, unvalidated int() conversions, download loads all observations into memory, no total count in paginated responses, error messages leak internal paths, RANK() without NULLS LAST, duplicate token validation logic, format shadows builtin, DuckDB schema missing app_version, dual migration systems conflict.

---

## E. Frontend Code Quality Audit

### Critical Issues
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| F1 | CRITICAL | `vite-env.d.ts:3-7` | Supabase env vars missing from TypeScript declarations |
| F2 | CRITICAL | `LoginPage.tsx:41` | Race condition -- 100ms setTimeout for auth state propagation |
| F3 | CRITICAL | `lib/supabase.ts:16` | Supabase client created with empty strings when env vars missing |
| F4 | CRITICAL | `api/client.ts:99-101` | Token refresh redirects via `window.location.href` destroying form state |

### High Issues
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| F5 | HIGH | `DatasetGeneratorPage.tsx` | `catch (error: any)` bypasses TypeScript (3 instances) |
| F6 | HIGH | `LoginPage.tsx:56-229` | Password validation inconsistency (6 vs 8 chars) |
| F7 | HIGH | `ProfilePage.tsx:66-84` | Fake API key with working Copy/Regenerate buttons |
| F8 | HIGH | `DatasetFilters.tsx:67` | No debouncing on search -- fires API call per keystroke |
| F9 | HIGH | `MyDatasetsPage.tsx:130-135` | Delete mutation has no error handling |
| F10 | HIGH | `FeedbackWidget.tsx:284` | `navigator.platform` is deprecated |
| F11 | HIGH | `LeaderboardPage.tsx:63-69` | Sorting bug -- position RMS direction inverted |

### Medium Issues (11 findings)
- ErrorBoundary reset doesn't re-mount, useActionLogger monkey-patches history, leaked object URL in downloads, trend data key collision, no pagination on lists, theme provider doesn't listen for system changes, sidebar not synced on route change, static/hardcoded statistics in dataset preview, unnecessary API calls in sidebar, useEffect search param re-render risk.

### Good Practices Already in Place
- Lazy loading with Suspense boundaries
- Error boundaries with Sentry integration
- React Query with sensible stale times
- Token refresh mutex
- No `dangerouslySetInnerHTML` usage (zero XSS risk)
- Good `sr-only` usage for screen readers

---

## F. Infrastructure & Deployment Audit

### Critical
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| I1 | CRITICAL | `.env` (local) | Live credentials in plaintext (mitigated by .gitignore) |

### High
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| I2 | HIGH | `nginx.conf:24-25` | Hardcoded Railway production URL in committed file |
| I3 | HIGH | `Dockerfile`/`start.py` | Alembic migrations never run on deploy |
| I4 | HIGH | CI workflow | VITE_API_BASE_URL may miss /api/v1 suffix |
| I5 | HIGH | `scripts/backup_db.sh` | Backup script exists but is never automated |
| I6 | HIGH | `start.py:9` | Single worker bottleneck (WEB_WORKERS=1) |

### Medium
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| I7 | MEDIUM | CI workflow | No linting (ruff, eslint) in CI |
| I8 | MEDIUM | CI workflow | No frontend tests in CI |
| I9 | MEDIUM | CI workflow | Non-blocking deployment verification |
| I10 | MEDIUM | CI workflow | No security scanning (pip-audit, npm audit) |
| I11 | MEDIUM | CI workflow | No staging environment |
| I12 | MEDIUM | `nginx.conf.template:15` | CSP blocks Cesium 3D viewer |
| I13 | MEDIUM | `frontend/Dockerfile` | Docker Compose nginx has no security headers |
| I14 | MEDIUM | `.env.example` | Production env vars not fully documented |
| I15 | MEDIUM | General | No rollback procedure documented |

---

## G. Database & Migration Audit

### Critical
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| DB1 | CRITICAL | All schema files | No FOREIGN KEY constraints on any table |
| DB2 | CRITICAL | `schema.py:688-703` | PostgreSQL init skips all inline migrations |
| DB3 | CRITICAL | All schema files | Zero Supabase RLS policies |
| DB4 | CRITICAL | `results.py`, `submissions.py:476` | Multiple endpoints missing auth (IDOR) |

### High
| # | Sev | Location | Issue |
|---|-----|----------|-------|
| DB5 | HIGH | All schema files | No CHECK constraints on enum columns |
| DB6 | HIGH | `alembic/`, `migrations/`, `schema.py` | Three competing migration systems |
| DB7 | HIGH | `alembic/env.py` | Alembic has no target_metadata (autogenerate broken) |
| DB8 | HIGH | `postgres_adapter.py` | Not a connection pool despite parameters |
| DB9 | HIGH | `postgres_adapter.py:65` | Single connection shared across threads |
| DB10 | HIGH | `postgres_adapter.py:356,401` | SQL injection risk in get_row_count/vacuum_analyze |
| DB11 | HIGH | Junction tables | No CASCADE deletes |
| DB12 | HIGH | `datasets.py:191` | answer_key (ground truth) fetched via SELECT * |
| DB13 | HIGH | All timestamps | TIMESTAMP without timezone |
| DB14 | HIGH | `connection.py:220-253` | No PostgreSQL backup/restore mechanism |
| DB15 | HIGH | `schema_postgres.sql` | Missing many columns present in DuckDB schema |
| DB16 | HIGH | `submissions.py:281` | IDOR via `user_id IS NULL` fallback |

---

## H. Test Coverage Audit

### Coverage Summary
| Area | Tested | Untested | Coverage |
|------|--------|----------|----------|
| Backend API routers | 7/7 | 0 | 100% |
| Backend middleware | 0/3 | 3 | 0% |
| Backend utilities | 0/3 | 3 | 0% |
| Frontend pages | 3/13 | 10 | 23% |
| Frontend hooks | 3/7 | 4 | 43% |
| Frontend components | 1/15 | 14 | 7% |
| CI blocking tests | 47/230+ | 180+ | 20% |

### Critical
| # | Sev | Issue |
|---|-----|-------|
| T1 | CRITICAL | 10 of 13 frontend pages have ZERO tests |
| T2 | CRITICAL | No frontend tests run in CI at all |
| T3 | CRITICAL | ~100 backend API tests not in CI strict run |

### High
| # | Sev | Issue |
|---|-----|-------|
| T4 | HIGH | Auth tests use dependency overrides -- real JWT flow never tested |
| T5 | HIGH | All 3 middleware modules completely untested |
| T6 | HIGH | Crypto and token validation utilities untested |
| T7 | HIGH | E2E tests use soft assertions (never fail) and aren't in CI |

---

## PRIORITIZED ACTION PLAN

### Phase 1: Security Hotfixes (Do First -- 1-2 days)
1. Fix IDOR on `upload_results` (add user_id check)
2. Fix IDOR on all results endpoints (add user_id filtering)
3. Consolidate dual auth systems into one module
4. Fix X-Forwarded-For rate limit bypass
5. Sanitize `.env.example` (remove real Supabase project ref)
6. Add dev-mode guard (refuse if SUPABASE_URL is set)

### Phase 2: Database Critical Fixes (2-3 days)
7. Add `profiles` table to schema.py
8. Fix PostgreSQL init to run inline migrations
9. Implement connection pooling (ThreadedConnectionPool)
10. Add FOREIGN KEY constraints via Alembic migration
11. Add RLS policies for user-owned tables
12. Consolidate migration systems into Alembic only
13. Migrate TIMESTAMP to TIMESTAMPTZ

### Phase 3: Infrastructure Hardening (1-2 days)
14. Add `alembic upgrade head` to start.py
15. Add all backend tests to CI strict run
16. Add frontend test run to CI
17. Fix CSP for Cesium
18. Remove hardcoded Railway URL from nginx.conf
19. Automate database backups
20. Fix VITE_API_BASE_URL to always include /api/v1

### Phase 4: Frontend Bug Fixes (1-2 days)
21. Fix token refresh to use React Router navigate
22. Fix LoginPage auth race condition
23. Fix Supabase client empty string creation
24. Add env vars to vite-env.d.ts
25. Fix leaderboard sorting bug
26. Add debouncing to dataset search
27. Fix password validation inconsistency
28. Remove/disable fake API key feature

### Phase 5: Documentation Update (1 day)
29. Rewrite auth documentation (4 files)
30. Remove references to non-existent files
31. Add 8 orphaned docs to mkdocs.yml
32. Consolidate changelogs
33. Document deployment, feedback, rate limiting, security headers

### Phase 6: Test Coverage Improvement (2-3 days)
34. Write tests for all untested frontend pages
35. Write middleware unit tests
36. Write crypto/token validation tests
37. Fix E2E tests (hard assertions, add to CI)
38. Test real JWT validation flow

---

## WHAT'S WORKING WELL

Despite the issues above, significant parts of the application are solid:

1. **Evaluation pipeline** is scientifically rigorous and ~95% aligned with the benchmarking spec
2. **16-character dataset code system** is fully implemented and validated
3. **Security headers** (X-Frame-Options, HSTS, X-Content-Type-Options) are properly configured on the backend
4. **React Query** configuration with sensible stale times and garbage collection
5. **Token refresh mutex** prevents duplicate refresh attempts
6. **Lazy loading** for all page components with Suspense boundaries
7. **Error boundaries** at global and route levels with Sentry integration
8. **Backend auth router** has excellent test coverage (31 tests)
9. **Feedback system** includes XSS sanitization, rate limiting, and admin RBAC
10. **Frontend design** is polished with proper responsive layout and dark mode

---

*Generated by comprehensive 8-agent parallel audit on 2026-04-01*
