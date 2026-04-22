# Changelog

## v2.0.3 (2026-04-22)

### Fixed — 3D globe in production

The v2.0.2 `VISION_ALIGNMENT_AUDIT` claimed the 3D globe was working in
prod. It wasn't — first visual verification revealed `/reference-orbits`
failing with `Propagation failed for sat N: Attempt to create Java
package 'java' without jvm`, the Results page Orbits tab falsely
blocking Reference mode, and nginx → backend 502s from Railway internal
DNS outages. Six-commit fix train landed the feature end-to-end:

- **`d81e150`** — Eager `warm_jvm()` at FastAPI lifespan startup
  (`main.py`) + `/predictions` graceful degrade when UCTP file gone
  (`submissions.py`). With `include=reference`, we now return 200 with
  `predicted:[]` and `reference:[…]` instead of 410, so the Results
  page Reference view renders for historical submissions whose UCTP
  files have been cleaned from storage.
- **`189695f`** — `orekit.initVM()` must run BEFORE `from
  orekit_jpype.pyhelpers import setup_orekit_curdir` in
  `ephemerisPropagator` + `monteCarloPropagator`. The pyhelpers module
  executes `from java.io import File` at import time, which fails
  without a running JVM. `TLEpropagator` already had the correct
  ordering — which is why eval workers happened to work (they hit TLE
  propagation first, seeding the sys.modules cache). Web-path globe
  endpoints tripped the broken order on the first call in the process.
- **`7698337`** — `nginx.conf.template` hardcoded to proxy
  `/api/` + `/health` to the public backend URL
  (`backend-production-4b02.up.railway.app`). Railway's internal DNS
  (`backend.railway.internal` via resolver 127.0.0.11) stopped
  resolving on 2026-04-22 for ~an hour, 502'ing every proxied request.
  Public URL survives that class of outage at ~50-100ms per-request
  latency cost. Revert to `${BACKEND_URL}` once internal networking
  confirmed stable across multiple redeploys.
- **`5eb6f0b`** — Backend `SecurityHeadersMiddleware` sets
  `Cache-Control: no-store, no-cache, must-revalidate, private` +
  `Pragma: no-cache` on `/api/*` and `/health` responses. Frontend
  axios client sends `Cache-Control: no-cache` with each request.
  Together these bust stuck browser 410 caches (per RFC 7234 §4.2.2
  browsers cache 4xx responses indefinitely when no Cache-Control is
  set — which is how a single transient backend error can persist in
  a client session).
- **`f817ea8`** — CORS `allow_headers` extended with `Cache-Control`
  + `Pragma`. Without this the axios header above triggered preflight
  failures and all `/api/` calls 400'd.
- **`ae7a8b1`** — `VISION_ALIGNMENT_AUDIT.md` Priority 2 #2 + Missing
  Features #7 + Priority 2 #5 promoted back to RESOLVED after
  Claude-in-Chrome visual confirmation (1101×499 Cesium canvas
  mounting on `/results/47` with real satellite tracks).

### Prod verification

- `GET /api/v1/datasets/153/reference-orbits` → 200, `satellites:[1]`
- `GET /api/v1/datasets/158/reference-orbits` → 403 (correct
  owner-gate behavior; was 502 pre-fix)
- `GET /api/v1/submissions/47/predictions?include=reference` → 200,
  `predicted:[]` `reference:[1]`
- Prod Playwright: **85/92 passed, 0 failed, 7 skipped**
  (intentional fixture-skip)
- Claude-in-Chrome: Orbits tab → Reference toggle → Cesium canvas
  renders with "Showing 1 satellites", full viewer UI (regime pills,
  time slider, zoom/rotate hints)

### Alignment bump

Overall Alignment 82% → **87%**. External Integrations 85% → **92%**.
See `reports/VISION_ALIGNMENT_AUDIT.md`.

## v2.0.2 (2026-04-20)

### Added

- **Composite score visibility** (`f2fdd50`): Results page now shows a per-component breakdown (Binary × w1 + State × w2 + Residual × w3) with bars and a state-source badge (Mahalanobis p-score vs. position-RMS heuristic). Fallback banner when Orekit is unavailable. Closes the remaining Louis-vision gap from the Feb 19 transcript — the leaderboard ranks by composite, and users can now see *why* a score dropped instead of asking.
- **Leaderboard composite tooltip** (`f2fdd50`): train/val/test breakdown shown on hover, with a note that only test ranks (can't be cheated).
- **Rank ordering** (`f2fdd50`): ResultsPage ORDER BY now mirrors the leaderboard's `COALESCE(test_composite_score, composite_score, f1_score)`.
- **3D globe integration** (`f2fdd50`): `OrbitViewer` wired into DatasetDetailPage (owner+admin gated to preserve answer-key separation), ResultsPage (own-submissions only), and LandingPage hero (desktop-only static fixture). New backend endpoints: `GET /datasets/{id}/reference-orbits` and `GET /submissions/{id}/predictions` with Orekit propagation + disk cache.
- **Event filter DB-first short-circuit** (`f2fdd50`): `generateDataset()` now queries persisted events from `/events/detect` before the TLE heuristic runs. New `EventRepository.find_events_in_window` for bulk lookup.
- **`has_reference_orbits` filter** (`559db9d`, `21e4699`): backend exposes the boolean via EXISTS subquery on `dataset_references`; frontend `Dataset` interface maps `hasReferenceOrbits` and `SubmitPage` gates the dropdown on it. Replaces the date-only `EVAL_CUTOFF_MS` heuristic that was letting post-Apr-9 datasets without reference state vectors through to the evaluator.
- **`scripts/backfill_dataset_references.py`** (`a5eda35`): mirrors the reference-linking step from `run_dataset_generation` so a dataset that successfully generated observations but failed to write `dataset_references` can be repaired without full regeneration. Used pre-demo to repair dataset 158; retained as a general ops tool. Supports `--dry-run`; reads `DATABASE_URL` from `.env`.
- **`scripts/seed_demo_submission.py`** (`0879bdd`): realistic demo submission helper — fetches truth state + observation IDs for a dataset, adds Gaussian noise, builds a valid UCTP record, posts it via the authenticated submissions API, and polls until terminal. Drove the Apr-17 prod verification that produced the first completed submission in prod history (submission 44, `composite_score=1.0`) and surfaced the chain of 8 latent eval-pipeline bugs below.
- **Regression test coverage** (`3ea3c64`): backend tests for QA C1, H1, L4 so the fixes are guarded in CI.

### Fixed

**QA prod findings 2026-04-17** (`559db9d`):
- **C1** (demo blocker): evaluation pipeline failed on every post-Apr-9 dataset because `SubmitPage`'s date-only filter let datasets without persisted reference state vectors through. See the Added section above for the structural fix.
- **H1**: `submission.error_message` is now persisted alongside `status='failed'` on job failure (`workers.py:1945-1954`), so the ResultsPage banner surfaces the underlying `ValueError` text instead of generic fallback copy.
- **L1**: `apiIntegration.py` `WindowEvaluation` attribute typos — `avg_orbital_coverage` → `avg_coverage`, `avg_track_gap` → `avg_track_gap_periods`. Stops producing `performance_metadata.error` on every dataset generation.
- **L4**: `DatabaseJobManager.list_jobs` now merges in-memory and DB rows (deduped by id) so historical jobs survive in-memory eviction and operators retain forensic visibility.

**Eval pipeline hardening — chain of 8 latent bugs surfaced by seed_demo_submission.py** (Apr 17–18):
- `f62a197` guard `orbitAssociation` against infeasible cost matrix.
- `20295f2` guard empty-DataFrame sort after infeasible-matrix fallback.
- `d0a222d` fail-fast epoch sanity check on submission epochs.
- `3d328a3` / `092449e` rebuild SV-mode associated DataFrame via iloc-slice (not list-of-Series).
- `16db3b5` serialize stateMetrics + residualMetrics SV-mode pools.
- `6661622` serial cost-column computation in SV mode to unblock Orekit.
- `6d8ebdd` convert truth covariance from 21-element lower-triangular to 6×6.
- `c27ae8f` force truth state/cov to float64 for `multivariate_normal`.
- `b35c2da` guarantee UCTP `cov_matrix` is 6×6 float64 post-`generateCov`.
- `6f4a4f1` safety-net `cov_matrix` on `associated_orbits` post-assoc.
- `f3d522b` convert NaN/Inf to null in results JSON serialization (was crashing `JSONResponse`).

**Frontend globe rescue** (Apr 18–19):
- `5b4276e` / `41bcd74` Cesium entity graphics marshaled correctly (reverted from plain-object props back to `Graphics` class instances per Cesium's React error #31 guidance).
- `7cbf1bd` dropped `creditContainer={undefined}` Viewer prop (Cesium strict type-check).
- **`12c2f2b` pinned `resium` to `1.18.3`** — 1.18.4+ targets React 19 internals and silently crashes hidden behind our ErrorBoundary/SVG fallback. Upgrade blocked until React 18 → 19 migration.
- `236dea0` disable CDN caching on SPA `index.html` so the globe fix actually ships to users.

**Deploy hygiene** (Apr 17):
- `51b56ba` / `e959d09` / `d9c38c3` `orekit-data.zip` un-LFS'd + tracked normally so Railway's Docker build can `COPY` it.
- `487f078` / `cc2b506` Railway CLI deploys now stage the frontend dir in `/tmp` and use an empty `.railwayignore` so the CLI doesn't walk into the repo-root `.gitignore`.

**e2e test stability** (Apr 17):
- `84bd0d3` fixed M1/M2/M5/M6 + hardened C1/H1 guardrails per QA prod 2026-04-17 findings.
- `5c88360` prod projects get 1 retry locally, 2 in CI.
- `c5f64af` stabilize post-QA regressions.
- `dea79aa` non-owner globe asserts no interactive globe, not no header.
- `40c4995` `findUnownedId` uses ownership cross-check instead of probing optional `user_id`/`owner_id` fields.
- `e814720` tighten waits on leaderboard/navigation/orbits specs.

## v2.0.1 (2026-04-09)

### Fixed
- **Coverage threshold bug**: LEO/MEO coverage thresholds were 100x too permissive (0.0213 instead of 0.000213 as fraction), causing incorrect tier classification. GEO was already correct.
- **HEO coverage scoring**: Added missing HEO coverage threshold (0.20) — HEO satellites were silently excluded from coverage classification in basicScoringFunction.
- **HEO regime classification**: basicScoringFunction now uses eccentricity (via `determine_orbital_regime`) instead of semi-major axis only, consistent with the downsampling pipeline.
- **Combo regime pipeline**: Added 7 missing regime combo mappings (LGO, LHO, MGO, MHO, GHO, LMH, LGH) to windowSelection's `regime_map` — previously these silently defaulted to LEO-only.
- **HAMR threshold comment**: Corrected misleading comment from "A/M > 0.1" to "A/M > 1" (code value was already correct at 1.0).
- **Frontend regime combos**: All 15 regime options (4 singles + ALL + 6 two-regime + 4 three-regime combos) are now visible in both the Standard Wizard and Legacy Code wizard, and accepted by the client-side validator.
- **SQL injection pattern**: Removed f-string interpolation from events.py WHERE clause construction.
- **Silent DDL error swallowing**: schema.py DDL init now logs caught exceptions instead of bare `pass`.
- **22 pre-existing test failures**: Fixed attribute name mismatches, function signature mismatches, auth fixtures, datetime fixture bug, and timer test flakiness (849 → 890 tests passing).
- **Documentation**: Updated Evaluation Metrics docs to describe composite scoring (was stale "ranked by F1-Score").
- **Composite scoring gap**: Marked as resolved — `compute_composite_score()` implements Lewis's Feb 19 "you lose points there" philosophy with weights 0.4/0.3/0.3.

## v2.0.0 (2026-04-01)

### Added
- Full-stack web application (FastAPI + React + PostgreSQL/DuckDB)
- Supabase JWT authentication with ES256 JWKS verification
- User-scoped data access with admin override
- Rate limiting via slowapi on all API endpoints
- Encrypted API token storage (Fernet) for UDL/ESA credentials
- Feedback system with screenshot support
- Leaderboard with algorithm comparison
- Security headers (CSP, HSTS, X-Frame-Options)
- Sentry error tracking (frontend + backend)
- Daily automated database backups
- CI/CD pipeline with GitHub Actions deploying to Railway

### Changed
- Migrated from desktop customtkinter GUI to React web frontend
- Migrated from single-user local to multi-user cloud architecture
- Database schema versioned at 1.6.0 with automated migrations

### Fixed
- IDOR vulnerabilities on submissions, results, and jobs endpoints
- Thread-safe database connections (threading.local pattern)
- Leaderboard sorting logic for position RMS
- Token refresh memory leak in API client
- XFF rate limit bypass (trust rightmost proxy IP)

## v1.0.0 (2026-01-15)

### Added
- Core evaluation pipeline with 19 metrics (6 state, 8 binary, 5 residual)
- 16-character dataset code system with full validation
- Window selection with bisection algorithm
- 3-stage downsampling (coverage, track gap, observation count)
- T1-T5 tier classification
- True negative generation (non-reference observations)
- UDL and ESA API integrations
- Orekit-based orbit propagation (DormandPrince853 integrator)
- DuckDB local database backend
