# Changelog

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
