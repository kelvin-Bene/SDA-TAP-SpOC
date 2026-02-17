# UCT-Benchmark-DMR Test Report

**Date:** 2026-01-29
**Branch:** blakes-local-work
**Tester:** Claude Code (Opus 4.5)

---

## Executive Summary

| Category | Passed | Failed | Total | Pass Rate |
|----------|--------|--------|-------|-----------|
| Backend Tests (existing `run_all_tests.py`) | 289 | 16 | 459* | 63% |
| New Auth Endpoint Tests | 16 | 0 | 16 | 100% |
| New UCTP Endpoint Tests | 22 | 0 | 22 | 100% |
| New Security Tests | 28 | 3 | 31 | 90% |
| Playwright E2E Tests | 105 | 0 | 105 | 100% |
| **Total New Tests** | **171** | **3** | **174** | **98%** |

\* 154 errors in existing tests due to conftest/pg8000 import issues unrelated to application code.

---

## Phase 2: Existing Backend Tests (`run_all_tests.py`)

| Category | Name | Passed | Failed | Errors | Status |
|----------|------|--------|--------|--------|--------|
| 1 | Core Pipeline Integrity | 42 | 11 | 69 | Partial |
| 2 | Data Processing & Simulation | 30 | 0 | 0 | PASS |
| 3 | API & Data Sources | 31 | 5 | 85 | Partial |
| 4 | Backend API | 164 | 0 | 0 | PASS |
| 5 | UCTP Lab | 22 | 0 | 0 | PASS |

**Notes:**
- Categories 1 and 3 have errors due to `conftest.py` fixture issues and `pg8000` import failures when `DATABASE_BACKEND=postgres` is set in the environment.
- Categories 2, 4, and 5 pass fully.

---

## Phase 3: New Backend Tests

### `test_auth_endpoints.py` - 16/16 passed

| Class | Tests | Status |
|-------|-------|--------|
| `TestAuthDisabled` | 5 | All pass |
| `TestAuthEnabled` | 6 | All pass |
| `TestAuthValidation` | 5 | All pass |

Tests cover: signup/login/logout with auth disabled (anonymous mode), signup/login with auth enabled (local user store), duplicate email detection, missing fields validation, malformed JSON.

### `test_uctp_endpoints.py` - 22/22 passed

| Class | Tests | Status |
|-------|-------|--------|
| `TestDashboardStats` | 1 | Pass |
| `TestRunsCRUD` | 7 | All pass |
| `TestRunComparison` | 3 | All pass |
| `TestModels` | 6 | All pass |
| `TestConnectivity` | 3 | All pass |
| `TestAlgorithms` | 2 | All pass |

Tests cover: dashboard stats, runs CRUD (list/create/delete/404s), run comparison validation, model training/listing/deletion, connectivity tests (mocked), algorithm options.

### `test_security.py` - 28/31 passed (3 real findings)

| Class | Passed | Failed | Status |
|-------|--------|--------|--------|
| `TestSQLInjection` | 5 | 1 | 1 finding |
| `TestInputValidation` | 7 | 2 | 2 findings |
| `TestMalformedPayloads` | 7 | 0 | Pass |
| `TestCORS` | 2 | 0 | Pass |
| `TestCredentialSecurity` | 4 | 0 | Pass |
| `TestParameterizedQueries` | 3 | 0 | Pass |

**3 failing tests document real application bugs (see Security Findings below).**

---

## Phase 4: Playwright E2E Tests - 105/105 passed

| Spec File | Tests | Passed | Failed | Notes |
|-----------|-------|--------|--------|-------|
| `landing-page.spec.ts` | 8 | 8 | 0 | |
| `login-page.spec.ts` | 7 | 7 | 0 | |
| `dashboard.spec.ts` | 10 | 10 | 0 | |
| `datasets.spec.ts` | 14 | 14 | 0 | |
| `submissions.spec.ts` | 8 | 8 | 0 | |
| `leaderboard.spec.ts` | 7 | 7 | 0 | |
| `uctp-lab.spec.ts` | 16 | 16 | 0 | |
| `info-popover.spec.ts` | 10 | 10 | 0 | |
| `theme.spec.ts` | 5 | 5 | 0 | |
| `navigation.spec.ts` | 8 | 8 | 0 | |
| `settings-credentials.spec.ts` | 6 | 6 | 0 | |
| `docs-profile.spec.ts` | 5 | 5 | 0 | |

All 105 Playwright E2E tests pass reliably. Tests use `domcontentloaded` instead of `networkidle` to avoid flaky timeouts when running 6 parallel workers against the local backend.

### All 17 UI Pages Verified

| Route | Page | Loads | No Console Errors | InfoPopovers |
|-------|------|-------|-------------------|--------------|
| `/welcome` | Landing Page | Yes | Yes | N/A |
| `/login` | Login Page | Yes | Yes | N/A |
| `/` | Dashboard | Yes | Yes | N/A |
| `/datasets` | Dataset Browser | Yes | Yes | Yes - open/close |
| `/datasets/generate` | Dataset Generator | Yes | Yes | Yes - trigger/popover/badge |
| `/datasets/my-datasets` | My Datasets | Yes | Yes | N/A |
| `/submit` | Submit Algorithm | Yes | Yes | N/A |
| `/submit/my-submissions` | My Submissions | Yes | Yes | N/A |
| `/results/:id` | Submission Results | Yes | Yes | N/A |
| `/leaderboard` | Leaderboard | Yes | Yes | N/A |
| `/uctp` | UCTP Dashboard | Yes | Yes | Yes - stat cards |
| `/uctp/workbench` | UCTP Workbench | Yes | Yes | Yes - clustering/IOD/refine |
| `/uctp/runs/:id` | Run Results | Yes | N/A | N/A |
| `/uctp/training` | ML Training | Yes | Yes | Yes |
| `/uctp/connectivity` | Connectivity | Yes | Yes | Yes - connector cards |
| `/docs` | Documentation | Yes | Yes | N/A |
| `/profile` | Profile | Yes | Yes | N/A |
| `/settings` | Settings | Yes | Yes | N/A |

---

## Phase 5: Security Findings

### Critical / High

None found.

### Medium

| # | Finding | File:Line | Details | Recommendation |
|---|---------|-----------|---------|----------------|
| S1 | **No input validation on limit/offset params** | `backend_api/routers/datasets.py` | Negative limit/offset values pass through to DuckDB which throws `LIMIT/OFFSET cannot be negative`, returning 500. | Add `ge=0` constraint to FastAPI query params: `limit: int = Query(50, ge=0)` |
| S2 | **Submission filter injection** | `backend_api/routers/submissions.py` | `dataset_id` query param accepts non-integer strings like `"1 OR 1=1"` causing 500 server error. | Use FastAPI typed query params: `dataset_id: Optional[int] = None` |
| S3 | **`days` param f-string interpolated into SQL** | `backend_api/routers/leaderboard.py:150` | The `days` parameter is interpolated as `f"INTERVAL '{days} days'"` -- not parameterized. No upper bound validation. | Use parameterized queries for the days value and add `le=365` validation. |
| S4 | **No rate limiting** | `backend_api/main.py` | No rate limiting middleware on any endpoint. Auth endpoints (login/signup) are especially vulnerable. | Add `slowapi` or similar rate limiting middleware. |

### Low

| # | Finding | File:Line | Details | Recommendation |
|---|---------|-----------|---------|----------------|
| S5 | **`generate-key` endpoint has no auth guard** | `backend_api/routers/credentials.py:204` | The API key generation endpoint works without authentication. | Add `Depends(require_auth)` to the endpoint. |
| S6 | **No request size limits** | `backend_api/main.py` | No explicit max request body size configured. | Configure max body size in ASGI server or middleware. |
| S7 | **CORS allows `*` headers** | `backend_api/main.py:122` | `allow_headers=["*"]` is overly permissive. | Restrict to required headers only. |

### Info

| # | Finding | File:Line | Details |
|---|---------|-----------|---------|
| S8 | **In-memory user store lost on restart** | `backend_api/routers/auth.py` | `_users_db` dict is lost when server restarts. |
| S9 | **AUTH_ENABLED=false bypasses all security** | `backend_api/auth/dependencies.py` | Default dev mode disables all auth checks. |
| S10 | **`datetime.utcnow()` deprecated** | `backend_api/routers/leaderboard.py:119` | Use `datetime.now(datetime.UTC)` instead. |
| S11 | **Pydantic V1-style `class Config` deprecated** | `backend_api/models/__init__.py`, `uctp_models.py` | Multiple models use deprecated `class Config` instead of `ConfigDict`. |

---

## Phase 6: Code Review Findings

### Priority: High

| # | Finding | File:Line | Fix Required |
|---|---------|-----------|--------------|
| C1 | **DISTINCT ON syntax (PostgreSQL-only)** | `backend_api/routers/uctp.py:457` | `DISTINCT ON` breaks DuckDB. Use subquery with `ROW_NUMBER()` instead. |
| C2 | **Audit middleware uses `%s` placeholders on DuckDB** | `backend_api/middleware/audit.py` | Audit SQL uses PostgreSQL `%s` placeholders. DuckDB uses `?`. Add backend detection. |

### Priority: Medium

| # | Finding | File:Line | Fix Required |
|---|---------|-----------|--------------|
| C3 | **Dataset ID path params not typed** | `backend_api/routers/datasets.py` | Some path parameters accept strings where integers are expected. Use `dataset_id: int` in route signatures. |
| C4 | **InfoPopover CSS class `cfg.accentBg.replace('/10', '')` may produce invalid class** | `frontend/src/components/ui/info-popover.tsx:160` | String replacement of Tailwind opacity modifier could produce non-existent CSS class. |

### Priority: Low

| # | Finding | File:Line | Details |
|---|---------|-----------|---------|
| C5 | Generator page has 1 InfoPopover (expected more) | `frontend/src/pages/DatasetGeneratorPage.tsx` | Only 1 `[aria-label^="Learn about"]` trigger found. Consider adding more educational content. |
| C6 | Test fixtures create separate in-memory DBs per module | `backend_api/tests/test_*.py` | Module-scoped DB fixtures work correctly but cross-module test runs can fail due to app lifespan DB lifecycle. |

---

## Test Infrastructure

### Files Created

| File | Purpose | Tests |
|------|---------|-------|
| `backend_api/tests/test_auth_endpoints.py` | Auth endpoint tests | 16 |
| `backend_api/tests/test_uctp_endpoints.py` | UCTP Lab endpoint tests | 22 |
| `backend_api/tests/test_security.py` | Security & input validation tests | 31 |
| `frontend/playwright.config.ts` | Playwright configuration | - |
| `frontend/e2e/fixtures.ts` | Shared Playwright helpers | - |
| `frontend/e2e/landing-page.spec.ts` | Landing page E2E | 8 |
| `frontend/e2e/login-page.spec.ts` | Login page E2E | 7 |
| `frontend/e2e/dashboard.spec.ts` | Dashboard E2E | 10 |
| `frontend/e2e/datasets.spec.ts` | Dataset pages E2E | 14 |
| `frontend/e2e/submissions.spec.ts` | Submit/results E2E | 8 |
| `frontend/e2e/leaderboard.spec.ts` | Leaderboard E2E | 7 |
| `frontend/e2e/uctp-lab.spec.ts` | UCTP Lab pages E2E | 16 |
| `frontend/e2e/info-popover.spec.ts` | InfoPopover component E2E | 10 |
| `frontend/e2e/theme.spec.ts` | Theme switching E2E | 5 |
| `frontend/e2e/navigation.spec.ts` | Navigation/routing E2E | 8 |
| `frontend/e2e/settings-credentials.spec.ts` | Settings page E2E | 6 |
| `frontend/e2e/docs-profile.spec.ts` | Docs & profile E2E | 5 |

### Running Tests

```bash
# Backend tests (run individually to avoid cross-module DB issues)
cd combined
uv run pytest backend_api/tests/test_auth_endpoints.py -v
uv run pytest backend_api/tests/test_uctp_endpoints.py -v
uv run pytest backend_api/tests/test_security.py -v

# Existing backend test suite
uv run python run_all_tests.py

# Playwright E2E (requires backend on :8000, frontend on :3000, Supabase on :54321)
cd frontend
npx playwright test
npx playwright test --reporter=html  # HTML report
npx playwright show-report            # View report
```

### Key Technical Notes

1. **Backend test fixtures** must patch both `backend_api.database` AND `backend_api.main` module references to prevent app lifespan from closing the shared test DB.
2. **DuckDB backend** must be explicitly specified in test fixtures: `DatabaseManager(in_memory=True, backend="duckdb")` to avoid `DATABASE_BACKEND=postgres` env var interference.
3. **InfoPopover** is a custom component (NOT Radix). Popover card selector: `.absolute.z-50.w-80`. Backdrop: `.fixed.inset-0.z-40`. ConceptBadge: `button.cursor-help`.
4. **UCTP models** use strict Pydantic enums: Clustering methods (`angular_dbscan`, `stonesoup_mht`, `stonesoup_gnn`), IOD methods (`gauss`, `orbdetpy_laplace`, `orekit_gooding`), Refinement methods (`none`, `batch_least_squares`, `ekf`, `ukf`), Model types (`clustering_nn`, `propagation_ml`, `hybrid`).
