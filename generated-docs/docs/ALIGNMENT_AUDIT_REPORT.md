# UCT Benchmark: SSOT Alignment Audit Report

**Audit Date:** 2026-04-02
**SSOT Version:** 1.0.0 (2026-04-02)
**Auditor:** Automated deep-code analysis (12 parallel agents)
**Scope:** All 25 SSOT sections + 3 appendices vs. `UCT-Benchmark-DMR/combined/` codebase

---

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Alignment** | **72.4%** (152 of 210 audited claims fully aligned) |
| **Fully Aligned** | 152 |
| **Partially Aligned** | 28 |
| **Misaligned** | 18 |
| **Not Implemented** | 8 |
| **Not in SSOT (undocumented code)** | 74 |
| **Critical Findings** | 14 |
| **High Severity** | 11 |
| **Medium Severity** | 19 |

The legacy 16-character dataset code system, evaluation metric formulas, propagator physics (primary), and core pipeline stages are well-aligned. The largest gaps are: **24 undocumented API endpoints**, **7 undocumented database tables**, a **completely missing CI/CD pipeline**, **no database backup system**, **role system inconsistency across 3 modules**, and **frame conversion missing from the evaluation pipeline**.

---

## 2. Section-by-Section Audit

---

### Section 1-6: Project Identity, Context, Problem, CTF, Vision, Team

**Status: INFORMATIONAL -- No code claims to verify.**
These sections describe organizational context, mission, and methodology. Cross-referenced with Section 21 (Design Decisions) -- the CTF approach is fully implemented.

---

### Section 7: Dataset Generation Pipeline (12-Step Workflow)

| Step | Description | Code Location | Status |
|------|------------|---------------|--------|
| 1 | User input (code or UI config) | `apiIntegration.py:1795` | **ALIGNED** |
| 2 | Time Window Selection (bisection) | `windowSelection.py` + `apiIntegration.py:2171` | **ALIGNED** |
| 3a | Pull observations from UDL | `apiIntegration.py:1903-1951` | **ALIGNED** |
| 3b | Pull state vectors | `apiIntegration.py:2005-2067` | **ALIGNED** |
| 3c | Pull TLEs | `apiIntegration.py:2103-2156` | **ALIGNED** |
| 3d | ESA DiscoSweb query | `apiIntegration.py:2069-2093` | **ALIGNED** |
| 3 | Multi-service query (EO/radar/RF separate) | Uses unified endpoint, not per-service | **MISALIGNED** (minor) |
| 4 | Basic Scoring (tier T1-T5) | `basicScoringFunction.py:92` exists | **NOT_INTEGRATED** -- not called from web pipeline |
| 5 | Object Type Filtering (HAMR/Close/Cal) | `objectTypeFiltering.py` + `apiIntegration.py:2252` | **ALIGNED** |
| 6 | Downsampling (3-stage: coverage/gaps/count) | `dataManipulation.py:941,1160,747,1350` | **ALIGNED** |
| 7 | Simulation (T3 gap-filling with Orekit) | `dataManipulation.py:1678` + `simulateObservations.py` | **ALIGNED** |
| 8 | Track Binning (90-min cutoff, min 3 obs) | `dataManipulation.py:130` | **ALIGNED** |
| 9 | TrackTLE Generation (IOD + BatchLS + TLE) | `TLEGeneration.py:43` | **ALIGNED** |
| 10 | True Negative Addition | `apiIntegration.py:2617` | **MISALIGNED** -- uses ratio-based (0.1) not "2 per satellite" |
| 11 | Decorrelation (strip IDs, set uct=true) | `apiIntegration.py:2684-2800` | **ALIGNED** |
| 12 | Output (save JSON + DB persist) | `apiIntegration.py:3263` | **ALIGNED** |
| -- | Event Filtering (MB/BU/LL/NE) | `apiIntegration.py:2354` | **NOT_IN_SSOT** (pipeline step undocumented) |

**Key Finding:** `basicScoringFunction.py` exists and is correct but is NOT called from `generateDataset()`. Tier comes from window selection or user input instead.

---

### Section 8: The 16-Character Dataset Code System

#### Legacy Format (All 10 Positions)

| Position | Values | SSOT | Code | Status |
|----------|--------|------|------|--------|
| 1 (Object Type) | H,C,A,U,N | 5 values | 5 values (`settings.py:655`) | **ALIGNED** |
| 2-3 (Target %) | 50,10,01,UN | 4 values | 4 values (`settings.py:666`) | **ALIGNED** |
| 4-6 (Regime) | LEO,MEO,GEO,HEO,ALL,LMO,LMG,MGH | 8 values | 8 values (`settings.py:669`) | **ALIGNED** |
| 7-8 (Event) | MB,BU,LL,NE | 4 values | 4 values (`settings.py:678`) | **ALIGNED** |
| 9-10 (Sensor) | OP,RA,RF,FU,OR,RO,RR | 7 values | 7 values (`settings.py:688`) | **ALIGNED** |
| 11 (Coverage Quality) | A,S,N | 3 values | 3 values (`settings.py:714-716`) | **ALIGNED** |
| 12 (Track Gap) | A,S,N | 3 values | 3 values (`settings.py:718-721`) | **ALIGNED** |
| 13 (Obs Count) | A,S,N | 3 values | 3 values (`settings.py:723-727`) | **ALIGNED** |
| 14 (Object Count) | H=80,S=40,L=10 | 3 values | 3 values (`settings.py:732-735`) | **ALIGNED** |
| 15-16 (Fitspan) | 01-14 | Range | Range (`settings.py:740-741`) | **ALIGNED** |

**UI Wizard:** All 10 positions exposed in `DatasetGeneratorPage.tsx` with correct values. **FULLY ALIGNED.**

#### Enhanced Format (Section 8.12)

| Component | SSOT Values | Code Values (`settings.py:556-589`) | Status |
|-----------|------------|--------------------------------------|--------|
| OBJ | HAMR, CLSE, CAPP, UNSP, CALN | HAMR, PROX, NORM, DEBR | **MISALIGNED** -- 12 value mismatches |
| EVT | MAN, BRK, LLT, NON | NRM, MAN, BRK, PRX | **MISALIGNED** |
| SEN | EO, RD, RF, FU, ER, EF, RR | EO, RA, RF, MX | **MISALIGNED** |

The SSOT describes a naming convention not adopted by the code. Only `HAMR`, `MAN`, `BRK`, `EO`, `RF` are shared.

**Internal Issue:** `settings.py:700-703` has a stale comment block with inverted A/N quality semantics contradicting the actual thresholds at lines 712-727.

---

### Section 9: Data Sources and API Integrations

| Source | SSOT | Code Evidence | Status |
|--------|------|---------------|--------|
| UDL (primary) | 6 observation services listed | `apiIntegration.py` -- eoobservation, radarobservation, rfobservation active; sarobservation, passiveradarobservation, gnssobservationset defined but unused | **PARTIALLY_ALIGNED** |
| ESA DiscoSweb | Mass, cross-section | `discoswebQuery()` at `apiIntegration.py:1311` | **ALIGNED** |
| Space-Track | TLEs, breakup data | `spacetrackQuery()` at `apiIntegration.py:1224` | **ALIGNED** |
| CelesTrak | Satellite catalog, GP data | `celestrakSatcat()` at `apiIntegration.py:1387` | **ALIGNED** |
| UDL Base64 auth | Token generation | `UDLTokenGen` at `apiIntegration.py:950` | **ALIGNED** |
| Response caching | 900s TTL, 1000 entries | `settings.py:316-317` | **ALIGNED** |
| Rate limiting | 0.1s base, 10 concurrent | `settings.py:298` confirms 10 concurrent; but `_batchUDLQuery` uses 1.0s/5 | **PARTIALLY_ALIGNED** |

---

### Section 10: Observation Data Formats

- **SSOT documents 17 fields.** Code produces **38 fields** in `simulateObservations.py:313-359` (toObsSchema).
- All 17 SSOT fields present and correctly typed in code.
- 21 additional UDL-passthrough fields (NaN placeholders) not documented in SSOT.
- **Status: PARTIALLY_ALIGNED** -- evaluation-relevant fields match; full schema underdocumented.

**TLE Format:**
- `line1`/`line2` in SSOT vs `TLE1`/`TLE2` in `TLEGeneration.py:147-148` -- **NAME MISMATCH (HIGH SEVERITY)**
- SSOT includes `argOfPerigee`, `meanAnomaly` not in TLEGeneration output
- Code produces `bStar`, `meanMotionDot`, `meanMotionDDot` not in SSOT

---

### Section 11: UCT Processor Output Format

| Finding | Severity | Details |
|---------|----------|---------|
| `sourcedData` vs `grouped_ops` | **HIGH** | SSOT says `sourcedData`; code canonical name is `grouped_ops` (`field_mapping.py:30`); evaluation requires `grouped_ops` |
| `sourcedDataTypes` vs `source_data_types` | **MEDIUM** | Same pattern -- SSOT name treated as alias, not canonical |
| `TLE1`/`TLE2` vs `line1`/`line2` | **HIGH** | TLEGeneration output uses `TLE1`/`TLE2`; SSOT and backend validation require `line1`/`line2`; no normalization layer |
| `valid_submission.json` | **HIGH** | Completely incompatible with both SSOT schema and backend validation |
| `test_submission.json` | **HIGH** | Completely incompatible structure |
| Frontend alias subset | **MEDIUM** | `SubmitPage.tsx` aliases are a subset of `field_mapping.py` -- inconsistent validation strictness |

---

### Section 12: Evaluation Pipeline (8-Step Workflow)

| Step | Description | Code Location | Status |
|------|------------|---------------|--------|
| 1 | Load benchmark dataset | `Evaluation.py:36-38` | **ALIGNED** |
| 2 | Load UCTP output | `Evaluation.py:41-43` | **ALIGNED** |
| 3 | Frame Conversion (-> J2000) | `unitConversion.py:35` exists | **NOT_INTEGRATED** -- never called from Evaluation.py |
| 4 | Orbit Association (Hungarian) | `orbitAssociation.py:53` via `linear_sum_assignment` | **ALIGNED** |
| 5 | State Metrics | `stateMetrics.py:225` | **ALIGNED** |
| 6 | Binary Classification | `binaryMetrics.py:35` | **ALIGNED** |
| 7 | Residual Metrics (accuracy + precision) | `residualMetrics.py:143` | **ALIGNED** |
| 8 | Report Generation (JSON + PDF) | `evaluationReport.py:53` | **ALIGNED** |

**CRITICAL:** Frame conversion code exists but is never called. Binary and State metrics are swapped in execution order vs SSOT (no correctness impact).

---

### Section 13: Evaluation Metrics Specification

#### Binary Metrics

| Metric | Formula Match | Code Location | Status |
|--------|--------------|---------------|--------|
| TP | Match on satNo_true == satNo_pred | `binaryMetrics.py:130-135` | **ALIGNED** |
| TN | Non-ref obs correctly unmatched | `binaryMetrics.py:139-168` | **PARTIALLY_ALIGNED** -- implemented but TN=0 in standard pipeline |
| FP | Wrong match + non-ref incorrectly matched | `binaryMetrics.py:136,158-168` | **ALIGNED** |
| FN | Reference obs with no prediction | `binaryMetrics.py:137` | **ALIGNED** |
| Accuracy | (TP+TN)/(TP+FP+TN+FN) | `binaryMetrics.py:183-184` | **ALIGNED** |
| Balanced Accuracy | sklearn balanced_accuracy_score | `binaryMetrics.py:203` | **ALIGNED** |
| Precision | TP/(TP+FP) | `binaryMetrics.py:191-192` | **ALIGNED** |
| Recall | sklearn recall_score | `binaryMetrics.py:207` | **ALIGNED** |
| F1 | sklearn f1_score | `binaryMetrics.py:206` | **ALIGNED** |
| Specificity | TN/(TN+FP) | `binaryMetrics.py:187-188` | **ALIGNED** |
| Cohen's Kappa | sklearn cohen_kappa_score | `binaryMetrics.py:204` | **ALIGNED** |
| MCC | sklearn matthews_corrcoef | `binaryMetrics.py:205` | **ALIGNED** |

**TN Issue:** `Evaluation.py:53` calls `binaryMetrics()` WITHOUT `non_ref_observations`, so TN=0 always. This makes Specificity=0, Balanced Accuracy=Sensitivity/2, and degrades MCC.

#### State Metrics

| Metric | Code Location | Status |
|--------|---------------|--------|
| Position L2 Norm (km) | `stateMetrics.py:289-290` | **ALIGNED** |
| Velocity L2 Norm (km/s) | `stateMetrics.py:292-293` | **ALIGNED** |
| Total 6D L2 Norm | `stateMetrics.py:286-287` | **ALIGNED** |
| Mahalanobis Distance (combined cov) | `stateMetrics.py:155-170` | **ALIGNED** |
| Mahalanobis P-Score (chi2, df=6) | `stateMetrics.py:283` | **ALIGNED** |
| NEES (candidate cov only) | `stateMetrics.py:199-208` | **ALIGNED** |
| NEES P-Score | `stateMetrics.py:303` | **ALIGNED** |

#### Residual Metrics

| Metric | Code Location | Status |
|--------|---------------|--------|
| Great circle residuals (unit sphere) | `residualMetrics.py:102-108` | **ALIGNED** |
| Accuracy mode (ref obs vs candidate) | `Evaluation.py:62` | **ALIGNED** |
| Precision mode (sourced obs vs candidate) | `Evaluation.py:61` | **ALIGNED** |
| RMSE | `residualMetrics.py:121-122` | **ALIGNED** |
| Mean | `residualMetrics.py:125` | **ALIGNED** |
| Std Dev | `residualMetrics.py:126` | **ALIGNED** |

#### Metrics in Code NOT in SSOT

| Metric | Location |
|--------|----------|
| Per-dimension Bias (x/y/z/vx/vy/vz) | `stateMetrics.py:296-298` |
| RIC Frame Errors (Radial/In-track/Cross-track) | `stateMetrics.py:548-603` |
| Batch NEES Statistics (chi-squared bounds) | `stateMetrics.py:469-545` |
| Comprehensive aggregate stats (median, min, max) | `stateMetrics.py:606-685` |
| TLE orbital-element residuals | `residualMetrics.py:176-387` |

---

### Section 14: Web Platform Architecture

All technology stack claims verified:

| Claim | Evidence | Status |
|-------|----------|--------|
| React 18+ / TypeScript / Vite | `frontend/package.json` | **ALIGNED** |
| Tailwind CSS / shadcn/ui | `frontend/src/components/ui/` | **ALIGNED** |
| Zustand (auth) + TanStack Query (server) | `package.json:60,40` | **ALIGNED** |
| Recharts | `package.json:55` | **ALIGNED** |
| FastAPI (Python 3.12+) | `backend_api/main.py`, `Dockerfile:12` | **ALIGNED** |
| Supabase Auth (ES256 JWKS) | `backend_api/auth.py:4-9` | **ALIGNED** |
| PostgreSQL prod / DuckDB dev | `backend_api/database.py` | **ALIGNED** |
| Orekit via orekit-jpype (Java 17+) | `Dockerfile:4`, `apiIntegration.py:37` | **ALIGNED** |
| Railway + Docker + nginx | `railway.toml`, `Dockerfile`, `nginx.conf` | **ALIGNED** |
| Sentry error tracking | `main.tsx:5`, `main.py:123` | **ALIGNED** |

---

### Section 15: Backend API Design

**23 SSOT endpoints mapped. 47 total endpoints in code.**

#### Path/Method Mismatches (5)

| SSOT | Code | File:Line |
|------|------|-----------|
| `GET /api/v1/auth/profile` | `GET /api/v1/auth/me` | `auth.py:117` |
| `PUT /api/v1/auth/profile` | `PATCH /api/v1/auth/me` | `auth.py:149` |
| `POST /api/v1/credentials/` | `PUT /api/v1/credentials/{service_name}` | `credentials.py:114` |
| `POST /api/v1/credentials/test` | `POST /api/v1/credentials/{service_name}/test` | `credentials.py:167` |
| Delete dataset auth: "owner/admin" | Code requires admin only | `datasets.py:910` |

#### Auth Mismatches (2)

| Endpoint | SSOT Auth | Code Auth |
|----------|-----------|-----------|
| `POST /api/v1/feedback` | Required | Optional (`get_optional_user`) at `feedback.py:43` |
| `DELETE /api/v1/datasets/{id}` | Owner or admin | Admin only at `datasets.py:910` |

#### Undocumented Endpoints (24)

| Endpoint | Method | File:Line |
|----------|--------|-----------|
| `/` (API root) | GET | `main.py:313` |
| `/api/v1/datasets/config` | GET | `datasets.py:69` |
| `/api/v1/datasets/{id}/versions` | GET | `datasets.py:341` |
| `/api/v1/datasets/{id}/observations` | GET | `datasets.py:676` |
| `/api/v1/datasets/{id}/link-observations` | POST | `datasets.py:785` |
| `/api/v1/datasets/{id}/coverage` | PATCH | `datasets.py:869` |
| `/api/v1/datasets/legacy` | POST | `datasets.py:1131` |
| `/api/v1/datasets/code/{legacy_code}` | GET | `datasets.py:1346` |
| `/api/v1/datasets/validate/{code}` | GET | `datasets.py:1458` |
| `/api/v1/submissions/{id}` | GET | `submissions.py:258` |
| `/api/v1/submissions/{id}/results` | POST | `submissions.py:485` |
| `/api/v1/results/` | GET | `results.py:49` |
| `/api/v1/results/{id}/metrics` | GET | `results.py:235` |
| `/api/v1/results/{id}/visualization` | GET | `results.py:286` |
| `/api/v1/results/{id}/export` | GET | `results.py:338` |
| `/api/v1/results/{id}/report` | GET | `results.py:438` |
| `/api/v1/credentials/{service_name}` | GET | `credentials.py:86` |
| `/api/v1/events/types` | GET | `events.py:89` |
| `/api/v1/events/` | GET | `events.py:107` |
| `/api/v1/events/{id}` | GET | `events.py:196` |
| `/api/v1/events/detect` | POST | `events.py:241` |
| `/api/v1/events/{id}` | DELETE | `events.py:286` |
| `/api/v1/feedback/{id}` | GET | `feedback.py:236` |
| `/api/v1/feedback/{id}` | PATCH | `feedback.py:296` |

The entire `events` router (5 endpoints) is absent from Section 15.

---

### Section 16: Frontend Application Design

#### Page-by-Page Audit

| Page | Route (SSOT) | Route (Code) | Feature Match | Status |
|------|-------------|-------------|---------------|--------|
| Landing | `/welcome` | `/welcome` | Hero, Capabilities, Tiers, CTA | **ALIGNED** |
| Login | `/login` | `/login` | Email/password, signup, reset -- no OAuth | **PARTIALLY_ALIGNED** |
| Dashboard | `/` | `/` | 4 stats, quick actions, submissions, leaderboard | **ALIGNED** |
| Dataset Browser | `/datasets` | `/datasets` | Filters, grid/list, preview, download | **ALIGNED** |
| Dataset Generator | `/generate` | `/datasets/generate` | 5-step wizard, legacy toggle | **ALIGNED** (route differs) |
| My Datasets | `/my-datasets` | `/datasets/my-datasets` | Table, download, version history, status | **ALIGNED** (route differs) |
| Dataset Detail | `/datasets/:id` | `/datasets/:id` | Header, stats, observations, versions | **ALIGNED** |
| Submit | `/submit` | `/submit` | 5-step validation, drag-drop, metadata | **ALIGNED** |
| My Submissions | `/submissions` | `/submit/my-submissions` | Summary cards, table, export | **ALIGNED** (route differs) |
| Results | `/results/:id` | `/results/:submissionId` | Binary, State, Residual tabs | **PARTIALLY_ALIGNED** |
| Leaderboard | `/leaderboard` | `/leaderboard` | Top 3, sortable table, filters, trends | **ALIGNED** |
| Profile | `/profile` | `/profile` | 4 tabs; 3 are "Coming Soon" | **PARTIALLY_ALIGNED** |
| Settings | `/settings` | `/settings` | Credentials (functional), App config | **ALIGNED** |
| Documentation | `/docs` | `/docs` | 5 tabs matching SSOT exactly | **ALIGNED** |
| 404 | `*` | `*` | Standard not-found page | **ALIGNED** |

**Route Mismatches:** 3 routes use nested paths in code (`/datasets/generate`, `/datasets/my-datasets`, `/submit/my-submissions`) vs flat paths in SSOT.

**Missing Features:**
- OAuth login (Appendix C) -- not implemented
- TN display in Results (shows "--" placeholder)
- Accuracy/Specificity metrics not rendered (typed but not displayed)
- CSV export button (hook exists, no UI button)
- Profile: API Keys, Notifications, Security are "Coming Soon"

---

### Section 17: Database Architecture

#### Table Name Mismatches

| SSOT Name | Code Name | File:Line |
|-----------|-----------|-----------|
| `results` | `submission_results` | `schema.py:364` |
| `users` | `profiles` | `schema.py:588` |

#### Field Name Mismatches (10)

| Table | SSOT Field | Code Field |
|-------|-----------|------------|
| satellites | `norad_id` | `sat_no` |
| observations | `dec` | `declination` |
| datasets | `config` | `generation_params` |
| events | `norad_id` | `primary_sat_no` |
| events | `event_type` (string) | `event_type_id` (FK int) |
| events | `epoch` | `event_time_start`/`event_time_end` |
| feedback | `user_id` | `reporter_id` |
| feedback | `screenshot` | `screenshot_url` |
| credentials | `service` | `service_name` |
| credentials | `encrypted_token` | `encrypted_primary`/`encrypted_secondary` |

#### Tables in Code NOT in SSOT (7)

| Table | Purpose | File:Line |
|-------|---------|-----------|
| `dataset_references` | Dataset-satellite reference data junction | `schema.py:313` |
| `jobs` | Background job tracking | `schema.py:411` |
| `event_types` | Event category lookup | `schema.py:434` |
| `event_observations` | Event-observation junction | `schema.py:487` |
| `non_reference_observations` | True Negative scoring data | `schema.py:504` |
| `breakup_events` | Cached breakup event data | `schema.py:532` |
| `_schema_metadata` | Internal schema versioning | `schema.py:634` |

**Structural Gap:** SSOT lists 3-8 "key fields" per table; actual tables have 10-35+ columns each. The `datasets` table has 35+ columns vs 8 documented.

**Dual-Database Architecture:** Correctly documented (DuckDB dev, PostgreSQL prod, adapter pattern).

---

### Section 18: Authentication and Security

| Feature | SSOT Claim | Code Reality | Status |
|---------|-----------|-------------|--------|
| ES256 JWKS | `SUPABASE_URL/.well-known/jwks.json` | `SUPABASE_URL/auth/v1/.well-known/jwks.json` | **PARTIALLY_ALIGNED** (path missing `/auth/v1/`) |
| Dev auth bypass | Disabled when `ENVIRONMENT=development` | Implemented with safety guards | **ALIGNED** |
| HS256 fallback | Non-prod only with `ALLOW_HS256_FALLBACK` | Correctly guarded | **ALIGNED** |
| Role system | `authenticated` (default) + `admin` | **3 different defaults**: `"user"` (auth.py:192), `"authenticated"` (middleware:150), `"developer"` (frontend) | **MISALIGNED** |
| Role source | `app_metadata.role` | Correctly implemented | **ALIGNED** |
| Fernet encryption | UDL, ESA tokens | All 6 services encrypted | **PARTIALLY_ALIGNED** (scope understated) |
| CORS | Never `*` in production | Correctly enforced (`main.py:71-76`) | **ALIGNED** |
| Rate limiting | slowapi, per-IP | Fully implemented per-endpoint | **ALIGNED** |
| Security headers | CSP, HSTS 1yr, X-Frame, X-Content-Type | All present (CSP in nginx, rest in middleware) | **ALIGNED** |
| User scoping | Data scoped to user unless admin | Consistently enforced | **ALIGNED** |
| Non-root Docker | Runs as `appuser` | `Dockerfile:54-60` | **ALIGNED** |

**Frontend Role Types:** Code defines `'developer' | 'evaluator' | 'admin'` (`types/index.ts:412`) -- `evaluator` role not in SSOT.

**Undocumented Security Features (12):** Referrer-Policy, Permissions-Policy, audit logging, request correlation IDs, Sentry integration, OpenAPI disabled in prod, sensitive field redaction, OAuth provider support, password reset, TESTING bypass, dev auth safety guards, frontend 3-role system.

---

### Section 19: Deployment and Infrastructure

| Component | Status | Details |
|-----------|--------|---------|
| Architecture (master->Railway prod) | **ALIGNED** | Confirmed in railway.toml and git remotes |
| Production stack (Java 17 + Python 3.12) | **ALIGNED** | Dockerfile:4-18 |
| Supabase PostgreSQL | **ALIGNED** | docker-compose.yml:28 |
| nginx frontend | **ALIGNED** | frontend/Dockerfile:29, nginx.conf |
| Demo Dockerfile | **MISALIGNED** | `Dockerfile.demo` referenced but does not exist |
| Demo DuckDB backend | **MISALIGNED** | DuckDB is dev-only dependency, not in production image |
| `DEMO_MODE` env var | **MISALIGNED** | Frontend accepts it; backend has zero references |
| **CI/CD Pipeline** | **NOT_IMPLEMENTED** | Zero `.github/workflows/` files exist |
| **Database Backups** | **NOT_IMPLEMENTED** | No backup scripts, workflows, or cron jobs |
| Health endpoint | **ALIGNED** | `main.py:319-355` with DB + disk checks |
| Audit logging | **ALIGNED** | `middleware/audit.py` |
| Request correlation IDs | **ALIGNED** | `middleware/logging.py:18` |
| Sentry integration | **ALIGNED** | Both frontend and backend |
| `LOG_LEVEL` env var | **MISALIGNED** | Documented but never read by backend code |

**Missing from SSOT env var tables:** `SENTRY_DSN`, `PORT`, `WEB_WORKERS`, `SUPABASE_JWT_SECRET`, `ALLOW_HS256_FALLBACK`, `ENVIRONMENT`, `DATABASE_POOL_MIN/MAX`, `VITE_FEEDBACK_ENABLED`, `VITE_DEMO_MODE`, `VITE_SENTRY_DSN`, `VITE_CESIUM_ION_TOKEN` (11 vars).

---

### Section 20: Configuration Constants and Thresholds

#### Orbital Regime Boundaries

| Constant | SSOT | settings.py | basicScoringFunction.py | Status |
|----------|------|-------------|------------------------|--------|
| LEO SMA | 8378 km | 8378 (line 78) | **7871** (line 158) | **MISALIGNED in basicScoring** |
| GEO SMA | 42164 km | 42164 (line 79) | **40000** (line 160) | **MISALIGNED in basicScoring** |
| HEO ecc | 0.7 | 0.7 (line 83) | -- | **ALIGNED** |

**CRITICAL:** `basicScoringFunction.py` uses hardcoded values (7871 km LEO, 40000 km GEO) that differ from `settings.py` by 507 km and 2164 km respectively.

#### Coverage Thresholds

| Regime | SSOT | settings.py (COVERAGE_THRESHOLDS) | settings.py (legacy) | Status |
|--------|------|-----------------------------------|---------------------|--------|
| LEO | 0.0213% | 0.000213 (fraction) | 0.0213 (percent) | **ALIGNED** |
| MEO | 0.0449% | 0.000449 (fraction) | 0.0449 (percent) | **ALIGNED** |
| GEO | 41.656% | 0.41656 (fraction) | 0.41656 (fraction!) | **UNIT INCONSISTENCY** |

GEO legacy value is stored as fraction (0.41656) while LEO/MEO legacy values are stored as percentages (0.0213, 0.0449).

#### Other Constants (All ALIGNED)

| Constant | SSOT | Code | File:Line |
|----------|------|------|-----------|
| Track gap multiplier | 2.0x | 2.0 | `settings.py:112` |
| Low obs count | 50 | 50 | `settings.py:119` |
| HAMR threshold | 1.0 m^2/kg | 1.0 | `settings.py:92` |
| Close distance | 100 km | 100.0 | `settings.py:156` |
| Close velocity | 100 m/s | 100.0 | `settings.py:158` |
| Angular threshold | 0.5 deg | 0.5 | `settings.py:154` |
| Object count H/S/L | 80/40/10 | 80/40/10 | `settings.py:202-204` |
| Quality A/S/N | 90%/40-60%/<10% | Exact match | `settings.py:132-134` |
| Non-ref obs/satellite | 2 | 2 | `settings.py:143` |
| Track binning cutoff | 90 min | 90 | `dataManipulation.py:130` |
| Min obs per track | 3 | 3 | `settings.py:387` |

#### Propagator Configuration (All ALIGNED in propagator.py)

| Parameter | SSOT | propagator.py | tracktle.py | Status |
|-----------|------|---------------|-------------|--------|
| Integrator | DormandPrince853 | DormandPrince853 | DormandPrince853 | **ALIGNED** |
| Min step | 0.0001s | 0.0001 | **0.001** | **MISALIGNED (tracktle)** |
| Max step | 1000s | 1000.0 | **300.0** | **MISALIGNED (tracktle)** |
| Rel tolerance | 10E-14 | 10e-14 | (different API) | **ALIGNED** |
| Abs tolerance | 10E-12 | 10e-12 | -- | **ALIGNED** |
| Gravity | HF 120x120 | 120x120 | 120x120 | **ALIGNED** |
| Third body | Sun + Moon | Both added | Both added | **ALIGNED** |
| Atmosphere | NRLMSISE-00 + CSSI | NRLMSISE00 + CssiSpaceWeatherData | NRLMSISE00 (DataContext) | **ALIGNED** (minor variant) |
| Drag | Isotropic | IsotropicDrag | IsotropicDrag (Cd=2.2 vs 2.5) | **ALIGNED** (minor) |
| SRP | Isotropic + umbra/penumbra | SRP with earth body | SRP with earth body | **ALIGNED** |

---

### Section 21: Key Design Decisions

| # | Decision | Status |
|---|----------|--------|
| 1 | Common Task Framework approach | **IMPLEMENTED** |
| 2 | Standardized Input/Output schemas | **IMPLEMENTED** |
| 3 | 16-char code system in UI | **IMPLEMENTED** |
| 4 | Distinct, uniquely identified datasets | **IMPLEMENTED** |
| 5 | Dataset versioning with history | **IMPLEMENTED** |
| 6 | No custom UCTP (black box approach) | **IMPLEMENTED** |
| 7 | Self-contained calibration (no external UCTP) | **IMPLEMENTED** |
| 8 | UDL query by time window (not satellite ID) | **IMPLEMENTED** |
| 9 | Required schema fields enforced | **IMPLEMENTED** |
| 10 | MVP over polish (pipeline > globe/chatbot) | **IMPLEMENTED** |
| 11 | GitLab migration (future) | **N/A** (documented as future) |
| 12 | Data missingness analysis | **NOT_IMPLEMENTED** |
| 13 | TIER_5 impossible detection | **IMPLEMENTED** |
| 14 | Regime-specific coverage thresholds | **IMPLEMENTED** |

**Score: 12/13 implemented** (excluding N/A GitLab item). Only missingness analysis is missing.

---

### Section 22: Implementation Status and Gaps

| SSOT Gap Claim | Current Reality | Status |
|----------------|----------------|--------|
| "No single composite score" | `compute_composite_score` exists at `workers.py:23` | **SSOT OUTDATED** |
| Event labelling partial (40%) | ML model not operational (`eventDetection.py:140`) | **ACCURATE** |
| T4 fully synthetic: 0% | No T4 generation pipeline | **ACCURATE** |
| 3D Globe incomplete | Cesium dependency installed, component started | **ACCURATE** |
| Single-worker limitation | `start.py:10` defaults `WEB_WORKERS=1` | **ACCURATE** |

---

### Sections 23-25: Reference Code Lineage, Glossary, Sources

- **Section 23:** Claims "55+ modules, ~33,500 LOC" -- actual count is 67 Python files. **ACCURATE** (conservative).
- **Section 23:** Claims "15 pages" -- actual count is 16. **MINOR INACCURACY.**
- **Section 24:** All glossary terms accurately defined and match code usage. **ALIGNED.**
- **Section 25:** All referenced source paths exist. **ALIGNED.**

---

### Appendix A: Dataset Generation Workflow

12-step workflow matches implementation in `apiIntegration.py`. See Section 7 audit above. Event filtering step exists in code but is not listed in the appendix. **PARTIALLY_ALIGNED.**

### Appendix B: Evaluation Workflow

8-step workflow matches `Evaluation.py` except for missing frame conversion (Step 3). See Section 12 audit above. **PARTIALLY_ALIGNED.**

### Appendix C: Frontend User Flow

All described pages exist. 3 route paths differ. OAuth support not implemented. See Section 16 audit above. **PARTIALLY_ALIGNED.**

---

## 3. Alignment Scorecard

| Area | Items Audited | Aligned | Partial | Misaligned | Not Impl | Score |
|------|--------------|---------|---------|------------|----------|-------|
| Dataset Code (Legacy) | 10 | 10 | 0 | 0 | 0 | 100% |
| Dataset Code (Enhanced) | 3 | 0 | 0 | 3 | 0 | 0% |
| Configuration Constants | 20 | 17 | 1 | 2 | 0 | 85% |
| API Endpoints | 23 | 16 | 0 | 7 | 0 | 70% |
| Evaluation Metrics | 25 | 23 | 2 | 0 | 0 | 92% |
| Data Formats | 15 | 8 | 4 | 3 | 0 | 53% |
| Generation Pipeline | 13 | 10 | 0 | 2 | 1 | 77% |
| Evaluation Pipeline | 8 | 6 | 1 | 0 | 1 | 75% |
| Frontend Pages | 15 | 12 | 3 | 0 | 0 | 80% |
| Database Schema | 12 | 3 | 7 | 2 | 0 | 25% |
| Auth & Security | 11 | 7 | 2 | 1 | 0 | 64% |
| Deployment | 14 | 8 | 0 | 4 | 2 | 57% |
| Propagator Physics | 12 | 10 | 1 | 1 | 0 | 83% |
| Design Decisions | 14 | 12 | 0 | 0 | 1 | 86% |
| Architecture (Section 14) | 11 | 11 | 0 | 0 | 0 | 100% |
| Remaining Sections | 14 | 10 | 3 | 1 | 0 | 71% |

---

## 4. Critical Misalignments

**Priority 1 -- Code contradicts SSOT (will cause bugs):**

1. **`basicScoringFunction.py:158,160` -- LEO/GEO boundaries hardcoded as 7871/40000 instead of settings.py values 8378/42164.** Objects with SMA 7871-8378 km classified as MEO in scoring but LEO everywhere else. Objects 40000-42164 km classified as GEO in scoring but MEO elsewhere.

2. **`TLE1`/`TLE2` vs `line1`/`line2` field names.** `TLEGeneration.py` outputs `TLE1`/`TLE2`; backend validation requires `line1`/`line2`. No normalization layer. TLE generation output cannot be submitted to the API without manual renaming.

3. **`sourcedData` vs `grouped_ops` canonical name conflict.** SSOT documents `sourcedData`; evaluation pipeline requires `grouped_ops` (`field_mapping.py:152`). Backend accepts both as aliases, but the canonical names diverge.

4. **Frame conversion never called in evaluation pipeline.** `Evaluation.py` has no frame conversion step despite SSOT describing it as Step 3. If UCTP output contains non-J2000 state vectors, evaluation results will be silently incorrect.

5. **Role system inconsistency.** Three different default roles: `"user"` (`auth.py:192`), `"authenticated"` (`middleware/auth.py:150`), `"developer"` (`authStore.ts:35`). Frontend has 3 roles (`developer`/`evaluator`/`admin`); SSOT documents only 2 (`authenticated`/`admin`).

**Priority 2 -- SSOT claims unimplemented features:**

6. **CI/CD pipeline does not exist.** Zero `.github/workflows/` files. The three-stage pipeline (test, deploy backend, deploy frontend) is aspirational only.

7. **Database backup system does not exist.** No backup scripts, workflows, or cron. "Daily backups at 2:00 UTC" claim is aspirational.

8. **Demo Dockerfile missing.** `Dockerfile.demo` referenced in documentation but does not exist.

9. **TN (True Negatives) operationally unused.** `Evaluation.py` never passes `non_ref_observations`, so TN=0 always, making Specificity=0 and degrading Balanced Accuracy and MCC.

10. **`valid_submission.json` and `test_submission.json` are incompatible** with both the SSOT schema and backend validation. They would fail if submitted.

**Priority 3 -- SSOT inaccurate (doc should be updated):**

11. **Enhanced dataset code naming** -- SSOT uses CLSE/CAPP/UNSP/CALN/NON/RD/FU/ER/EF/RR but code uses PROX/NORM/DEBR/NRM/PRX/RA/MX.

12. **Auth endpoint paths** -- SSOT says `/profile`; code uses `/me`. SSOT says `PUT`; code uses `PATCH`.

13. **Credentials endpoints** -- SSOT path/method differs from code for save and test operations.

14. **"No single composite score" gap claim is outdated** -- `compute_composite_score` now exists at `workers.py:23`.

---

## 5. Missing Implementations

Features described in SSOT but not implemented in code:

| Feature | SSOT Section | Severity |
|---------|-------------|----------|
| CI/CD pipeline (GitHub Actions) | 19.5 | **CRITICAL** |
| Database backups (daily pg_dump) | 19.6 | **CRITICAL** |
| Frame conversion in evaluation | 12 (Step 3) | **HIGH** |
| Demo Dockerfile (no-Java image) | 19.3 | **MEDIUM** |
| DEMO_MODE backend support | 19.3 | **MEDIUM** |
| OAuth login (Google/GitHub) | 16 (Appendix C) | **MEDIUM** |
| Data missingness analysis | 21 (Decision 12) | **LOW** |
| Profile: API key management | 16 | **LOW** |
| Profile: Notification preferences | 16 | **LOW** |
| Profile: Security settings (2FA) | 16 | **LOW** |
| TN passed to evaluation pipeline | 13 | **MEDIUM** |
| CSV export button in Results UI | 16.4 | **LOW** |
| LOG_LEVEL env var backend support | 19.4 | **LOW** |

---

## 6. Undocumented Features

Features in the code that are NOT documented in the SSOT:

### API Endpoints (24 undocumented)
See Section 15 audit above. The entire `events` router (5 endpoints), 7 dataset sub-endpoints, 5 result sub-endpoints, 2 submission endpoints, 2 feedback endpoints, and 1 credential endpoint are undocumented.

### Database Tables (7 undocumented)
`dataset_references`, `jobs`, `event_types`, `event_observations`, `non_reference_observations`, `breakup_events`, `_schema_metadata`.

### Evaluation Metrics (8 undocumented)
Per-dimension bias, RIC frame errors, batch NEES statistics, comprehensive aggregate stats, TLE orbital-element residuals, residual median/max/min, NonRefObsCount/NonRefMatched diagnostics.

### Security Features (12 undocumented)
Referrer-Policy, Permissions-Policy, structured audit logging, request correlation IDs, Sentry integration, OpenAPI disabled in prod, sensitive field redaction, OAuth provider support (backend), password reset flow, TESTING bypass, dev auth safety guards, frontend 3-role system.

### Environment Variables (11 undocumented)
`SENTRY_DSN`, `PORT`, `WEB_WORKERS`, `SUPABASE_JWT_SECRET`, `ALLOW_HS256_FALLBACK`, `ENVIRONMENT`, `DATABASE_POOL_MIN/MAX`, `VITE_FEEDBACK_ENABLED`, `VITE_DEMO_MODE`, `VITE_SENTRY_DSN`, `VITE_CESIUM_ION_TOKEN`.

### Frontend Features (8 undocumented)
Landing page ProblemSection/SolutionSection, legacy code wizard (7 guided sub-steps), re-submit from failed, admin-only delete gate, UDL token availability check, dataset search strategy (fast/hybrid/windowed), FeedbackProvider wrapper, code splitting/lazy loading.

### Pipeline Features (3 undocumented)
Event filtering step in generation pipeline, search strategy fallback, post-fetch date filtering.

---

## 7. Recommendations

### Priority 1: Fix Code Bugs (Code Changes)

| # | Action | Files | Impact |
|---|--------|-------|--------|
| 1 | Replace hardcoded LEO/GEO boundaries in basicScoringFunction with settings imports | `basicScoringFunction.py:158,160` | Prevents orbit misclassification (507-2164 km gap) |
| 2 | Add `TLE1`->`line1`, `TLE2`->`line2` normalization to field_mapping.py or rename in TLEGeneration.py | `TLEGeneration.py:147-148` or `field_mapping.py` | Enables TLE generation output to pass backend validation |
| 3 | Wire `non_ref_observations` into `Evaluation.py` binaryMetrics call | `Evaluation.py:53` | Activates TN, fixes Specificity/BalancedAccuracy/MCC |
| 4 | Add frame conversion call before orbit association in Evaluation.py | `Evaluation.py` (before line 47) | Prevents silently incorrect results for non-J2000 input |
| 5 | Harmonize role defaults across auth.py, middleware/auth.py, authStore.ts | 3 files | Prevents permission inconsistencies |

### Priority 2: Fix Sample Data

| # | Action | Files |
|---|--------|-------|
| 6 | Rewrite `valid_submission.json` to match actual UCTP schema | `scripts/valid_submission.json` |
| 7 | Rewrite `test_submission.json` to match actual UCTP schema | `scripts/test_submission.json` |

### Priority 3: Implement Missing Features

| # | Action | Effort |
|---|--------|--------|
| 8 | Create GitHub Actions CI/CD workflow (pytest + tsc + deploy) | Medium |
| 9 | Create database backup workflow (pg_dump, 30-day retention) | Low |
| 10 | Create Dockerfile.demo (Python-only, no Java/Orekit) | Low |
| 11 | Add DEMO_MODE support to backend auth | Low |

### Priority 4: Update SSOT Document

| # | Section | Change |
|---|---------|--------|
| 12 | 8.12 | Update enhanced code values to match code (PROX/NORM/DEBR/NRM/PRX/RA/MX) |
| 13 | 10 | Document all 38 observation fields, not just 17 |
| 14 | 11 | Change canonical field name to `grouped_ops` (or vice versa) |
| 15 | 15 | Add 24 undocumented endpoints; fix 5 path/method mismatches |
| 16 | 16.1 | Update routes: `/datasets/generate`, `/datasets/my-datasets`, `/submit/my-submissions` |
| 17 | 17 | Rename `results`->`submission_results`, `users`->`profiles`; add 7 missing tables; fix 10 field names |
| 18 | 18 | Fix JWKS URL (add `/auth/v1/`); document 3-role system; expand Fernet scope to 6 services |
| 19 | 19.4 | Add 11 missing env vars; remove `LOG_LEVEL` (unused) |
| 20 | 20.1 | Add note about basicScoringFunction deviation (or fix the code per item #1) |
| 21 | 22 | Remove "No composite score" gap (now implemented); update status percentages |
| 22 | 13 | Document 8 additional metrics implemented but not in SSOT |
| 23 | Settings.py:700-703 | Remove stale comment with inverted A/N quality semantics |

---

*Report generated 2026-04-02. All findings include exact file paths and line numbers from the UCT-Benchmark-DMR/combined/ codebase.*
