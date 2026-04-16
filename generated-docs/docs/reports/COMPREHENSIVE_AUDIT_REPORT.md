# UCT Benchmark (SpOC) -- Comprehensive Production Readiness Audit

**Date:** 2026-04-01
**Scope:** Full-stack deep audit across 8 domains
**Total Findings:** 195+ issues across all categories

---

## Executive Summary

This audit examined every file in the UCT Benchmark project across 8 dimensions: security, alignment with original vision, documentation accuracy, backend code quality, frontend code quality, data pipeline correctness, testing coverage, and infrastructure/DevOps. The project has a **strong scientific core** (~85-90% aligned with Louis Caves' original vision) but has **critical gaps in security, testing, and operational readiness** that must be addressed before production use.

### Findings by Severity

| Severity | Security | Backend | Frontend | Pipeline | Testing | Infra | Total |
|----------|----------|---------|----------|----------|---------|-------|-------|
| CRITICAL | 3 | 5 | 3 | 4 | 3 | 4 | **22** |
| HIGH | 7 | 10 | 7 | 7 | 4 | 8 | **43** |
| MEDIUM | 8 | 14 | 10 | 10 | -- | 8 | **50** |
| LOW | 7 | 10 | 9 | 8 | -- | 6 | **40** |

**Documentation:** 13 inaccuracies, 14 outdated items, 8 missing topics, 11 contradictions, 9 quality issues = **55 doc issues**

**Alignment:** 20 features aligned, 4 divergent, 6 missing, 6 added beyond scope, 5 alignment risks

---

## TOP 15 MOST CRITICAL ISSUES (Fix Before Showing to Anyone)

### 1. CI pipeline `|| true` swallows ALL test failures
- **File:** `.github/workflows/deploy.yml:25`
- **Impact:** Tests never gate deployments. 100% test failure still deploys to production.
- **Fix:** Remove `|| true`

### 2. Dev-mode auth bypass if env vars are missing
- **File:** `backend_api/middleware/auth.py:68-80`
- **Impact:** If `SUPABASE_JWT_SECRET` is unset, ANY token authenticates as a valid user with full access.
- **Fix:** Refuse to start in production without auth config. Require explicit `ENVIRONMENT=development` flag.

### 3. Two parallel auth modules with different security behaviors
- **File:** `backend_api/auth.py` vs `backend_api/middleware/auth.py`
- **Impact:** Routers import from different auth modules. One has dev-mode bypass, the other doesn't. Confusion leads to bypass risk.
- **Fix:** Consolidate to a single auth module.

### 4. No JWT issuer verification
- **File:** `backend_api/auth.py:100-105`
- **Impact:** JWTs from other Supabase projects with `audience="authenticated"` could authenticate.
- **Fix:** Add `issuer=f"{supabase_url}/auth/v1"` to `jwt.decode()`.

### 5. Space-Track query is completely broken -- parameters silently ignored
- **File:** `uct_benchmark/api/apiIntegration.py:1256`
- **Impact:** `str.join()` return value discarded. Every Space-Track query sends unfiltered requests.
- **Fix:** Replace `requestFind.join(...)` with `requestFind += f"/{k.upper()}/{v}"` in a loop.

### 6. SQL placeholder mismatch -- feedback router uses `%s`, all others use `?`
- **File:** `backend_api/routers/feedback.py` (all queries)
- **Impact:** Either the feedback router or ALL other routers are broken at runtime, depending on which style the DB adapter supports.
- **Fix:** Standardize to one placeholder style across all routers.

### 7. `getattr(request, ...)` reads HTTP Request object instead of Pydantic model
- **File:** `backend_api/routers/datasets.py:529-539`
- **Impact:** User-provided dataset config values (object_type_code, event_code, etc.) are silently ignored. All datasets get default values.
- **Fix:** Change `request` to `dataset_request`.

### 8. Race condition: background job starts before transaction commits
- **File:** `backend_api/routers/datasets.py:607-625`
- **Impact:** Worker may not see the dataset row because INSERT hasn't committed yet. Sporadic "Dataset not found" errors.
- **Fix:** Move `submit_dataset_generation()` after `COMMIT`.

### 9. ZERO authentication tests in the entire test suite
- **Impact:** 23+ auth-protected endpoints have never been tested for auth enforcement. No test verifies that unauthenticated requests are rejected.
- **Fix:** Create `backend_api/tests/test_auth.py` covering all auth paths.

### 10. Backend API tests never run in CI
- **File:** `.github/workflows/deploy.yml:25` -- only `tests/` is targeted, not `backend_api/tests/`
- **Impact:** All backend API tests are invisible to CI.
- **Fix:** Change to `pytest tests/ backend_api/tests/`

### 11. Docker containers run as root
- **Files:** All Dockerfiles (backend, frontend, deploy-dist)
- **Impact:** Container compromise gives root access.
- **Fix:** Add `USER` directive with non-root user.

### 12. `np.arccos` without clipping in Gauss IOD -- NaN propagation
- **File:** `uct_benchmark/simulation/gauss.py:157, 225-226, 453-454`
- **Impact:** Floating-point rounding causes NaN, corrupting all downstream orbit determination.
- **Fix:** Wrap with `np.clip(..., -1.0, 1.0)`.

### 13. Orekit modules crash at import on non-Java systems
- **Files:** `uct_benchmark/utils/unitConversion.py:9-28`, `uct_benchmark/utils/generateCov.py:13-28`
- **Impact:** Importing these modules on CI, web frontend, or lightweight workers crashes the process immediately.
- **Fix:** Wrap Orekit init in try/except like `apiIntegration.py` does.

### 14. No IDOR protection on submissions -- any user can access any submission
- **File:** `backend_api/routers/submissions.py` (all endpoints)
- **Impact:** Any authenticated user can view, modify, or re-upload results for any other user's submissions.
- **Fix:** Add `user_id` column to submissions and filter by authenticated user.

### 15. Token refresh subscribers hang forever on failure
- **File:** `frontend/src/api/client.ts:71-109`
- **Impact:** When token refresh fails, queued API requests remain as unresolved promises forever. The app appears frozen.
- **Fix:** Reject all queued subscribers in failure paths before clearing the array.

---

## DOMAIN 1: SECURITY & AUTHENTICATION

### Critical (3)
| ID | Issue | File | Line |
|----|-------|------|------|
| S-C1 | Dev-mode auth bypass when env vars missing | middleware/auth.py | 68-80 |
| S-C2 | Two parallel auth modules create bypass risk | auth.py + middleware/auth.py | -- |
| S-C3 | No JWT issuer verification | auth.py | 100-105 |

### High (7)
| ID | Issue | File | Line |
|----|-------|------|------|
| S-H1 | IDOR: No user-scoped access on submissions/results | submissions.py, results.py | all |
| S-H2 | Any user can PATCH any dataset's coverage | datasets.py | 845-879 |
| S-H3 | Any user can link-observations to any dataset | datasets.py | 782 |
| S-H4 | Admin role from client-writable user_metadata | authStore.ts | 33, 76-78 |
| S-H5 | HS256 fallback weakens ES256 security | auth.py | 119-132 |
| S-H6 | File upload extension not allowlisted | submissions.py | 351-352 |
| S-H7 | Feedback SQL uses `%s`, others use `?` | feedback.py | 131-161 |

### Medium (8)
| ID | Issue | File |
|----|-------|------|
| S-M1 | No Content-Security-Policy header | main.py |
| S-M2 | Rate limiting only on 3 endpoints | multiple routers |
| S-M3 | Encryption key falls back to plaintext silently | crypto.py |
| S-M4 | Temp files from PDF generation never cleaned up | results.py |
| S-M5 | SQL ILIKE f-string in leaderboard history | leaderboard.py:163 |
| S-M6 | CORS allows credentials with potentially wide origins | main.py:207-213 |
| S-M7 | Supabase client created with empty strings when env missing | supabase.ts:3-4 |
| S-M8 | Jobs endpoint exposes all jobs to all users | jobs.py:14-114 |

---

## DOMAIN 2: ALIGNMENT WITH ORIGINAL VISION

### Alignment Score: ~85-90%

**Implemented & Aligned (20 items):** CTF architecture, 16-char dataset code, orbital regimes (LEO/MEO/GEO/HEO), tier system (1-5), bisection window selection, orbit association (Jonker-Volgenant), all 6 state metrics, all 8 binary classification metrics, residual metrics, decorrelation, true negatives, all 4 data sources (UDL/ESA/CelesTrak/Space-Track), 3-metric downsampling, observation simulation, Orekit propagator, atmospheric refraction/aberration, object type filtering (HAMR/Close/Apparent/Calibration), 30 calibration satellites, PDF reports, track gap definition.

**Missing / Not Implemented (6 items):**
1. Event types (Maneuver/Breakup/Long-Duration) -- infrastructure only, no detection
2. Radar and RF observation types -- pipeline only queries optical
3. Covariance propagation Monte Carlo Earth-interior rejection -- needs verification
4. Full Modified Gauss Method with BatchLSEstimator -- implementation unclear
5. Complete frame conversion (all 6 types) -- needs verification
6. Target object percentage enforcement (50%/10%/1%) -- not evident in window selection

**Alignment Risks:**
- Leaderboard creates relative rankings; Louis wanted absolute performance reporting
- UI allows radar/RF and event type selection but data is optical-only -- misleading
- `uctp/dummyUCTP.py` should never contain a real UCTP implementation (black-box principle)

---

## DOMAIN 3: DOCUMENTATION

### Top Issues
1. **Auth listed as "Not Started 0%"** everywhere -- it's fully implemented
2. **Port 5173 vs 3000** -- vite.config.ts uses 3000 but 3 docs say 5173
3. **Wrong PostgreSQL driver** -- docs say pg8000, code uses psycopg2-binary
4. **API endpoints wrong** -- docs list /auth/login, /auth/logout that don't exist
5. **CHANGELOG stops at v1.2.0** -- project is at v2.0.0
6. **8 missing topics:** auth system, feedback system, deployment, rate limiting, security headers, CORS, Sentry, demo mode

---

## DOMAIN 4: BACKEND API CODE QUALITY

### Critical (5)
| ID | Issue | File | Line |
|----|-------|------|------|
| B-C1 | SQL placeholder mismatch (`%s` vs `?`) | feedback.py vs all others | all |
| B-C2 | Temp file leak in PDF/report generation | results.py | 494, 521 |
| B-C3 | JobManager in-memory state lost with >1 worker | jobs/__init__.py | all |
| B-C4 | Background job starts before transaction commits | datasets.py | 607-625 |
| B-C5 | `datetime.utcnow()` produces naive datetimes (deprecated) | jobs/__init__.py, feedback.py | 43, 160, 384 |

### High (10)
| ID | Issue | File | Line |
|----|-------|------|------|
| B-H1 | Download loads entire dataset into memory (OOM risk) | datasets.py | 950-1062 |
| B-H2 | File upload size checked AFTER full read into memory | submissions.py | 354-363 |
| B-H3 | link-observations links WRONG observations | datasets.py | 819-827 |
| B-H4 | No user isolation on submissions (IDOR) | submissions.py | all |
| B-H5 | Coverage/link-observations no ownership check | datasets.py | 781-879 |
| B-H6 | ILIKE wildcards not escaped in user input | results.py | 82 |
| B-H7 | Feedback rate limiter leaks memory (unbounded defaultdict) | feedback.py | 31-48 |
| B-H8 | `SELECT s.*, sr.*` column name collisions in export | results.py | 326-334 |
| B-H9 | `_use_production_auth` flag evaluated at import time | middleware/auth.py | 34 |
| B-H10 | Dual auth systems return incompatible user types | auth.py vs middleware/auth.py | all |

### Notable Medium Issues
- **B-M10:** `getattr(request, ...)` reads HTTP Request instead of Pydantic model -- dataset config silently ignored
- **B-M8:** No `ON CONFLICT` on submission_results INSERT -- re-evaluation creates duplicates
- **B-M11:** `BEGIN TRANSACTION`/`COMMIT` may not work with connection pooling
- **B-M14:** Legacy dataset creation endpoint missing token validation

---

## DOMAIN 5: FRONTEND CODE QUALITY

### Critical (3)
| ID | Issue | File | Line |
|----|-------|------|------|
| F-C1 | Auth state listener never cleaned up (memory leak) | authStore.ts | 84 |
| F-C2 | isAdmin from client-writable user_metadata (privilege escalation) | authStore.ts | 33 |
| F-C3 | useToast listener re-registers on every state change | use-toast.ts | 174 |

### High (7)
| ID | Issue | File | Line |
|----|-------|------|------|
| F-H1 | Login race: navigates before auth state propagates | LoginPage.tsx | 38-44 |
| F-H2 | Supabase client created with empty strings | supabase.ts | 3-4, 13 |
| F-H3 | Delete button on submissions has no onClick handler | MySubmissionsPage.tsx | 227-229 |
| F-H4 | Statistics tab shows completely fake hardcoded data | DatasetPreviewDialog.tsx | 127-163 |
| F-H5 | Token refresh subscribers hang forever on failure | client.ts | 71-109 |
| F-H6 | Notifications/Security/Avatar/API Key tabs are non-functional stubs | ProfilePage.tsx | 397-524 |
| F-H7 | `any` type in ProfilePage error handler | ProfilePage.tsx | 110 |

### Notable Medium Issues
- **F-M4:** `transformSubmission` creates results stub with all metrics hardcoded to 0
- **F-M5:** Dashboard greeting is hardcoded "researcher" instead of actual username
- **F-M7:** Sensor filter is client-side only; search filter is applied both server and client-side
- **F-M9:** `useActionLogger` monkey-patches global history methods

---

## DOMAIN 6: DATA PIPELINE & ALGORITHMS

### Critical (4)
| ID | Issue | File | Line |
|----|-------|------|------|
| P-C1 | Space-Track query parameters silently ignored | apiIntegration.py | 1256 |
| P-C2 | `np.arccos` without clipping causes NaN in Gauss IOD | gauss.py | 157, 225, 453 |
| P-C3 | unitConversion.py initializes Orekit at import -- crashes non-Java systems | unitConversion.py | 9-28 |
| P-C4 | generateCov.py same Orekit import crash | generateCov.py | 13-28 |

### High (7)
| ID | Issue | File | Line |
|----|-------|------|------|
| P-H1 | Binary metrics y_true/y_pred semantically incorrect for sklearn | binaryMetrics.py | 171-173 |
| P-H2 | basicScoringFunction `os.chdir()` at module level | basicScoringFunction.py | 12-16 |
| P-H3 | Uninitialized variables on some code paths | basicScoringFunction.py | 329, 344, 351 |
| P-H4 | `_discosweb_cache` is an unbounded dict (memory leak) | apiIntegration.py | 1291 |
| P-H5 | `addManeuverFlags` is O(n*m) per-row apply | apiIntegration.py | 915-922 |
| P-H6 | `np.random.seed()` global state (not thread-safe) | simulateObservations.py | 45 |
| P-H7 | B* unit conversion missing Earth radius scaling factor | objectTypeFiltering.py | 186-192 |

### Notable Medium Issues
- **P-M2:** `datetimeToUDL` microsecond formatting wrong for values < 100000
- **P-M4:** `compute_arc_coverage` double-counts coverage arcs
- **P-M5:** PostgreSQL adapter uses single connection, not a pool
- **P-M7:** Gauss IOD `cullStates` uses 0.25 sigma (rejects ~80% of valid states)
- **P-M10:** Repository `create()` uses `?` placeholders that break on PostgreSQL

---

## DOMAIN 7: TESTING COVERAGE

### Critical Gaps
1. **ZERO authentication tests** -- 23+ auth-protected endpoints never tested for auth enforcement
2. **CI `|| true`** silences all test failures
3. **Backend API tests not in CI path** -- only `tests/` is targeted, not `backend_api/tests/`

### High Priority Gaps
4. **Zero frontend tests** -- test infrastructure exists but no actual test files
5. **Zero security tests** -- no SQL injection, file upload, rate limiting, or XSS tests
6. **Zero error recovery tests** -- worker crashes, DB connection loss, concurrency untested
7. **Zero feedback router tests**

### Test Quality Issues
- Many tests only check status codes, not response bodies
- Integration tests only test DuckDB, never PostgreSQL (production DB)
- E2E tests excluded from CI (`--ignore=tests/e2e`)
- Worker tests mock 4+ layers deep -- testing mock wiring, not behavior
- Tests dependent on Orekit imports silently skip in CI

---

## DOMAIN 8: INFRASTRUCTURE & DEVOPS

### Critical (4)
| ID | Issue | File |
|----|-------|------|
| I-C1 | CI `\|\| true` swallows all test failures | deploy.yml:25 |
| I-C2 | Both containers run as root | All Dockerfiles |
| I-C3 | Sentry SDK installed but never initialized on backend | pyproject.toml |
| I-C4 | ENCRYPTION_KEY not enforced in production | crypto.py |

### High (8)
| ID | Issue | File |
|----|-------|------|
| I-H1 | Railway CLI version not pinned | deploy.yml:47, 84 |
| I-H2 | `--detach` with no deploy verification | deploy.yml:50, 87 |
| I-H3 | No database migration framework (Alembic) | -- |
| I-H4 | No backup strategy | -- |
| I-H5 | OpenAPI/Swagger docs exposed in production | main.py:133 |
| I-H6 | nginx missing all security headers | nginx.conf.template |
| I-H7 | Python dependencies not pinned | pyproject.toml |
| I-H8 | `.gitignore` excludes all `*.lock` files | .gitignore:74 |

### Medium (8)
| ID | Issue | File |
|----|-------|------|
| I-M1 | Frontend deploy depends sequentially on backend (not atomic) | deploy.yml:58 |
| I-M2 | Rate limiter uses proxy IP, not real client IP | rate_limit.py |
| I-M3 | Backend runs single worker by default | start.py:7 |
| I-M4 | Docker build not multi-stage for backend | Dockerfile |
| I-M5 | No resource limits in Railway config | railway.toml |
| I-M6 | docker-compose frontend missing BACKEND_URL | docker-compose.yml:48-60 |
| I-M7 | Health check timeouts misaligned (Docker 60s vs Railway 300s) | Dockerfile, railway.toml |
| I-M8 | No Content-Security-Policy on frontend nginx | nginx.conf.template |

### What's Already Done Well
- Health check endpoints on both services
- Railway restart policy configured (ON_FAILURE, max 3)
- Security headers middleware on FastAPI (partial)
- JWT auth with ES256 JWKS + HS256 fallback
- Request logging with correlation IDs
- Sensitive field redaction in logs
- Gzip compression in nginx
- Static asset caching (1-year immutable)
- Token encryption module (Fernet) exists

---

## PRIORITIZED ACTION PLAN

### Phase 0: Immediate (Day 1) -- 5 fixes
1. Remove `|| true` from CI deploy.yml
2. Fix `getattr(request, ...)` bug in datasets.py (user config silently ignored)
3. Move `submit_dataset_generation()` after COMMIT in datasets.py
4. Fix Space-Track query `str.join()` bug in apiIntegration.py
5. Add `np.clip` to all `np.arccos` calls in gauss.py

### Phase 1: Security (Days 2-3) -- 8 fixes
1. Consolidate auth modules (remove middleware/auth.py dev bypass)
2. Add JWT issuer verification
3. Add user_id to submissions table + ownership checks
4. Fix SQL placeholder inconsistency in feedback router
5. Admin role from app_metadata only (not user_metadata)
6. Enforce ENCRYPTION_KEY in production
7. Add non-root USER to all Dockerfiles
8. Disable OpenAPI docs in production

### Phase 2: Infrastructure (Days 4-5) -- 7 fixes
1. Pin Railway CLI version in CI
2. Add deploy verification step in CI
3. Add security headers to nginx
4. Fix rate limiter to use X-Forwarded-For
5. Initialize Sentry on backend
6. Pin Python dependencies
7. Remove `*.lock` from gitignore

### Phase 3: Code Quality (Days 6-8) -- 10 fixes
1. Wrap Orekit init in try/except in unitConversion.py and generateCov.py
2. Fix `datetime.utcnow()` -> `datetime.now(timezone.utc)` everywhere
3. Fix token refresh subscriber drain on failure (client.ts)
4. Fix download endpoint to use streaming (datasets.py)
5. Fix file upload to check size before full read (submissions.py)
6. Fix link-observations to filter by dataset context
7. Remove os.chdir() from basicScoringFunction.py
8. Fix datetimeToUDL microsecond formatting
9. Fix orbital coverage double-counting
10. Replace np.random.seed() with Generator in simulateObservations.py

### Phase 4: Testing (Days 9-11) -- 6 fixes
1. Add backend API tests to CI path
2. Remove `--ignore=tests/e2e` from CI
3. Write auth test suite (test_auth.py)
4. Write security tests (injection, uploads, rate limiting)
5. Add PostgreSQL test target in CI
6. Add pytest-cov with 60% minimum threshold

### Phase 5: Documentation (Days 12-13) -- 5 fixes
1. Update all planning docs to show auth as "Complete"
2. Fix port references (3000 not 5173)
3. Fix PostgreSQL driver docs (psycopg2, not pg8000)
4. Fix API endpoint documentation
5. Update CHANGELOG through v2.0.0

### Phase 6: Alignment Gaps (Days 14+) -- ongoing
1. Add UI warnings when selecting non-optical sensors or event types
2. Implement event detection integration
3. Enforce target object percentages
4. Set up Alembic for database migrations
5. Set up automated database backups

---

## Conclusion

The UCT Benchmark has a **solid scientific foundation** with 20 of Louis's core requirements faithfully implemented. The orbital mechanics, evaluation metrics, and dataset generation pipeline are well-designed. However, the application has **significant security, testing, and operational gaps** that prevent it from being production-ready:

- **Security:** Auth bypass risks, IDOR vulnerabilities, missing JWT validation
- **Testing:** Zero auth tests, CI doesn't gate deploys, no frontend tests
- **Reliability:** Race conditions, silent data corruption (Space-Track, getattr bug), memory leaks
- **Operations:** Root containers, no error tracking, no backups, no migration framework

The 6-phase action plan above addresses these in priority order. Phase 0 (5 immediate fixes) can be done in a single day and will resolve the most impactful bugs. Phases 1-2 (security + infra) make the app genuinely safe to deploy. Phases 3-5 bring it to production quality.
