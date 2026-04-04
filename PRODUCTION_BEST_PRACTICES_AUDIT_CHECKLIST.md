# Production Best Practices Audit Checklist
## For UCT Benchmark Application (Compiled April 2026)

This document compiles authoritative industry best practices (2025-2026) across eight categories relevant to the UCT Benchmark application stack (FastAPI + React/TypeScript + PostgreSQL/Supabase + Docker + Railway + GitHub Actions).

---

## 1. FastAPI Production Best Practices

### Industry Best Practices (from web research)

**Project Structure & Architecture**
- Use a modular router-based structure with separate routers per domain (e.g., `routers/datasets.py`, `routers/jobs.py`) -- [Render: FastAPI Production Deployment](https://render.com/articles/fastapi-production-deployment-best-practices)
- Run Gunicorn with Uvicorn workers for multi-core utilization and fault isolation in production -- [CYS Docs: FastAPI Production Deployment 2025](https://craftyourstartup.com/cys-docs/fastapi-production-deployment/)
- Use async context manager (lifespan) for startup/shutdown events instead of deprecated `on_event` -- [CYS Docs: FastAPI Lifecycle Management 2025](https://craftyourstartup.com/cys-docs/tutorials/fastapi-startup-and-shutdown-events-guide/)

**Security Middleware & CORS**
- Never use `allow_origins=["*"]` in production; specify explicit allowed origins from environment variables -- [David Muraya: FastAPI CORS Configuration](https://davidmuraya.com/blog/fastapi-cors-configuration/)
- Apply HTTPS enforcement, CORS policies, and rate limiting as layered middleware -- [ShipSafer: FastAPI Security Guide](https://www.shipsafer.app/blog/fastapi-security-guide)
- Use custom middleware for cross-cutting concerns (logging, timing, error handling) -- [Sizan Mahmud: FastAPI Middleware Production Guide](https://medium.com/@sizanmahmud08/securing-your-fastapi-application-with-middleware-a-production-ready-guide-part-2-8a6914f56e24)
- Add security headers (X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security) via middleware -- [FastAPI Security Best Practices](https://blog.greeden.me/en/2025/07/29/fastapi-security-best-practices-from-authentication-authorization-to-cors/)

**Rate Limiting**
- Apply per-IP rate limiting for anonymous users, per-user for authenticated requests -- [App-Generator: FastAPI Security](https://app-generator.dev/docs/technologies/fastapi/security-best-practices.html)
- Use Redis backend for consistent rate limiting across multiple instances -- [Zaman Rahimi: 8 FastAPI Security Best Practices](https://medium.com/@zaman.rahimi.rz/8-best-practices-to-make-python-fastapi-secure-785d75368a6e)
- Configure different limits per endpoint (stricter on auth endpoints, more lenient on reads)

**Authentication & Authorization**
- Use OAuth2 with JWT tokens for stateless authentication -- [David Muraya: FastAPI Security Guide](https://davidmuraya.com/blog/fastapi-security-guide/)
- Validate tokens per-request without database queries for basic validation
- Implement dependency injection for auth checks (FastAPI `Depends()`)

**Health Checks**
- Implement `/health` endpoint returning HTTP 200 with status info -- [Index.dev: FastAPI Health Check](https://www.index.dev/blog/how-to-implement-health-check-in-python)
- Separate liveness probes (app running) from readiness probes (can handle traffic) for container orchestration -- [DEV Community: Health-Check Microservice](https://dev.to/lisan_al_gaib/building-a-health-check-microservice-with-fastapi-26jo)
- Include dependency checks (database connectivity, external services) in readiness probe

**Logging & Error Handling**
- Use structured logging (JSON format) with correlation IDs per request -- [Deployra: Deploy FastAPI 2025](https://deployra.com/blog/deploy-fastapi-app)
- Never expose internal error details to clients; return generic messages with error codes
- Log request/response metadata (method, path, status, duration) via middleware
- Use exception handlers for consistent error response format

**Graceful Shutdown**
- Handle SIGTERM for container orchestration compatibility -- [Hash Block: Zero Downtime FastAPI](https://medium.com/@connect.hashblock/achieving-zero-downtime-fastapi-deployments-with-gunicorn-uvicorn-workers-and-health-probes-f169bdd524eb)
- Drain in-flight requests before shutting down
- Close database connections and background task queues cleanly

### Checklist for Audit

- [ ] Modular router-based project structure with clear separation of concerns
- [ ] CORS configured with explicit allowed origins (not wildcard `*`) loaded from environment variables
- [ ] Security headers middleware (X-Content-Type-Options, X-Frame-Options, HSTS, CSP)
- [ ] Rate limiting implemented with per-IP and/or per-user limits
- [ ] Rate limiting uses persistent backend (Redis) for multi-instance consistency
- [ ] Different rate limits for different endpoint types (auth vs. read vs. write)
- [ ] JWT/OAuth2 authentication with proper token validation
- [ ] Auth dependency injection using FastAPI `Depends()`
- [ ] `/health` endpoint returning HTTP 200 with status information
- [ ] Health check verifies database connectivity
- [ ] Structured logging with correlation IDs
- [ ] Request/response logging middleware (method, path, status, duration)
- [ ] No internal error details leaked to clients
- [ ] Consistent error response format across all endpoints
- [ ] Exception handlers registered for common error types
- [ ] Graceful shutdown handling (SIGTERM, connection draining)
- [ ] Lifespan context manager used (not deprecated `on_event`)
- [ ] Production server configuration (Gunicorn + Uvicorn workers)
- [ ] Async database operations (no sync blocking in async routes)
- [ ] Input validation using Pydantic models on all endpoints

---

## 2. React/TypeScript Production Best Practices

### Industry Best Practices (from web research)

**Error Boundaries**
- Use `react-error-boundary` library for TypeScript-native error boundary support without class components -- [Certificates.dev: Error Handling with react-error-boundary](https://certificates.dev/blog/error-handling-in-react-with-react-error-boundary)
- Place boundaries at logical divisions (routes, features) to isolate failures -- [DEV Community: React Error Boundaries](https://dev.to/blamsa0mine/react-error-boundaries-building-resilient-applications-that-dont-crash-4kc5)
- Error boundaries catch render errors only; use separate handling for async/event handler errors -- [OneUptime: Error Boundaries 2026](https://oneuptime.com/blog/post/2026-01-15-react-error-boundaries/view)
- Integrate with monitoring (Sentry) for production error tracking -- [TatvaSoft: React Error Boundary](https://www.tatvasoft.com/outsourcing/2025/02/react-error-boundary.html)

**State Management**
- Prefer Zustand for lightweight, simple global state over Redux for most applications -- [eSpark Info: React Best Practices 2026](https://www.esparkinfo.com/software-development/technologies/reactjs/best-practices)
- Use React Query / TanStack Query for server state (API data caching, background refetching)
- Keep component-local state in `useState`/`useReducer`; only elevate to global when needed

**API Client Architecture**
- Use Axios interceptors to automatically attach Authorization headers to all requests -- [Theashishmaurya: JWT Token Handling](https://blog.theashishmaurya.me/handling-jwt-access-and-refresh-token-using-axios-in-react-app)
- Implement response interceptors for automatic token refresh on 401 responses -- [DEV Community: JWT Refresh with Axios](https://dev.to/ayon_ssp/jwt-refresh-with-axios-interceptors-in-react-2bnk)
- Queue failed requests during token refresh and retry after new token is obtained -- [npm: axios-auth-refresh](https://www.npmjs.com/package/axios-auth-refresh)
- Centralize API client configuration (baseURL, headers, timeout) in a single module

**Authentication Token Handling**
- Store tokens in httpOnly cookies when possible (prevents XSS access) -- [CodeVoweb: JWT Authentication 2025](https://codevoweb.com/react-query-context-api-axios-interceptors-jwt-auth/)
- If using localStorage, implement token rotation and short expiry times
- Never store refresh tokens in localStorage in high-security applications
- Implement automatic logout on token expiry

**Environment Variable Management**
- Only variables prefixed with `VITE_` are exposed to the client; never put secrets in VITE_ variables -- [Vite Docs: Env Variables](https://vite.dev/guide/env-and-mode)
- Use `.env.example` file documenting all required variables without sensitive values -- [Mykola Aleksandrov: Vite Docker React Env Vars](https://www.mykolaaleksandrov.dev/posts/2025/10/vite-docker-react-environment-variables/)
- Add `.env` and `.env.*.local` to `.gitignore`
- Validate environment variables at build time or app startup

**Bundle Optimization & Performance**
- Use code splitting with `React.lazy()` and `Suspense` for route-level splitting
- Implement tree shaking by using named imports instead of default imports
- Use React 18+ concurrent features (useTransition, useDeferredValue) for UI responsiveness
- Memoize expensive computations with `useMemo` and callbacks with `useCallback`

### Checklist for Audit

- [ ] Error boundaries implemented at route/feature level
- [ ] Error boundaries display user-friendly fallback UI
- [ ] Error reporting integrated with monitoring service (Sentry or equivalent)
- [ ] Async/event handler errors caught and handled separately from render errors
- [ ] Server state managed with React Query or equivalent (caching, background refetch)
- [ ] Global state management is lightweight (Zustand/Context, not over-engineered)
- [ ] API client centralized with base URL configuration
- [ ] Axios/fetch interceptors for automatic auth token attachment
- [ ] Token refresh flow implemented (automatic retry on 401)
- [ ] Tokens stored securely (httpOnly cookies preferred, or short-lived localStorage)
- [ ] Automatic logout on token/session expiry
- [ ] No secrets in VITE_* environment variables
- [ ] `.env.example` file with all required variables documented
- [ ] `.env` files excluded from version control (.gitignore)
- [ ] Environment variables validated at startup
- [ ] Code splitting implemented for routes (React.lazy/Suspense)
- [ ] TypeScript strict mode enabled
- [ ] Functional components with hooks (no class components)
- [ ] Performance optimizations (useMemo, useCallback where appropriate)
- [ ] Loading states displayed during async operations
- [ ] Empty states handled for lists/tables with no data

---

## 3. PostgreSQL/Supabase Production Best Practices

### Industry Best Practices (from web research)

**Connection Pooling**
- Use PgBouncer or built-in Supabase connection pooling for all production workloads -- [Instaclustr: Top 10 PostgreSQL Best Practices 2025](https://www.instaclustr.com/education/postgresql/top-10-postgresql-best-practices-for-2025/)
- Choose transaction pooling mode for web applications (connection shared per transaction, not per session) -- [Microsoft: Connection Pooling Best Practices](https://learn.microsoft.com/en-us/azure/postgresql/connectivity/concepts-connection-pooling-best-practices)
- Set pool size limits appropriate for your plan (Supabase has specific limits per tier) -- [AI2SQL: Database Connection Pooling Guide](https://ai2sql.io/learn/database-connection-pooling-guide)
- Monitor connection utilization and adjust pool sizes based on actual usage

**Index Optimization**
- Create indexes for columns used in WHERE clauses, JOIN conditions, and ORDER BY -- [TechStackGuide: PostgreSQL Performance 2025](https://techstackguide.com/postgresql-performance-optimization/)
- Use B-tree indexes for equality/range queries; GIN indexes for full-text search and JSONB -- [DEV Community: PostgreSQL Tuning 2026](https://dev.to/_d7eb1c1703182e3ce1782/postgresql-performance-tuning-checklist-2026-complete-guide-65a)
- Avoid over-indexing (increases write overhead and disk usage)
- Create indexes on columns used in RLS policies

**Row-Level Security (Supabase-specific)**
- Enable RLS on ALL user-facing tables -- mandatory for production -- [Supabase Docs: RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)
- Use `auth.uid()` in policies for user-scoped access -- [Supabase Docs: Production Checklist](https://supabase.com/docs/guides/deployment/going-into-prod)
- Always specify `authenticated` role in policies; never rely solely on `auth.uid()` to exclude `anon` -- [Medium: Supabase RLS Explained](https://medium.com/@jigsz6391/supabase-row-level-security-explained-with-real-examples-6d06ce8d221c)
- Add indexes on columns used within RLS policies for performance -- [Supabase Docs: RLS Performance](https://supabase.com/docs/guides/troubleshooting/rls-performance-and-best-practices-Z5Jjwv)
- Always filter queries explicitly even with RLS (don't rely on "implicit where")

**Security (Supabase-specific)**
- Never expose `service_role` key on the frontend -- [Medium: Securing Supabase](https://medium.com/@firmanbrilian/best-practices-for-securing-and-scaling-supabase-for-production-data-workloads-4394aba9e868)
- Enable SSL enforcement in database settings -- [Supabase Docs: Production Checklist](https://supabase.com/docs/guides/deployment/going-into-prod)
- Enable network restrictions to limit database access by IP
- Use short-lived JWTs and rotate keys periodically
- Run Security Advisor to identify issues

**Backup & Recovery**
- Enable automated backups (daily minimum) -- [Supabase Docs: Production Checklist](https://supabase.com/docs/guides/deployment/going-into-prod)
- Enable Point-in-Time Recovery (PITR) for databases exceeding 4 GB
- Test restore procedures regularly
- Store backups in a different region/zone

**Migration Best Practices**
- Use a migration tool (Alembic for Python) with version-controlled migration files
- Never modify production schema manually; always use migrations
- Include both upgrade and downgrade paths in migrations
- Test migrations against a staging database before production

**Monitoring**
- Enable `pg_stat_statements` extension for query performance tracking -- [Instaclustr: Top 10 PostgreSQL Best Practices 2025](https://www.instaclustr.com/education/postgresql/top-10-postgresql-best-practices-for-2025/)
- Run ANALYZE and VACUUM regularly for query planner accuracy -- [PloyCloud: PostgreSQL Hosting Guide 2025](https://ploy.cloud/blog/postgresql-hosting-guide-2025/)
- Monitor connection count, query latency, and cache hit ratios

### Checklist for Audit

- [ ] Connection pooling configured (PgBouncer or Supabase pooler)
- [ ] Using transaction pooling mode for web application workloads
- [ ] Pool size limits set appropriately for the deployment tier
- [ ] Indexes created for frequently queried columns (WHERE, JOIN, ORDER BY)
- [ ] Indexes created for columns used in RLS policies
- [ ] No excessive/unused indexes consuming write overhead
- [ ] RLS enabled on ALL user-facing tables
- [ ] RLS policies use `auth.uid()` for user-scoped access
- [ ] RLS policies specify `authenticated` role explicitly
- [ ] Queries explicitly filter data (not relying solely on RLS implicit filtering)
- [ ] `service_role` key never exposed in frontend code
- [ ] SSL enforcement enabled on database
- [ ] Network restrictions configured (IP allowlisting)
- [ ] Automated backups enabled
- [ ] PITR enabled if database exceeds 4 GB
- [ ] Migration tool (Alembic) with version-controlled migrations
- [ ] Migrations include both upgrade and downgrade paths
- [ ] `pg_stat_statements` enabled for query monitoring
- [ ] Regular VACUUM/ANALYZE configured or Supabase auto-maintenance verified
- [ ] Database credentials rotated periodically
- [ ] MFA enabled on Supabase dashboard account

---

## 4. Docker Production Best Practices

### Industry Best Practices (from web research)

**Multi-Stage Builds**
- Use multi-stage builds to separate build environment from runtime (reduces image size by 80%+) -- [Owais.io: Dockerfile Best Practices Part 2](https://www.owais.io/blog/2025-10-03_dockerfile-best-practices-security-production/)
- Build stage: install dependencies, compile code; Runtime stage: copy only artifacts needed -- [Nerd Level Tech: Docker Best Practices 2025](https://nerdleveltech.com/mastering-docker-best-practices-for-2025)
- Use minimal base images (Alpine, distroless, slim variants) for runtime stage -- [Saraswathi Lakshman: Docker Image Optimization 2025](https://saraswathilakshman.medium.com/optimise-your-docker-images-for-speed-and-security-best-practices-for-2025-e888f6dc131f)

**Security Hardening**
- Run containers as non-root user (include USER instruction) -- [Sysdig: Dockerfile Best Practices](https://www.sysdig.com/learn-cloud-native/dockerfile-best-practices)
- Make filesystem read-only where possible -- [ZeonEdge: Docker Security 2026](https://zeonedge.com/blog/docker-security-best-practices-2026-hardening-containers-build-runtime)
- Never store secrets in Docker images or layers -- [TheLinuxCode: Docker Security 2026](https://thelinuxcode.com/docker-security-best-practices-2026-hardening-the-host-images-and-runtime-without-slowing-teams-down/)
- Install as root in build stage, run as non-root in runtime stage
- Drop all capabilities and only add what's needed

**Layer Caching**
- Order Dockerfile instructions from least to most frequently changing -- [BenchHub: Docker Best Practices 2025](https://docs.benchhub.co/docs/tutorials/docker/docker-best-practices-2025)
- Copy dependency files (requirements.txt, package.json) before source code
- Use `.dockerignore` to exclude unnecessary files (node_modules, .git, tests, docs)

**Image Management**
- Pin base image versions (never use `latest` tag) -- [Mykola Aleksandrov: Docker Production 2026](https://www.mykolaaleksandrov.dev/posts/2026/02/docker-production-best-practices/)
- For high assurance, pin by digest (SHA256)
- Scan images regularly for vulnerabilities (Trivy, Snyk, Docker Scout)
- Keep images small -- fewer packages means fewer vulnerabilities

**Health Checks**
- Include HEALTHCHECK instruction in Dockerfile -- [Medium: Health Checks for FastAPI](https://medium.com/@ntjegadeesh/implementing-health-checks-and-auto-restarts-for-fastapi-applications-using-docker-and-4245aab27ece)
- Configure appropriate interval, timeout, start_period, and retries
- Health check should verify the application is truly ready to serve

### Checklist for Audit

- [ ] Multi-stage build used (separate build and runtime stages)
- [ ] Minimal base image for runtime (Alpine, slim, or distroless)
- [ ] Container runs as non-root user (USER instruction present)
- [ ] No secrets baked into image layers
- [ ] Base image versions pinned (not using `latest`)
- [ ] `.dockerignore` file present and comprehensive
- [ ] Dependency files copied before source code (layer caching optimization)
- [ ] Instructions ordered least-to-most-changing for cache efficiency
- [ ] HEALTHCHECK instruction included in Dockerfile
- [ ] Image size is reasonable (not carrying build tools in runtime)
- [ ] No unnecessary packages installed in runtime image
- [ ] Vulnerability scanning configured (Trivy, Snyk, Docker Scout, or equivalent)
- [ ] Docker Compose production configuration separate from development
- [ ] Container resource limits defined (memory, CPU)
- [ ] Logs directed to stdout/stderr for container log collection

---

## 5. Railway Deployment Best Practices

### Industry Best Practices (from web research)

**Environment Management**
- Use Railway's Variables tab for production settings; never commit secrets to version control -- [Railway Docs: Deploy Guide](https://docs.railway.com/guides/deploy-node-express-api-with-auto-scaling-secrets-and-zero-downtime)
- Use shared variables (`${{shared.DATABASE_URL}}`) across services to eliminate duplication
- Maintain separate environments (staging, production) with independent variable sets
- Use `railway.toml` for non-sensitive deployment configuration

**Health Checks for Zero-Downtime Deploys**
- Configure a `/health` endpoint returning HTTP 200 when the app is ready -- [Railway Docs: Healthchecks](https://docs.railway.com/deployments/healthchecks)
- Railway only switches traffic to new deployment after health check passes -- [Railway Docs: Configure Healthchecks](https://docs.railway.com/guides/healthchecks)
- Set `RAILWAY_HEALTHCHECK_TIMEOUT_SEC` appropriately (default is 300 seconds) -- [Railway Help Station: Health Check Timeout](https://station.railway.com/questions/how-to-set-a-health-check-timeout-1af79182)
- Ensure app listens on the `PORT` environment variable injected by Railway

**Scaling**
- Vertical scaling is automatic on Railway (CPU/memory increase with traffic) -- [Railway Docs: Deploy Guide](https://docs.railway.com/guides/deploy-node-express-api-with-auto-scaling-secrets-and-zero-downtime)
- Horizontal scaling via replicas (each gets full resource allocation)
- Consider multi-region deployment for global traffic routing

**Graceful Shutdown**
- Set `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` to allow in-flight requests to complete (default is 0) -- [Railway Docs: Deployment Teardown](https://docs.railway.com/guides/deployment-teardown)
- Handle SIGTERM signal in application code for clean shutdown
- Close database connections and flush logs on shutdown

**Monitoring & Reliability**
- Configure health check restarts for automatic recovery from crashes -- [Railway Docs: Healthchecks and Restarts](https://docs.railway.com/guides/healthchecks-and-restarts)
- Monitor deployment logs via Railway dashboard
- Use Pro plan for production workloads (prevents pausing for inactivity)

### Checklist for Audit

- [ ] `/health` endpoint configured and returning HTTP 200
- [ ] Health check path configured in Railway deployment settings
- [ ] `RAILWAY_HEALTHCHECK_TIMEOUT_SEC` set appropriately
- [ ] Application listens on Railway-injected `PORT` environment variable
- [ ] `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` set > 0 for graceful shutdown
- [ ] SIGTERM handler implemented for clean shutdown
- [ ] All secrets stored in Railway Variables (not in code or docker image)
- [ ] Shared variables used for cross-service configuration
- [ ] Separate staging and production environments
- [ ] `railway.toml` present with deployment configuration
- [ ] Pro plan or higher for production (no inactivity pausing)
- [ ] Deployment logs monitored
- [ ] Automatic restart configured for crash recovery

---

## 6. Web Application Security (OWASP Top 10 2025)

### Industry Best Practices (from web research)

The OWASP Top 10 2025 identifies these critical risk categories:

| # | Category | Key Mitigation |
|---|----------|---------------|
| A01 | Broken Access Control | Least privilege, RBAC, deny by default |
| A02 | Security Misconfiguration | Automated config management, security baselines |
| A03 | Software Supply Chain Failures | Verify package integrity, pin versions, audit dependencies |
| A04 | Cryptographic Failures | Strong algorithms (AES, TLS 1.3), encrypt at rest and in transit |
| A05 | Injection (incl. XSS, SQLi) | Parameterized queries, output encoding, CSP headers |
| A06 | Insecure Design | Threat modeling, secure design patterns |
| A07 | Authentication Failures | MFA, rate-limited auth, standardized frameworks |
| A08 | Software/Data Integrity Failures | Verify CI/CD integrity, signed artifacts |
| A09 | Security Logging & Alerting Failures | Comprehensive logging with alerting capability |
| A10 | Mishandling of Exceptional Conditions | Fail closed, sanitize error output, secure exception handling |

Sources: [OWASP Top 10:2025](https://owasp.org/Top10/2025/), [OWASP Introduction](https://owasp.org/Top10/2025/0x00_2025-Introduction/), [Aikido: OWASP Changes for Developers](https://www.aikido.dev/blog/owasp-top-10-2025-changes-for-developers), [aTeam: Security Checklist 2025](https://www.ateamsoftsolutions.com/web-application-security-checklist-2025-complete-owasp-top-10-implementation-guide-for-ctos/), [Fastly: OWASP 2025](https://www.fastly.com/blog/new-2025-owasp-top-10-list-what-changed-what-you-need-to-know)

**Authentication Best Practices**
- Implement multi-factor authentication (MFA) -- [OWASP: A07:2025](https://owasp.org/Top10/2025/)
- Use standardized authentication frameworks (Supabase Auth, Auth0, etc.)
- Rate limit login attempts to prevent brute force
- Enforce password complexity requirements
- Use bcrypt/argon2 for password hashing

**Authorization Patterns**
- Deny access by default; explicitly grant permissions -- [OWASP: A01:2025](https://owasp.org/Top10/2025/)
- Implement role-based access control (RBAC) consistently
- Validate authorization server-side on every request (never trust client-side checks)
- Log authorization failures for monitoring

**Input Validation**
- Validate all input on the server side regardless of client-side validation -- [OWASP: A05:2025](https://owasp.org/Top10/2025/)
- Use parameterized queries (never string concatenation for SQL)
- Validate data type, length, range, and format

**Output Encoding**
- Encode output based on context (HTML, JavaScript, URL, CSS) -- [OWASP: A05:2025](https://owasp.org/Top10/2025/)
- Use React's built-in JSX escaping (avoid `dangerouslySetInnerHTML`)

**CSRF Protection**
- Use SameSite cookie attribute (Lax or Strict) -- [OWASP: CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- For API-driven SPAs, use custom request headers (e.g., `X-Requested-With`)
- Stateless apps: use double-submit cookie pattern

**Security Headers**
- `Content-Security-Policy`: Restrict script/resource origins -- [OWASP: CSP Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
- `Strict-Transport-Security`: Enforce HTTPS (HSTS) -- [OWASP: HTTP Headers Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html)
- `X-Content-Type-Options: nosniff`: Prevent MIME type sniffing
- `X-Frame-Options: DENY` or `SAMEORIGIN` (or CSP frame-ancestors): Prevent clickjacking
- `Referrer-Policy`: Control information leakage
- `Permissions-Policy`: Restrict browser feature access

**Error Handling**
- Systems must "fail closed" -- security controls remain enforced under abnormal conditions -- [OWASP: A10:2025](https://owasp.org/Top10/2025/)
- Sanitize all error outputs; never expose stack traces or internal details
- Log exceptions with context for debugging but return generic messages to clients

### Checklist for Audit

**A01: Broken Access Control**
- [ ] Deny by default; permissions explicitly granted
- [ ] RBAC implemented consistently across all endpoints
- [ ] Server-side authorization check on every request
- [ ] Authorization failures logged
- [ ] No direct object reference vulnerabilities (IDOR)

**A02: Security Misconfiguration**
- [ ] Security headers configured (CSP, HSTS, X-Content-Type-Options, X-Frame-Options)
- [ ] Default credentials changed/removed
- [ ] Unnecessary features/endpoints disabled
- [ ] Error messages do not reveal stack traces or implementation details
- [ ] Directory listing disabled

**A03: Software Supply Chain**
- [ ] Dependencies pinned to specific versions
- [ ] Dependency audit configured (npm audit, pip audit, or equivalent)
- [ ] Lock files (uv.lock, package-lock.json) committed to version control
- [ ] No known vulnerable dependencies

**A04: Cryptographic Failures**
- [ ] TLS/HTTPS enforced for all connections
- [ ] Sensitive data encrypted at rest
- [ ] Strong hashing algorithms for passwords (bcrypt/argon2)
- [ ] No hardcoded secrets or keys in source code

**A05: Injection**
- [ ] Parameterized queries used (no string concatenation for SQL)
- [ ] Input validation on all user-supplied data (server-side)
- [ ] Output encoding appropriate to context
- [ ] Content Security Policy header configured

**A07: Authentication Failures**
- [ ] Rate limiting on authentication endpoints
- [ ] Secure session management (token expiry, rotation)
- [ ] Password complexity requirements enforced
- [ ] MFA available or enforced for sensitive operations

**A09: Security Logging & Alerting**
- [ ] Authentication events logged (login, logout, failed attempts)
- [ ] Authorization failures logged
- [ ] Logs include sufficient context (user ID, IP, timestamp, action)
- [ ] Log injection prevented (sanitize user input in log messages)
- [ ] Alerting configured for suspicious patterns

**A10: Mishandling of Exceptional Conditions**
- [ ] Application fails closed (security controls maintained on error)
- [ ] All exceptions caught and handled explicitly
- [ ] Error responses sanitized (no internal details leaked)
- [ ] Graceful degradation on external service failures

---

## 7. CI/CD Best Practices (GitHub Actions)

### Industry Best Practices (from web research)

**Pipeline Design**
- Use distinct jobs for each phase: build, test, security scan, deploy -- [GitHub: Awesome Copilot CI/CD Instructions](https://github.com/github/awesome-copilot/blob/main/instructions/github-actions-ci-cd-best-practices.instructions.md)
- Define dependencies with `needs` clauses for proper ordering
- Use `concurrency` settings to prevent simultaneous runs on the same branch -- [Security Boulevard: GitHub Actions CI/CD](https://securityboulevard.com/2025/11/how-to-build-and-implement-ci-cd-pipeline-with-github-actions/)
- Use matrix strategies for testing across multiple configurations
- Keep workflows modular and reusable with composite actions

**Secret Management**
- Store all credentials in GitHub Secrets, never hardcode -- [Blacksmith: Secret Management Best Practices](https://www.blacksmith.sh/blog/best-practices-for-managing-secrets-in-github-actions)
- Use OIDC for cloud provider authentication (eliminates long-lived credentials) -- [NeoVA Solutions: GitHub Actions Secrets](https://www.neovasolutions.com/2025/02/06/github-actions-how-to-secure-secrets-and-credentials-in-ci-cd/)
- Rotate secrets regularly (30-90 days)
- Use environment-specific secrets with approval workflows for production
- Restrict secret scope to only necessary workflows/jobs

**Action Security**
- Pin marketplace actions to full commit SHAs (not mutable tags like `@v4`) -- [GitHub Blog: Actions 2026 Security Roadmap](https://github.blog/news-insights/product-news/whats-coming-to-our-github-actions-2026-security-roadmap/)
- Set explicit `permissions` on GITHUB_TOKEN (read-only by default) -- [GitHub: Awesome Copilot CI/CD Instructions](https://github.com/github/awesome-copilot/blob/main/instructions/github-actions-ci-cd-best-practices.instructions.md)
- Review third-party actions before use
- Use `actions/dependency-review-action` for PR dependency scanning

**Testing Strategy**
- Implement testing pyramid: unit > integration > E2E -- [GitHub: Awesome Copilot CI/CD Instructions](https://github.com/github/awesome-copilot/blob/main/instructions/github-actions-ci-cd-best-practices.instructions.md)
- Run fast tests first, slow tests later (fail fast)
- Use test reporting for visibility
- Cache dependencies and test artifacts between runs

**Deployment Gates**
- Require environment approval for production deployments -- [NamasteDev: Securing CI/CD Pipeline](https://namastedev.com/blog/securing-your-ci-cd-pipeline-managing-secrets-and-tokens-with-github-actions/)
- Run security scanning (SAST, SCA) as blocking steps before deploy
- Enforce dependency reviews on pull requests
- Require passing CI checks before merge

**Rollback Strategies**
- Maintain artifact immutability for deployments -- [GitHub: Awesome Copilot CI/CD Instructions](https://github.com/github/awesome-copilot/blob/main/instructions/github-actions-ci-cd-best-practices.instructions.md)
- Store build outputs as artifacts with appropriate retention
- Enable quick redeployment of previous verified versions
- Test rollback procedures regularly

**Caching & Performance**
- Use `actions/cache` with hash-based cache keys for dependencies -- [NetApp: GitHub Actions Best Practices](https://www.netapp.com/learn/cvo-blg-5-github-actions-cicd-best-practices/)
- Cache Docker layers for faster image builds
- Use `upload-artifact`/`download-artifact` for passing data between jobs

### Checklist for Audit

- [ ] CI pipeline runs on pull requests (not just pushes)
- [ ] Distinct jobs for build, test, lint, security scan, deploy
- [ ] Job dependencies defined with `needs` clauses
- [ ] `concurrency` configured to prevent duplicate runs
- [ ] All secrets stored in GitHub Secrets (none hardcoded)
- [ ] GITHUB_TOKEN permissions explicitly set (minimal scope)
- [ ] Third-party actions pinned to commit SHAs (not mutable tags)
- [ ] Unit tests run in CI
- [ ] Integration tests run in CI
- [ ] Linting/formatting checks run in CI
- [ ] Security scanning (dependency audit, SAST) in pipeline
- [ ] Environment protection rules for production deployment
- [ ] Deployment requires passing CI checks
- [ ] Build artifacts stored with appropriate retention
- [ ] Dependency caching configured for faster builds
- [ ] Docker layer caching configured
- [ ] Rollback mechanism documented and tested
- [ ] Branch protection rules enforced (require PR, require CI pass)
- [ ] No force-push to main/master allowed

---

## 8. REST API Design Best Practices

### Industry Best Practices (from web research)

**Versioning**
- Use URL path versioning (`/api/v1/...`) as the most common and discoverable approach -- [Speakeasy: Versioning Best Practices](https://www.speakeasy.com/api-design/versioning)
- Only introduce new versions for breaking changes (removed fields, type changes, auth changes) -- [Postman: REST API Best Practices](https://blog.postman.com/rest-api-best-practices/)
- Include deprecation warnings via `Sunset` header for end-of-life endpoints -- [Codebrand: REST API Design 2026](https://www.codebrand.us/blog/rest-api-design-best-practices-2026/)
- Maintain backward compatibility; non-breaking additions don't need new versions

**Pagination**
- Never return unbounded result sets; always paginate collection endpoints -- [Strapi: RESTful API Design Guide](https://strapi.io/blog/restful-api-design-guide-principles-best-practices)
- Use cursor-based pagination for large/changing datasets (more performant than offset) -- [OneUptime: REST API Design 2026](https://oneuptime.com/blog/post/2026-02-20-api-design-rest-best-practices/view)
- Include pagination metadata in responses (total count, next cursor/page, has_more) -- [dotMock: RESTful API Best Practices 2025](https://dotmock.com/blog/restful-api-best-practices)
- Return consistent pagination structure across all list endpoints

**Error Responses**
- Use correct HTTP status codes semantically (400 client error, 500 server error) -- [Stack Overflow: REST API Design](https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/)
- Define a standard error format and use it everywhere (error code, message, details) -- [Microsoft: API Design Best Practices](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- Include machine-readable error codes alongside human-readable messages
- Never expose internal details in error responses (stack traces, SQL errors)
- Use Problem Details format (RFC 9457) for structured error responses

**Rate Limiting**
- Apply rate limits to all public endpoints -- [DEV Community: REST API Design](https://dev.to/_d7eb1c1703182e3ce1782/understanding-rest-api-design-best-practices-7gf)
- Return `429 Too Many Requests` with `Retry-After` header
- Include rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)
- Apply stricter limits on write operations and authentication endpoints

**Documentation**
- Provide OpenAPI/Swagger documentation auto-generated from code -- [Postman: REST API Best Practices](https://blog.postman.com/rest-api-best-practices/)
- FastAPI auto-generates OpenAPI docs at `/docs` (Swagger UI) and `/redoc`
- Keep documentation in sync with actual API behavior
- Include request/response examples for each endpoint

**Resource Design**
- Use nouns for resource names, not verbs (`/datasets` not `/getDatasets`) -- [SBB: API Best Practices](https://schweizerischebundesbahnen.github.io/api-principles/restful/best-practices/)
- Use plural nouns for collection endpoints
- Nest resources logically (`/datasets/{id}/results`)
- Support filtering via query parameters

### Checklist for Audit

- [ ] API versioning implemented (URL path: `/api/v1/`)
- [ ] Versioning strategy documented
- [ ] All collection endpoints paginated (no unbounded responses)
- [ ] Pagination metadata included in responses (total, next, has_more)
- [ ] Consistent pagination format across all list endpoints
- [ ] Standard error response format used across all endpoints
- [ ] Correct HTTP status codes used semantically
- [ ] Machine-readable error codes included in error responses
- [ ] No internal details leaked in error responses
- [ ] Rate limiting applied to public endpoints
- [ ] `429 Too Many Requests` returned with `Retry-After` header
- [ ] Rate limit headers included in responses (X-RateLimit-*)
- [ ] OpenAPI/Swagger documentation available and auto-generated
- [ ] Documentation accessible at `/docs` or `/redoc`
- [ ] Resource names use plural nouns (not verbs)
- [ ] Logical resource nesting where appropriate
- [ ] Filtering supported via query parameters
- [ ] Consistent response envelope/structure across all endpoints
- [ ] PATCH used for partial updates, PUT for full replacement
- [ ] 201 Created returned for successful POST operations with Location header

---

## Summary: Quick Reference Counts

| Category | Checklist Items |
|----------|----------------|
| 1. FastAPI Production | 20 items |
| 2. React/TypeScript | 21 items |
| 3. PostgreSQL/Supabase | 21 items |
| 4. Docker Production | 15 items |
| 5. Railway Deployment | 13 items |
| 6. OWASP Security | 30 items |
| 7. CI/CD (GitHub Actions) | 19 items |
| 8. REST API Design | 20 items |
| **TOTAL** | **159 items** |

---

## Sources

### FastAPI
- [Render: FastAPI Production Deployment](https://render.com/articles/fastapi-production-deployment-best-practices)
- [CYS Docs: FastAPI Production Deployment 2025](https://craftyourstartup.com/cys-docs/fastapi-production-deployment/)
- [CYS Docs: FastAPI Lifecycle Management](https://craftyourstartup.com/cys-docs/tutorials/fastapi-startup-and-shutdown-events-guide/)
- [David Muraya: FastAPI Security Guide](https://davidmuraya.com/blog/fastapi-security-guide/)
- [David Muraya: FastAPI CORS Configuration](https://davidmuraya.com/blog/fastapi-cors-configuration/)
- [ShipSafer: FastAPI Security Guide](https://www.shipsafer.app/blog/fastapi-security-guide)
- [Sizan Mahmud: FastAPI Middleware Production Guide](https://medium.com/@sizanmahmud08/securing-your-fastapi-application-with-middleware-a-production-ready-guide-part-2-8a6914f56e24)
- [FastAPI Security Best Practices](https://blog.greeden.me/en/2025/07/29/fastapi-security-best-practices-from-authentication-authorization-to-cors/)
- [App-Generator: FastAPI Security](https://app-generator.dev/docs/technologies/fastapi/security-best-practices.html)
- [Index.dev: FastAPI Health Check](https://www.index.dev/blog/how-to-implement-health-check-in-python)
- [DEV Community: Health-Check Microservice with FastAPI](https://dev.to/lisan_al_gaib/building-a-health-check-microservice-with-fastapi-26jo)
- [Deployra: Deploy FastAPI 2025](https://deployra.com/blog/deploy-fastapi-app)
- [Hash Block: Zero Downtime FastAPI](https://medium.com/@connect.hashblock/achieving-zero-downtime-fastapi-deployments-with-gunicorn-uvicorn-workers-and-health-probes-f169bdd524eb)
- [Zaman Rahimi: 8 FastAPI Security Best Practices](https://medium.com/@zaman.rahimi.rz/8-best-practices-to-make-python-fastapi-secure-785d75368a6e)

### React/TypeScript
- [Certificates.dev: Error Handling with react-error-boundary](https://certificates.dev/blog/error-handling-in-react-with-react-error-boundary)
- [DEV Community: React Error Boundaries](https://dev.to/blamsa0mine/react-error-boundaries-building-resilient-applications-that-dont-crash-4kc5)
- [eSpark Info: React Best Practices 2026](https://www.esparkinfo.com/software-development/technologies/reactjs/best-practices)
- [OneUptime: Error Boundaries 2026](https://oneuptime.com/blog/post/2026-01-15-react-error-boundaries/view)
- [TatvaSoft: React Error Boundary](https://www.tatvasoft.com/outsourcing/2025/02/react-error-boundary.html)
- [Theashishmaurya: JWT Token Handling](https://blog.theashishmaurya.me/handling-jwt-access-and-refresh-token-using-axios-in-react-app)
- [DEV Community: JWT Refresh with Axios](https://dev.to/ayon_ssp/jwt-refresh-with-axios-interceptors-in-react-2bnk)
- [CodeVoweb: JWT Authentication 2025](https://codevoweb.com/react-query-context-api-axios-interceptors-jwt-auth/)
- [npm: axios-auth-refresh](https://www.npmjs.com/package/axios-auth-refresh)
- [Vite Docs: Env Variables](https://vite.dev/guide/env-and-mode)
- [Mykola Aleksandrov: Vite Docker React Env Vars](https://www.mykolaaleksandrov.dev/posts/2025/10/vite-docker-react-environment-variables/)

### PostgreSQL/Supabase
- [Instaclustr: Top 10 PostgreSQL Best Practices 2025](https://www.instaclustr.com/education/postgresql/top-10-postgresql-best-practices-for-2025/)
- [TechStackGuide: PostgreSQL Performance 2025](https://techstackguide.com/postgresql-performance-optimization/)
- [DEV Community: PostgreSQL Tuning 2026](https://dev.to/_d7eb1c1703182e3ce1782/postgresql-performance-tuning-checklist-2026-complete-guide-65a)
- [Microsoft: Connection Pooling Best Practices](https://learn.microsoft.com/en-us/azure/postgresql/connectivity/concepts-connection-pooling-best-practices)
- [AI2SQL: Database Connection Pooling Guide](https://ai2sql.io/learn/database-connection-pooling-guide)
- [PloyCloud: PostgreSQL Hosting Guide 2025](https://ploy.cloud/blog/postgresql-hosting-guide-2025/)
- [Supabase Docs: RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase Docs: Production Checklist](https://supabase.com/docs/guides/deployment/going-into-prod)
- [Supabase Docs: RLS Performance](https://supabase.com/docs/guides/troubleshooting/rls-performance-and-best-practices-Z5Jjwv)
- [Medium: Securing Supabase](https://medium.com/@firmanbrilian/best-practices-for-securing-and-scaling-supabase-for-production-data-workloads-4394aba9e868)
- [Medium: Supabase RLS Explained](https://medium.com/@jigsz6391/supabase-row-level-security-explained-with-real-examples-6d06ce8d221c)

### Docker
- [Owais.io: Dockerfile Best Practices Part 2](https://www.owais.io/blog/2025-10-03_dockerfile-best-practices-security-production/)
- [Nerd Level Tech: Docker Best Practices 2025](https://nerdleveltech.com/mastering-docker-best-practices-for-2025)
- [Saraswathi Lakshman: Docker Image Optimization 2025](https://saraswathilakshman.medium.com/optimise-your-docker-images-for-speed-and-security-best-practices-for-2025-e888f6dc131f)
- [Sysdig: Dockerfile Best Practices](https://www.sysdig.com/learn-cloud-native/dockerfile-best-practices)
- [ZeonEdge: Docker Security 2026](https://zeonedge.com/blog/docker-security-best-practices-2026-hardening-containers-build-runtime)
- [TheLinuxCode: Docker Security 2026](https://thelinuxcode.com/docker-security-best-practices-2026-hardening-the-host-images-and-runtime-without-slowing-teams-down/)
- [BenchHub: Docker Best Practices 2025](https://docs.benchhub.co/docs/tutorials/docker/docker-best-practices-2025)
- [Mykola Aleksandrov: Docker Production 2026](https://www.mykolaaleksandrov.dev/posts/2026/02/docker-production-best-practices/)
- [Medium: Health Checks for FastAPI with Docker](https://medium.com/@ntjegadeesh/implementing-health-checks-and-auto-restarts-for-fastapi-applications-using-docker-and-4245aab27ece)

### Railway
- [Railway Docs: Healthchecks](https://docs.railway.com/deployments/healthchecks)
- [Railway Docs: Configure Healthchecks](https://docs.railway.com/guides/healthchecks)
- [Railway Docs: Healthchecks and Restarts](https://docs.railway.com/guides/healthchecks-and-restarts)
- [Railway Docs: Deploy Guide](https://docs.railway.com/guides/deploy-node-express-api-with-auto-scaling-secrets-and-zero-downtime)
- [Railway Docs: Deployment Teardown](https://docs.railway.com/guides/deployment-teardown)
- [Railway Help Station: Health Check Timeout](https://station.railway.com/questions/how-to-set-a-health-check-timeout-1af79182)

### OWASP Security
- [OWASP Top 10:2025](https://owasp.org/Top10/2025/)
- [OWASP Top 10:2025 Introduction](https://owasp.org/Top10/2025/0x00_2025-Introduction/)
- [Aikido: OWASP 2025 Changes for Developers](https://www.aikido.dev/blog/owasp-top-10-2025-changes-for-developers)
- [aTeam: Security Checklist 2025](https://www.ateamsoftsolutions.com/web-application-security-checklist-2025-complete-owasp-top-10-implementation-guide-for-ctos/)
- [Fastly: OWASP 2025](https://www.fastly.com/blog/new-2025-owasp-top-10-list-what-changed-what-you-need-to-know)
- [eSecurity Planet: OWASP 2025](https://www.esecurityplanet.com/threats/news-owasp-top-10-2025/)
- [Equixly: OWASP 2025 vs 2021](https://equixly.com/blog/2025/12/01/owasp-top-10-2025-vs-2021/)
- [OWASP: CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP: CSP Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
- [OWASP: HTTP Headers Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html)

### CI/CD (GitHub Actions)
- [GitHub Blog: Actions 2026 Security Roadmap](https://github.blog/news-insights/product-news/whats-coming-to-our-github-actions-2026-security-roadmap/)
- [GitHub: Awesome Copilot CI/CD Instructions](https://github.com/github/awesome-copilot/blob/main/instructions/github-actions-ci-cd-best-practices.instructions.md)
- [Security Boulevard: GitHub Actions CI/CD](https://securityboulevard.com/2025/11/how-to-build-and-implement-ci-cd-pipeline-with-github-actions/)
- [Blacksmith: Secret Management Best Practices](https://www.blacksmith.sh/blog/best-practices-for-managing-secrets-in-github-actions)
- [NeoVA Solutions: GitHub Actions Secrets](https://www.neovasolutions.com/2025/02/06/github-actions-how-to-secure-secrets-and-credentials-in-ci-cd/)
- [NamasteDev: Securing CI/CD Pipeline](https://namastedev.com/blog/securing-your-ci-cd-pipeline-managing-secrets-and-tokens-with-github-actions/)
- [NetApp: GitHub Actions Best Practices](https://www.netapp.com/learn/cvo-blg-5-github-actions-cicd-best-practices/)

### REST API Design
- [Postman: REST API Best Practices](https://blog.postman.com/rest-api-best-practices/)
- [Strapi: RESTful API Design Guide](https://strapi.io/blog/restful-api-design-guide-principles-best-practices)
- [Speakeasy: Versioning Best Practices](https://www.speakeasy.com/api-design/versioning)
- [dotMock: RESTful API Best Practices 2025](https://dotmock.com/blog/restful-api-best-practices)
- [Microsoft: API Design Best Practices](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- [Stack Overflow: REST API Design](https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/)
- [Codebrand: REST API Design 2026](https://www.codebrand.us/blog/rest-api-design-best-practices-2026/)
- [OneUptime: REST API Design 2026](https://oneuptime.com/blog/post/2026-02-20-api-design-rest-best-practices/view)
- [DEV Community: REST API Design](https://dev.to/_d7eb1c1703182e3ce1782/understanding-rest-api-design-best-practices-7gf)
- [SBB: API Best Practices](https://schweizerischebundesbahnen.github.io/api-principles/restful/best-practices/)
