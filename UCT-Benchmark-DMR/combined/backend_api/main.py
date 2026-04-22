"""
UCT Benchmark API - FastAPI backend.

This module provides REST endpoints for:
- Dataset management (list, create, retrieve)
- Submission handling (upload, process)
- Result retrieval
- Leaderboard data
- Job status tracking

Note: Auto-links observations when retrieving dataset observations.
"""

import glob
import json
import os
import shutil
import tempfile
import time
from contextlib import asynccontextmanager, contextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

# Configurable log level via LOG_LEVEL env var (default: INFO)
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.remove()
logger.add(sys.stderr, level=_log_level)

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

_SENSITIVE_FIELDS = {"password", "token", "secret", "api_key", "screenshot_base64"}

from .database import close_database, init_database
from .jobs import init_job_manager
from .jobs.workers import shutdown_executor
from .middleware.auth import get_current_user
from .middleware.logging import RequestLoggingMiddleware, get_request_id
from .middleware.rate_limit import limiter
from .routers import auth as auth_router
from .routers import credentials, datasets, events, feedback, jobs, leaderboard, results, submissions

# Module-level flag to skip lifespan initialization during testing
# Set to True when using create_test_app() to prevent double database initialization
_skip_lifespan_init = False


def get_cors_origins() -> tuple[list[str], bool]:
    """
    Get CORS origins from environment or use defaults for development.

    Environment Variables:
        CORS_ORIGINS: Comma-separated list of allowed origins (e.g., "https://example.com,https://app.example.com")

    Returns:
        Tuple of (origin list, is_explicit) where is_explicit indicates
        that CORS_ORIGINS was explicitly configured (production).
    """
    _dev_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
    ]

    env_origins = os.getenv("CORS_ORIGINS")
    if env_origins:
        origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
        if "*" in origins:
            logger.error(
                "CORS_ORIGINS contains '*' which is incompatible with "
                "allow_credentials=True. Falling back to defaults."
            )
            return _dev_origins, False
        return origins, True

    # Default development origins
    return _dev_origins, False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown tasks:
    - Initialize database connection
    - Initialize job manager
    - Clean up on shutdown

    Note: When _skip_lifespan_init is True (set by create_test_app),
    database initialization is skipped to allow test fixtures to control the database.
    """
    global _skip_lifespan_init

    if _skip_lifespan_init:
        # Skip initialization - test fixtures handle database setup
        logger.info("Skipping lifespan init (test mode)")
        yield
        logger.info("Skipping lifespan cleanup (test mode)")
        return

    # Startup
    logger.info("Starting UCT Benchmark API...")

    # Clean up stale temp directories from previous crashed report generations
    try:
        temp_dir = tempfile.gettempdir()
        stale_cutoff = time.time() - 3600  # 1 hour
        cleaned = 0
        for d in glob.glob(os.path.join(temp_dir, "tmp*")):
            if os.path.isdir(d) and os.path.getmtime(d) < stale_cutoff:
                shutil.rmtree(d, ignore_errors=True)
                cleaned += 1
        if cleaned:
            logger.info(f"Cleaned {cleaned} stale temp directories")
    except Exception as e:
        logger.debug(f"Temp cleanup skipped: {e}")

    # Initialize Sentry error tracking (if configured)
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=sentry_dsn,
                traces_sample_rate=0.1,
                environment="production" if os.getenv("CORS_ORIGINS") else "development",
            )
            logger.info("Sentry error tracking initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Sentry: {e}")
    else:
        logger.debug("SENTRY_DSN not set — error tracking disabled")

    # Initialize database
    db = init_database()
    if db.backend == "duckdb":
        logger.info(f"Database initialized (DuckDB): {db.db_path}")
    else:
        logger.info("Database initialized (PostgreSQL): connection pool ready")
        # Verify connection works and log diagnostics
        try:
            result = db.execute("SELECT 1").fetchone()
            logger.info(f"PostgreSQL connection verified: SELECT 1 = {result}")
            tables = db.adapter.get_tables()
            logger.info(f"Database tables found: {tables}")
        except Exception as e:
            logger.error(f"PostgreSQL connection test FAILED: {e}")

    # Verify critical modules are importable
    try:
        import uct_benchmark.data.dataManipulation  # noqa: F401
        logger.info("Module uct_benchmark.data loaded successfully")
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import uct_benchmark.data: {e}")

    # Initialize job manager with DB persistence for crash recovery
    job_manager = init_job_manager(db=db)
    logger.info("Job manager initialized (with DB persistence)")

    # Warm Orekit JVM eagerly so /reference-orbits and /predictions don't
    # race to lazy-init in the request path. In prod we observed the first
    # `orekit.initVM()` call failing silently when triggered from a uvicorn
    # request thread (Propagation failed for sat NNN: "Attempt to create
    # Java package 'java' without jvm"), which left the class loader
    # poisoned for the rest of the process and made every subsequent
    # /reference-orbits response either empty (single-sat) or 502
    # (multi-sat). Eval workers were unaffected because they ran inside
    # ThreadPoolExecutor threads that paid the init cost themselves.
    # Calling warm_jvm here forces the one-time init to happen during
    # container boot, before the first HTTP request.
    try:
        from backend_api.services.orbit_propagation import warm_jvm
        from backend_api.services import orbit_propagation as _op
        warm_jvm()
        # warm_jvm() swallows exceptions internally (logger.exception) so it
        # never raises; we have to check the flag to know whether it actually
        # succeeded. Without this, the "warmed at startup" info log fires
        # even when JVM init silently failed — which is what happened before
        # the propagator.py import-order fix.
        if _op._JVM_WARMED:
            logger.info("Orekit JVM warmed at startup")
        else:
            logger.error(
                "Orekit JVM warm-up at startup reported failure — globe "
                "endpoints (/reference-orbits, /predictions) will fail or "
                "return empty. See the logger.exception traceback above."
            )
    except Exception as e:
        # Defensive: warm_jvm should never raise, but if something goes
        # wrong at import time we still want the app to serve non-globe
        # endpoints rather than failing to boot.
        logger.error(f"Orekit JVM warm-up import failed at startup: {e}")

    yield

    # Shutdown
    logger.info("Shutting down UCT Benchmark API...")

    # Shutdown worker threads
    shutdown_executor()

    # Close database
    close_database()
    logger.info("Cleanup complete")


_is_production = bool(os.getenv("CORS_ORIGINS"))

app = FastAPI(
    title="UCT Benchmark API",
    version="2.0.0",
    description="Backend API for the UCT Benchmark platform",
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# Rate limiting (slowapi) — attach limiter to app state and register error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses (S6).

    IMPORTANT: This middleware must NOT re-raise exceptions. When an exception
    escapes a BaseHTTPMiddleware, the outer CORSMiddleware never gets to inject
    CORS headers, causing browsers to report CORS errors instead of the real
    error. We catch all exceptions and return a JSON error response.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response: Response = await call_next(request)
        except Exception:
            # Convert unhandled exceptions to a proper response so CORS
            # headers can still be injected by the outer CORSMiddleware.
            # The RequestLoggingMiddleware (inner) should already catch most
            # exceptions, but this is a safety net.
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # X-XSS-Protection intentionally omitted — it is deprecated and can
        # introduce vulnerabilities.  CSP (configured in nginx) is the modern
        # replacement.
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # HSTS only in production (when CORS_ORIGINS is set to non-localhost)
        if os.getenv("CORS_ORIGINS"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        # Prevent browser HTTP caching of API and /health responses. Without this,
        # browsers apply default HTTP caching rules — which treat 410 Gone (and
        # other 4xx "permanent" status codes) as cacheable-forever. That's how
        # a single transient backend error can "stick" to a browser session and
        # keep showing stale error UI even after the backend is fixed. We saw
        # this on 2026-04-22: the Results page's Orbits tab kept rendering
        # "UCTP file has been removed from storage" for a specific submission
        # long after the /predictions endpoint was fixed to return 200 when
        # include=reference is passed, because the browser's HTTP cache was
        # serving the pre-fix 410 response without a network round-trip.
        path = request.url.path
        if path.startswith("/api/") or path == "/health" or path.startswith("/health/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
        return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log details server-side but return sanitized error to client (S7)."""
    body = await request.body()
    logger.error(f"Validation error for {request.method} {request.url}")
    # Sanitize request body: redact sensitive fields, fallback to byte length
    try:
        body_json = json.loads(body)
        if isinstance(body_json, dict):
            for key in body_json:
                if any(sf in key.lower() for sf in _SENSITIVE_FIELDS):
                    body_json[key] = "***REDACTED***"
        logger.error(f"Request body: {json.dumps(body_json)}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.error(f"Request body: <{len(body)} bytes, non-JSON>")
    logger.error(f"Validation errors: {json.dumps(exc.errors(), indent=2, default=str)}")

    # Sanitize: only return field names and error types, not raw input values
    sanitized = []
    for err in exc.errors():
        sanitized.append({
            "loc": err.get("loc"),
            "msg": err.get("msg"),
            "type": err.get("type"),
        })
    request_id = get_request_id()
    response = JSONResponse(
        status_code=422,
        content={"detail": sanitized},
    )
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


# ──────────────────────────────────────────────────────────────────────
# Middleware registration order
# ──────────────────────────────────────────────────────────────────────
# Starlette builds the middleware stack as:
#   [ServerErrorMiddleware] + user_middleware + [ExceptionMiddleware]
# then iterates reversed() to wrap the app. This means the FIRST
# add_middleware() call becomes the OUTERMOST user middleware.
#
# CORS must be outermost so it can inject Access-Control-Allow-Origin
# headers into ALL responses — including error responses from inner
# middleware and exception handlers. If CORS is inner, exceptions that
# propagate through BaseHTTPMiddleware bypass CORSMiddleware.send()
# and the browser sees a missing CORS header (reporting a CORS error
# instead of the real error like 401 or 500).
#
# Execution order (outermost to innermost):
#   ServerErrorMiddleware -> CORSMiddleware -> SecurityHeaders ->
#   RequestLogging -> ExceptionMiddleware -> Router
# ──────────────────────────────────────────────────────────────────────

# CORS — registered FIRST so it is the outermost user middleware (S11)
cors_origins, _cors_explicit = get_cors_origins()
if not _cors_explicit:
    logger.warning(
        "CORS_ORIGINS not set — using localhost defaults with credentials disabled. "
        "The frontend WILL NOT be able to communicate with this backend in production. "
        "Set CORS_ORIGINS=<your-frontend-url> in Railway env vars."
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=_cors_explicit,  # Only allow credentials when origins are explicitly configured
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

# Security headers middleware (S6) — inner to CORS so CORS headers are always present
app.add_middleware(SecurityHeadersMiddleware)

# Request logging with correlation IDs — innermost user middleware
app.add_middleware(RequestLoggingMiddleware)

# 3-tier auth: public routers have no global auth dep; authenticated routers require JWT (S1)
_auth_deps = [Depends(get_current_user)]

# Data routers — require valid Supabase JWT (private data, no unauthenticated access)
app.include_router(
    datasets.router, prefix="/api/v1/datasets", tags=["Datasets"],
    dependencies=_auth_deps,
)
app.include_router(
    leaderboard.router, prefix="/api/v1/leaderboard", tags=["Leaderboard"],
    dependencies=_auth_deps,
)

# Authenticated routers — require valid Supabase JWT for all endpoints
app.include_router(
    submissions.router, prefix="/api/v1/submissions", tags=["Submissions"],
    dependencies=_auth_deps,
)
app.include_router(
    results.router, prefix="/api/v1/results", tags=["Results"],
    dependencies=_auth_deps,
)
app.include_router(
    jobs.router, prefix="/api/v1/jobs", tags=["Jobs"],
    dependencies=_auth_deps,
)
app.include_router(
    credentials.router, prefix="/api/v1/credentials", tags=["Credentials"],
    dependencies=_auth_deps,
)
app.include_router(
    events.router, prefix="/api/v1/events", tags=["Events"],
    dependencies=_auth_deps,
)

# Auth router (verify, profile management) — uses its own auth dependency
# from backend_api.auth (ES256 JWKS in production)
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Auth"])

# Feedback router — POST is public (optional auth), GET/PATCH are admin-only
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])


@app.get("/")
async def root():
    """API root - health check."""
    return {"status": "ok", "message": "UCT Benchmark API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint with component status."""
    from .database import get_db
    import shutil

    components = {}

    # Database
    try:
        db = get_db()
        db.execute("SELECT 1").fetchone()
        components["database"] = "connected"
    except Exception as e:
        logger.warning(f"Health check database error: {e}")
        components["database"] = "error"

    # Disk space
    try:
        usage = shutil.disk_usage("/")
        free_mb = usage.free / (1024 * 1024)
        components["disk_space"] = "ok" if free_mb > 100 else "low"
    except Exception:
        components["disk_space"] = "unknown"

    # Orekit (Java) availability for state/residual metrics. The JVM starts
    # lazily on first propagation via `orbit_propagation.warm_jvm()` — we
    # don't start it here because that would cost 5-15s on every /health
    # probe. Import success is sufficient to know the pipeline *can* run.
    try:
        import orekit_jpype  # noqa: F401
        components["orekit"] = "available"
    except ImportError:
        components["orekit"] = "unavailable"

    is_healthy = components.get("database") == "connected"
    return JSONResponse(
        status_code=200 if is_healthy else 503,
        content={"status": "healthy" if is_healthy else "degraded", "components": components},
    )


def create_test_app() -> FastAPI:
    """
    Create a FastAPI app instance configured for testing.

    This function sets a module-level flag that causes the lifespan
    context manager to skip database initialization, allowing test
    fixtures to inject their own database via dependency overrides.

    Usage in tests:
        from backend_api.main import create_test_app
        from backend_api.database import get_db

        app = create_test_app()

        def override_get_db():
            return test_db

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as client:
            # Run tests
            pass

    Returns:
        The global FastAPI app instance with test mode enabled
    """
    global _skip_lifespan_init
    _skip_lifespan_init = True
    return app


def reset_test_mode():
    """
    Reset test mode flag after tests complete.

    Call this in test teardown to restore normal operation.
    """
    global _skip_lifespan_init
    _skip_lifespan_init = False


@contextmanager
def test_mode():
    """
    Context manager for test mode that auto-resets on exit.

    Usage:
        with test_mode() as test_app:
            test_app.dependency_overrides[get_db] = override_get_db
            with TestClient(test_app) as client:
                # Run tests
                pass
        # _skip_lifespan_init is automatically reset
    """
    global _skip_lifespan_init
    _skip_lifespan_init = True
    try:
        yield app
    finally:
        _skip_lifespan_init = False
