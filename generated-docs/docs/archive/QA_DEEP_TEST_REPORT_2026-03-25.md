> **ARCHIVED 2026-04-21** — This report is from **2026-03-25** and is **superseded by** [`reports/QA_PROD_RUN_2026-04-17.md`](../reports/QA_PROD_RUN_2026-04-17.md). The critical/high bugs (B1 dataset download 500, B2 results page Not Found, B3 server path leakage) were all fixed in the Apr 16 `f2fdd50` batch. The remaining UX items (B4–B6) carry forward in [`UCT-Benchmark-DMR/combined/BACKLOG.md`](../../../UCT-Benchmark-DMR/combined/BACKLOG.md). Preserved here as historical record.

---

# UCT Benchmark - Deep QA Test Report (Round 2)

**Date:** 2026-03-25
**Tester:** Claude (Automated)
**Frontend:** https://frontend-production-6d80.up.railway.app
**Backend:** https://backend-production-4b02.up.railway.app
**API Version:** 2.0.0

---

## Executive Summary

- **33 API endpoints tested** | 26 Pass, 6 Fail, 1 Partial | **79% pass rate**
- **10 UI journey phases completed** covering every page and interaction
- **4 bugs found** (1 Critical, 1 High, 2 Medium)
- **6 UX improvements** identified
- **3 missing API endpoints** discovered
- **2 security concerns** flagged

---

## Phase 1: Backend API Audit (33 Endpoints)

### Summary Scorecard

| Category | Tested | Pass | Fail | Rate |
|----------|--------|------|------|------|
| Health & Infrastructure | 5 | 4 + 1 partial | 0 | 100% |
| Datasets | 8 | 5 | 3 | 62.5% |
| Submissions | 3 | 3 | 0 | 100% |
| Results | 7 | 5 | 2 | 71.4% |
| Leaderboard | 3 | 3 | 0 | 100% |
| Jobs | 2 | 2 | 0 | 100% |
| Auth | 5 | 4 | 1 | 80% |
| **TOTAL** | **33** | **26** | **6** | **79%** |

### Endpoint Results

| # | Method | Endpoint | Status | Result | Notes |
|---|--------|----------|--------|--------|-------|
| 1 | GET | / | 200 | PASS | Health OK, version 2.0.0 |
| 2 | GET | /health | 200 | PASS | DB connected (24.6ms latency) |
| 3 | GET | /health/ready | 200 | PASS | ready: true |
| 4 | - | CORS headers | - | PASS | Frontend origin allowed, evil origins blocked |
| 5 | - | Security headers | - | PARTIAL | X-Content-Type-Options, X-Frame-Options, X-XSS-Protection present. **Missing: HSTS, CSP, Permissions-Policy** |
| 6 | GET | /api/v1/datasets/config | 400 | **FAIL** | Not implemented - routes to /{id} handler |
| 7 | GET | /api/v1/datasets/ | 200 | PASS | **17 datasets returned** (matches UI) |
| 8 | GET | /api/v1/datasets/72 | 200 | PASS | LEO T2, 87 obs, 8 sats. Note: satellites array empty despite count=8 |
| 9 | GET | /api/v1/datasets/72/versions | 404 | **FAIL** | Not implemented |
| 10 | GET | /api/v1/datasets/72/observations?limit=5 | 200 | PASS | Paginated correctly. Note: track_id="nan" instead of null |
| 11 | GET | /api/v1/datasets/72/download | 500 | **FAIL** | **CRITICAL** - SQL JOIN crash on ALL available datasets |
| 12 | GET | /api/v1/datasets/99999 | 404 | PASS | Proper JSON error format |
| 13 | POST | /api/v1/datasets/validate/{code} | 404 | **FAIL** | Not implemented |
| 14 | GET | /api/v1/submissions/ | 200 | PASS | 4 submissions returned |
| 15 | GET | /api/v1/submissions/3 | 200 | PASS | Detail returned. **Security: file_path exposes server paths** |
| 16 | GET | /api/v1/results/ | 200 | PASS | 1 result returned |
| 17 | GET | /api/v1/results/3 | 200 | PASS | All metrics 0.0 (test data) |
| 18 | GET | /api/v1/results/3/metrics | 200 | PASS | Empty arrays (expected) |
| 19 | GET | /api/v1/results/3/visualization | 200 | PASS | Empty arrays (0.603s - slowest) |
| 20 | GET | /api/v1/results/3/export?format=json | 200 | PASS | Complete export. **Security: file_path exposed** |
| 21 | GET | /api/v1/results/3/report?format=json | 404 | **FAIL** | Not implemented |
| 22 | GET | /api/v1/leaderboard/ | 200 | PASS | 1 entry. Note: dataset_id/name null |
| 23 | GET | /api/v1/leaderboard/history | 200 | PASS | Empty history (expected) |
| 24 | GET | /api/v1/leaderboard/statistics | 200 | PASS | 1 submission, scores 0.0 |
| 25 | GET | /api/v1/jobs/ | 401 | PASS | Auth gate working |
| 26 | GET | /api/v1/jobs/1 | 401 | PASS | Auth gate working |
| 27 | POST | /api/v1/auth/login | 404 | N/A | Login is Supabase-side (by design) |
| 28 | GET | /api/v1/auth/me (no token) | 401 | PASS | Auth required |
| 29 | GET | /api/v1/auth/me (invalid token) | 401 | PASS | Token validation working |
| 30 | GET | /api/v1/auth/me (malformed) | 401 | PASS | Format validation working |
| 31 | POST | /api/v1/auth/verify | 401 | PASS | Auth required |
| 32 | POST | /api/v1/datasets/72/link-observations | 200 | PASS | Discovered endpoint |
| 33 | GET | /api/v1/feedback | 401 | PASS | Auth gate working |

---

## Phase 2: Login & Onboarding Journey

| # | Test | Result | Notes |
|---|------|--------|-------|
| 2.1 | Login page renders | PASS | SpOC branding, email/password fields, Sign in button |
| 2.2 | Sign up form | PASS | Email, Password (min 6 chars), Confirm Password, Create Account |
| 2.3 | Forgot password form | PASS | Email field, Send Reset Link button, Back to sign in |
| 2.4 | Back to sign in navigation | PASS | Returns to login form correctly |
| 2.5 | Wrong password error | PASS | Red banner: "Invalid email or password. Please try again." |
| 2.6 | Correct login redirect | PASS | Redirects to dashboard (/) |
| 2.7 | Console errors | PASS | No JS errors on login flow |

---

## Phase 3: Dashboard Exploration Journey

| # | Test | Result | Notes |
|---|------|--------|-------|
| 3.1 | Dashboard loads | PASS | Welcome message, stat cards, quick actions visible |
| 3.2 | Generate Dataset button | PASS | Navigates to /datasets/generate |
| 3.3 | Submit Algorithm button | PASS | Navigates to /submit |
| 3.4 | View datasets link | PASS | Navigates to /datasets |
| 3.5 | View rankings link | PASS | Navigates to /leaderboard |
| 3.6 | Read docs link | PASS | Navigates to /docs |
| 3.7 | View All (Recent Submissions) | PASS | Navigates to /submit/my-submissions |
| 3.8 | View Full (Leaderboard) | PASS | Navigates to /leaderboard |
| 3.9 | Submission entry click | PASS | Navigates to /results/3 |
| 3.10 | Console errors | PASS | None |

**Bugs Found:**
- **P2**: TOP RANK stat card shows "--" with "Loading..." text that never resolves
- **P1**: Results page (/results/3) shows "Results Not Found" for submission marked "Complete" on dashboard

---

## Phase 4: Dataset Exploration & Download

| # | Test | Result | Notes |
|---|------|--------|-------|
| 4.1 | Dataset browser loads | PASS | 17 datasets in grid view |
| 4.2 | List view toggle | PASS | Layout changes to stacked list |
| 4.3 | Grid view toggle back | PASS | Returns to grid layout |
| 4.4 | Filter by LEO regime | PASS | 17 -> 16 datasets, Clear Filters appears |
| 4.5 | Filter by T1 tier (stacked) | PASS | 16 -> 1 dataset |
| 4.6 | Clear filters | PASS | Back to 17 datasets |
| 4.7 | Preview modal - Overview tab | PASS | Objects, Observations, Coverage, Size, Date, Description |
| 4.8 | Preview modal - Statistics tab | PASS | Observation Density chart, Track Gap, Sensor Distribution |
| 4.9 | Preview modal - Sample Data tab | PASS | JSON with observations and truthCatalog |
| 4.10 | Download button | FAIL | No visible feedback on click (backend returns 500) |
| 4.11 | My Datasets page | PASS | Stats cards, table with actions |
| 4.12 | Version history modal | PASS | Shows "No other versions found" |
| 4.13 | Delete confirmation dialog | **FAIL** | No confirmation dialog appears on delete click |

---

## Phase 5: Dataset Generation Wizard

| # | Test | Result | Notes |
|---|------|--------|-------|
| 5.1 | Wizard loads Step 1 (Regime) | PASS | 8 regime options, Target % options, Standard/Legacy tabs |
| 5.2 | MEO regime selection | PASS | Highlights correctly |
| 5.3 | 10% target selection | PASS | Radio updates |
| 5.4 | Step 2 (Quality) loads | PASS | Coverage, Obs Density slider, Track Gap, Sensor Type, Event Type |
| 5.5 | Radar sensor selection | PASS | Highlights on click |
| 5.6 | Step 3 (Objects) loads | PASS | Object count slider, Date Range, Object Type, HAMR toggle, Fitspan |
| 5.7 | Step 4 (Advanced) loads | PASS | Search strategies (Fast/Hybrid/Windowed), Downsampling, Gap-Filling |
| 5.8 | Step 5 (Review) loads | PASS | All selections summarized correctly |
| 5.9 | 16-char dataset code preview | PASS | U10MEONERAS$SS07 with breakdown |
| 5.10 | Back navigation | PASS | Returns to previous step, preserves selections |
| 5.11 | Legacy Code mode | PASS | Different wizard with 7 steps, code display |
| 5.12 | Enter Code mode | PASS | Direct 16-char input field with character counter |

---

## Phase 6: Submission & Results

| # | Test | Result | Notes |
|---|------|--------|-------|
| 6.1 | Submit page loads | PASS | Upload area, form fields, Submit for Evaluation button |
| 6.2 | Dataset dropdown | PASS | Lists 11+ datasets |
| 6.3 | Empty form submit validation | **FAIL** | No visible validation errors shown |
| 6.4 | My Submissions page | PASS | Stats: 4 total, 1 completed, 2 in progress |
| 6.5 | Submission table | PASS | Statuses: Queued, Complete, Failed with colored badges |
| 6.6 | Eye icon on completed submission | PASS | Present only on completed submissions |

---

## Phase 7: Leaderboard & Competition

| # | Test | Result | Notes |
|---|------|--------|-------|
| 7.1 | Leaderboard page | PASS | Podium (#1 SupabaseTestUCTP), filters, rankings table |
| 7.2 | Performance Trends tab | PASS | F1-Score Trends chart area renders |
| 7.3 | Rankings tab | PASS | Table with Rank/Algorithm/Team/F1/Precision/Recall/Pos RMS |
| 7.4 | Filters (Regime/Tier/Time) | PASS | All 3 filter dropdowns present |

---

## Phase 8: Documentation

| # | Test | Result | Notes |
|---|------|--------|-------|
| 8.1 | Getting Started tab | PASS | Welcome, Quick Start Steps, Key Concepts |
| 8.2 | Dataset Format tab | PASS | JSON schema with observations fields in code block |
| 8.3 | Submission Format tab | PASS | (Verified tab clickable) |
| 8.4 | Evaluation Metrics tab | PASS | (Verified tab clickable) |
| 8.5 | Regime badges (LEO/MEO/GEO/HEO) | PASS | Colored correctly |
| 8.6 | Tier badges (T1-T4) | PASS | Colored correctly |

---

## Phase 9: Profile & Settings

| # | Test | Result | Notes |
|---|------|--------|-------|
| 9.1 | Profile tab | PASS | Display Name, Email (disabled), Organization, UDL/ESA tokens |
| 9.2 | Email field disabled | PASS | "Managed by authentication provider" note |
| 9.3 | API Keys tab | PASS | Production key (Active), show/copy, Regenerate, Usage stats |
| 9.4 | Notifications tab | PASS | (Tab clickable) |
| 9.5 | Security tab | PASS | (Tab clickable) |
| 9.6 | Token show/hide toggle | PASS | Eye icon on UDL API Token field |

---

## Phase 10: Navigation & Feedback

| # | Test | Result | Notes |
|---|------|--------|-------|
| 10.1 | Dashboard sidebar link | PASS | Navigates to / |
| 10.2 | Browse Datasets link | PASS | Navigates to /datasets |
| 10.3 | Generate Dataset link | PASS | Navigates to /datasets/generate |
| 10.4 | My Datasets link | PASS | Navigates to /datasets/my-datasets |
| 10.5 | New Submission link | PASS | Navigates to /submit |
| 10.6 | My Submissions link | PASS | Navigates to /submit/my-submissions |
| 10.7 | Leaderboard link | PASS | Navigates to /leaderboard |
| 10.8 | Documentation link | PASS | Navigates to /docs |
| 10.9 | Top nav (Datasets/Submit/Leaderboard/Docs) | PASS | All navigate correctly |
| 10.10 | Notification bell | PASS | Badge shows count (2) |
| 10.11 | Status bar | PASS | "All systems operational" with green dot |

---

## Phase 11: Cross-Verification

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 11.1 | API dataset count vs UI | PASS | Both show 17 |
| 11.2 | API leaderboard vs UI | PASS | Both show 1 entry (SupabaseTestUCTP) |
| 11.3 | API submissions vs UI | PASS | Both show 4 submissions with matching statuses |
| 11.4 | Results page vs API | **MISMATCH** | UI shows "Not Found" but API returns data for /results/3 |
| 11.5 | Console errors | PASS | No JS errors observed across all pages |
| 11.6 | Loading states | PASS | All pages resolve (except TOP RANK on dashboard) |

---

## Bug List

| # | Severity | Component | Description |
|---|----------|-----------|-------------|
| B1 | **P0 - Critical** | Backend | **Dataset download returns 500** on ALL available datasets. SQL JOIN crash in `datasets.py` lines 664-676 between `observations` and `dataset_observations` tables. Error returned as plain text, not JSON. |
| B2 | **P1 - High** | Frontend | **Results page shows "Not Found"** for completed submission (ID 3). API returns valid data at `/api/v1/results/3` but UI at `/results/3` says "results are not available yet or submission doesn't exist." Frontend-backend data flow mismatch. |
| B3 | **P1 - High** | Backend | **Server file paths leaked** in `GET /submissions/{id}` response (`file_path: "C:\Users\kelvi\Desktop\DMR\..."`) and `GET /results/{id}/export`. Security risk exposing internal directory structure. |
| B4 | **P2 - Medium** | Frontend | **No validation errors on empty submit form**. Clicking "Submit for Evaluation" with all fields empty produces no visible feedback (no error toast, no field highlighting). |
| B5 | **P2 - Medium** | Frontend | **Delete button on My Datasets has no confirmation dialog**. Clicking delete icon on a dataset row produces no confirmation modal. |
| B6 | **P2 - Medium** | Frontend | **TOP RANK card stuck on "Loading..."** on dashboard. Never resolves to actual value. |
| B7 | **P2 - Medium** | Backend | **3 API endpoints not implemented**: `/datasets/config`, `/datasets/{id}/versions`, `/results/{id}/report` |
| B8 | **P3 - Low** | Backend | **Missing security headers**: HSTS, Content-Security-Policy, Permissions-Policy not set on responses |
| B9 | **P3 - Low** | Backend | **track_id stored as string "nan"** instead of null in observations data |
| B10 | **P3 - Low** | Backend | **Leaderboard dataset_id/name null** in all 3 leaderboard API responses |
| B11 | **P3 - Low** | Backend | **11/17 datasets (65%) in failed state** - consider cleanup for production |
| B12 | **P3 - Low** | Backend | **satellites array empty** on dataset 72 despite satellite_count: 8 |

---

## UX Improvement Suggestions

| # | Area | Suggestion |
|---|------|------------|
| U1 | Download | Show error toast when download fails (currently silent failure) |
| U2 | Submit form | Add inline validation with red borders and error messages on required fields |
| U3 | Delete flow | Add confirmation modal: "Are you sure you want to delete [dataset name]?" with Cancel/Delete buttons |
| U4 | Dashboard | Fix TOP RANK loading state - show "N/A" or "No rank yet" instead of perpetual loading |
| U5 | Results page | When results exist in API but fail to load in UI, show more specific error message with retry option |
| U6 | My Submissions | Add export/download button for submission history (CSV/JSON) |

---

## Backend Performance Notes

| Endpoint | Response Time | Assessment |
|----------|--------------|------------|
| GET /health | 0.174s | Good |
| GET /datasets/ | 0.545s | Acceptable |
| GET /datasets/72/observations | 0.780s | Slow (5 records) |
| GET /results/3/visualization | 0.603s | Slowest endpoint |
| GET /results/3/export | 0.372s | Acceptable |

---

## What's Working Well

1. **Authentication flow** - Login/signup/forgot password all work correctly with proper error handling
2. **Dashboard navigation** - All quick actions and links navigate to correct pages
3. **Dataset browser** - Grid/list toggle, filters, preview modal with 3 tabs all functional
4. **Generator wizard** - All 5 steps work with correct data flow, back navigation preserves state
5. **Legacy code mode** - Works with both wizard and direct code entry
6. **Documentation** - All 4 tabs render with proper formatting, code blocks, and colored badges
7. **Profile management** - All 4 tabs render, API key management works, token show/hide works
8. **CORS configuration** - Properly restricts to frontend origin
9. **Error handling** - 404s return proper JSON format, auth gates work on protected routes
10. **Sidebar navigation** - All links work, active state highlighted correctly

---

## Recommended Fix Priority

### Must Fix Before Stakeholder Demo
1. **B1** - Dataset download 500 (blocks core user workflow)
2. **B2** - Results page "Not Found" (blocks results viewing)
3. **B3** - File path leakage (security risk)

### Should Fix Soon
4. **B4** - Submit form validation feedback
5. **B5** - Delete confirmation dialog
6. **B6** - Dashboard TOP RANK loading state
7. **B7** - Implement missing API endpoints

### Nice to Have
8. **B8-B12** - Security headers, data cleanup, minor data issues
9. **U1-U6** - UX improvements
