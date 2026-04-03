# Changelog

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
