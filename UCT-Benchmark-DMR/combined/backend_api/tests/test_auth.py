"""
Comprehensive authentication and authorization tests for the UCT Benchmark API.

Verifies that:
- Unauthenticated requests are rejected with 401/403
- Invalid tokens are rejected
- All protected routers enforce authentication
- Admin-only endpoints return 403 for non-admin users
- Optional-auth endpoints work without a token
- Valid mock auth passes through correctly

Run with: uv run pytest backend_api/tests/test_auth.py -v
"""

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from backend_api.auth import CurrentUser, get_current_user as prod_get_current_user
from backend_api.auth import get_optional_user as prod_get_optional_user
from backend_api.database import get_db
from backend_api.main import create_test_app, reset_test_mode
from backend_api.middleware.auth import (
    get_current_user as mw_get_current_user,
    get_optional_user as mw_get_optional_user,
)
from uct_benchmark.database.connection import DatabaseManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_test_db(tmp_dir: Path) -> DatabaseManager:
    """
    Create a file-backed DuckDB test database, bypassing env config.

    Uses a temporary file instead of :memory: because DuckDB in-memory
    databases are per-connection, and Starlette's TestClient dispatches
    requests on a background thread which would get a separate (empty)
    in-memory database.
    """
    db_path = tmp_dir / "test_auth.duckdb"
    db = DatabaseManager(db_path=db_path, backend="duckdb")
    db.initialize(force=True)

    # Patch schema drift: DuckDB schema is missing app_version column
    # that exists in the Postgres schema and is used by the feedback router.
    try:
        db.execute("ALTER TABLE feedback ADD COLUMN app_version VARCHAR(50)")
    except Exception:
        pass  # Column may already exist

    return db


def _make_mock_user(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    role: str = "user",
) -> CurrentUser:
    """Create a mock CurrentUser for dependency overrides."""
    return CurrentUser(id=user_id, email=email, role=role)


def _make_mock_admin(
    user_id: str = "admin-user-456",
    email: str = "admin@example.com",
) -> CurrentUser:
    """Create a mock admin CurrentUser for dependency overrides."""
    return CurrentUser(id=user_id, email=email, role="admin")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_test_db(tmp_path: Path) -> Generator[DatabaseManager, None, None]:
    """Create a file-backed DuckDB test database with full schema."""
    test_db = _create_test_db(tmp_path)
    yield test_db
    test_db.close()


@pytest.fixture
def raw_client(auth_test_db: DatabaseManager) -> Generator[TestClient, None, None]:
    """
    Test client with database override but NO auth override.

    This client sends requests without any authentication, so protected
    endpoints should reject them.
    """
    app = create_test_app()
    app.dependency_overrides[get_db] = lambda: auth_test_db

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    app.dependency_overrides.clear()
    reset_test_mode()


@pytest.fixture
def authed_client(auth_test_db: DatabaseManager) -> Generator[TestClient, None, None]:
    """
    Test client with both database and auth overrides.

    Simulates an authenticated regular (non-admin) user so that protected
    endpoints allow the request through.
    """
    mock_user = _make_mock_user()
    app = create_test_app()

    app.dependency_overrides[get_db] = lambda: auth_test_db
    app.dependency_overrides[mw_get_current_user] = lambda: mock_user
    app.dependency_overrides[prod_get_current_user] = lambda: mock_user
    app.dependency_overrides[mw_get_optional_user] = lambda: mock_user
    app.dependency_overrides[prod_get_optional_user] = lambda: mock_user

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    app.dependency_overrides.clear()
    reset_test_mode()


@pytest.fixture
def admin_client(auth_test_db: DatabaseManager) -> Generator[TestClient, None, None]:
    """
    Test client authenticated as an admin user.

    Admin endpoints (feedback GET/PATCH) should allow these requests.
    """
    mock_admin = _make_mock_admin()
    app = create_test_app()

    app.dependency_overrides[get_db] = lambda: auth_test_db
    app.dependency_overrides[mw_get_current_user] = lambda: mock_admin
    app.dependency_overrides[prod_get_current_user] = lambda: mock_admin
    app.dependency_overrides[mw_get_optional_user] = lambda: mock_admin
    app.dependency_overrides[prod_get_optional_user] = lambda: mock_admin

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    app.dependency_overrides.clear()
    reset_test_mode()


@pytest.fixture
def anon_client(auth_test_db: DatabaseManager) -> Generator[TestClient, None, None]:
    """
    Test client with database override and optional-auth returning None.

    Simulates an anonymous user -- get_optional_user returns None,
    get_current_user is NOT overridden (so required-auth endpoints still
    reject), but optional-auth endpoints accept the request.
    """
    app = create_test_app()

    app.dependency_overrides[get_db] = lambda: auth_test_db
    app.dependency_overrides[prod_get_optional_user] = lambda: None
    app.dependency_overrides[mw_get_optional_user] = lambda: None

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    app.dependency_overrides.clear()
    reset_test_mode()


# ---------------------------------------------------------------------------
# 1. Unauthenticated access returns 401
# ---------------------------------------------------------------------------


class TestUnauthenticatedAccess:
    """Verify that requests without an Authorization header are rejected."""

    def test_datasets_list_requires_auth(self, raw_client: TestClient):
        """GET /api/v1/datasets/ must return 401 or 403 without a token."""
        response = raw_client.get("/api/v1/datasets/")
        assert response.status_code in (401, 403), (
            f"Expected 401/403 for unauthenticated datasets list, got {response.status_code}"
        )

    def test_datasets_detail_requires_auth(self, raw_client: TestClient):
        """GET /api/v1/datasets/1 must reject unauthenticated requests."""
        response = raw_client.get("/api/v1/datasets/1")
        assert response.status_code in (401, 403)

    def test_submissions_list_requires_auth(self, raw_client: TestClient):
        """GET /api/v1/submissions/ must reject unauthenticated requests."""
        response = raw_client.get("/api/v1/submissions/")
        assert response.status_code in (401, 403)

    def test_results_requires_auth(self, raw_client: TestClient):
        """GET /api/v1/results/ must reject unauthenticated requests."""
        response = raw_client.get("/api/v1/results/")
        assert response.status_code in (401, 403)

    def test_jobs_list_requires_auth(self, raw_client: TestClient):
        """GET /api/v1/jobs/ must reject unauthenticated requests."""
        response = raw_client.get("/api/v1/jobs/")
        assert response.status_code in (401, 403)

    def test_leaderboard_requires_auth(self, raw_client: TestClient):
        """GET /api/v1/leaderboard/ must reject unauthenticated requests."""
        response = raw_client.get("/api/v1/leaderboard/")
        assert response.status_code in (401, 403)

    def test_auth_verify_requires_auth(self, raw_client: TestClient):
        """POST /api/v1/auth/verify must reject unauthenticated requests."""
        response = raw_client.post("/api/v1/auth/verify")
        assert response.status_code in (401, 403)

    def test_auth_me_requires_auth(self, raw_client: TestClient):
        """GET /api/v1/auth/me must reject unauthenticated requests."""
        response = raw_client.get("/api/v1/auth/me")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 2. Invalid token returns 401/403
# ---------------------------------------------------------------------------


class TestInvalidToken:
    """Verify that malformed or random Bearer tokens are rejected."""

    def test_garbage_token_rejected(self, raw_client: TestClient):
        """A completely random string as Bearer token must not grant access."""
        response = raw_client.get(
            "/api/v1/datasets/",
            headers={"Authorization": "Bearer this-is-not-a-jwt"},
        )
        assert response.status_code != 200, (
            "Invalid token must not return 200 -- auth bypass detected"
        )
        # Accept 401, 403, or 503 (JWKS unreachable in test env)
        assert response.status_code in (401, 403, 503)

    def test_empty_bearer_rejected(self, raw_client: TestClient):
        """An empty Bearer value must be rejected."""
        response = raw_client.get(
            "/api/v1/datasets/",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code in (401, 403, 422)

    def test_no_bearer_prefix_rejected(self, raw_client: TestClient):
        """An Authorization header without the 'Bearer' prefix must be rejected."""
        response = raw_client.get(
            "/api/v1/datasets/",
            headers={"Authorization": "Token abc123"},
        )
        assert response.status_code in (401, 403)

    def test_malformed_jwt_rejected(self, raw_client: TestClient):
        """A string that looks like a JWT (three dot-separated parts) but is invalid must not grant access."""
        fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.fakesignature"
        response = raw_client.get(
            "/api/v1/datasets/",
            headers={"Authorization": f"Bearer {fake_jwt}"},
        )
        assert response.status_code != 200, (
            "Malformed JWT must not return 200 -- auth bypass detected"
        )
        assert response.status_code in (401, 403, 503)

    def test_invalid_token_on_submissions(self, raw_client: TestClient):
        """Invalid token must not grant access to submissions router."""
        response = raw_client.get(
            "/api/v1/submissions/",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code != 200
        assert response.status_code in (401, 403, 503)

    def test_invalid_token_on_jobs(self, raw_client: TestClient):
        """Invalid token must not grant access to jobs router."""
        response = raw_client.get(
            "/api/v1/jobs/",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code != 200
        assert response.status_code in (401, 403, 503)


# ---------------------------------------------------------------------------
# 3. Auth required on all protected routers
# ---------------------------------------------------------------------------


class TestProtectedRoutersCoverage:
    """
    Verify that every protected router group rejects unauthenticated requests.

    This ensures no router was accidentally registered without the auth
    dependency (a regression that happened in the past with duplicate
    route trees).
    """

    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/v1/datasets/"),
            ("GET", "/api/v1/datasets/1"),
            ("POST", "/api/v1/datasets/"),
            ("GET", "/api/v1/submissions/"),
            ("GET", "/api/v1/submissions/1"),
            ("GET", "/api/v1/results/"),
            ("GET", "/api/v1/results/1"),
            ("GET", "/api/v1/jobs/"),
            ("GET", "/api/v1/jobs/test-job-id"),
            ("GET", "/api/v1/leaderboard/"),
            ("POST", "/api/v1/auth/verify"),
            ("GET", "/api/v1/auth/me"),
            ("PATCH", "/api/v1/auth/me"),
        ],
    )
    def test_protected_endpoint_rejects_unauthenticated(
        self, raw_client: TestClient, method: str, path: str
    ):
        """Every protected endpoint must reject requests without a valid token."""
        response = raw_client.request(method, path)
        assert response.status_code in (401, 403, 405, 422), (
            f"{method} {path} returned {response.status_code}, "
            f"expected 401/403 (or 405/422 for method-specific validation)"
        )
        # 200 is never acceptable for an unauthenticated request on these routes
        assert response.status_code != 200, (
            f"{method} {path} returned 200 without authentication -- auth bypass detected"
        )


# ---------------------------------------------------------------------------
# 4. Admin-only endpoints return 403 for non-admin
# ---------------------------------------------------------------------------


class TestAdminOnlyEndpoints:
    """
    Verify that feedback list, detail, and update endpoints require admin role.

    These endpoints use get_current_user + a role check, so a regular
    authenticated user should get 403 Forbidden.
    """

    def test_feedback_list_forbidden_for_regular_user(self, authed_client: TestClient):
        """GET /api/v1/feedback must return 403 for a non-admin authenticated user."""
        response = authed_client.get("/api/v1/feedback")
        assert response.status_code == 403, (
            f"Expected 403 for non-admin on feedback list, got {response.status_code}"
        )

    def test_feedback_detail_forbidden_for_regular_user(self, authed_client: TestClient):
        """GET /api/v1/feedback/{id} must return 403 for a non-admin authenticated user."""
        response = authed_client.get("/api/v1/feedback/some-feedback-id")
        assert response.status_code == 403

    def test_feedback_update_forbidden_for_regular_user(self, authed_client: TestClient):
        """PATCH /api/v1/feedback/{id} must return 403 for a non-admin authenticated user."""
        response = authed_client.patch(
            "/api/v1/feedback/some-feedback-id",
            json={"status": "closed"},
        )
        assert response.status_code == 403

    def test_feedback_list_allowed_for_admin(self, admin_client: TestClient):
        """GET /api/v1/feedback must return 200 for an admin user."""
        response = admin_client.get("/api/v1/feedback")
        assert response.status_code == 200, (
            f"Expected 200 for admin on feedback list, got {response.status_code}: "
            f"{response.text}"
        )

    def test_feedback_detail_404_for_admin(self, admin_client: TestClient):
        """GET /api/v1/feedback/{id} returns 404 (not 403) for admin with nonexistent ID."""
        response = admin_client.get("/api/v1/feedback/nonexistent-id")
        assert response.status_code == 404, (
            f"Expected 404 for admin fetching nonexistent feedback, got {response.status_code}"
        )

    def test_feedback_update_404_for_admin(self, admin_client: TestClient):
        """PATCH /api/v1/feedback/{id} returns 404 (not 403) for admin with nonexistent ID."""
        response = admin_client.patch(
            "/api/v1/feedback/nonexistent-id",
            json={"status": "resolved"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# 5. Optional auth endpoints work without a token
# ---------------------------------------------------------------------------


class TestOptionalAuthEndpoints:
    """
    Verify that endpoints using get_optional_user work for anonymous users.

    The feedback POST endpoint accepts submissions from both authenticated
    and anonymous users.
    """

    def test_feedback_post_works_anonymously(self, anon_client: TestClient):
        """POST /api/v1/feedback must accept anonymous submissions (201)."""
        payload = {
            "description": "Something is broken on the leaderboard page.",
            "severity": "bug",
        }
        response = anon_client.post("/api/v1/feedback", json=payload)
        assert response.status_code == 201, (
            f"Expected 201 for anonymous feedback POST, got {response.status_code}: "
            f"{response.text}"
        )
        data = response.json()
        assert data["success"] is True
        assert "feedback_id" in data

    def test_feedback_post_works_with_auth(self, authed_client: TestClient):
        """POST /api/v1/feedback must also work for authenticated users."""
        payload = {
            "description": "Suggestion: add dark mode support.",
            "severity": "suggestion",
        }
        response = authed_client.post("/api/v1/feedback", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    def test_feedback_post_validates_payload(self, anon_client: TestClient):
        """POST /api/v1/feedback with invalid payload returns 422."""
        response = anon_client.post("/api/v1/feedback", json={})
        assert response.status_code == 422

    def test_feedback_post_rejects_invalid_severity(self, anon_client: TestClient):
        """POST /api/v1/feedback with invalid severity returns 422."""
        payload = {
            "description": "Test feedback.",
            "severity": "critical",  # not in the Literal["bug", "suggestion", "question"]
        }
        response = anon_client.post("/api/v1/feedback", json=payload)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# 6. Valid mock auth passes
# ---------------------------------------------------------------------------


class TestValidMockAuth:
    """
    Verify that endpoints succeed when auth is properly mocked.

    Uses the authed_client fixture which overrides get_current_user
    to return a mock user, confirming that the dependency override
    mechanism works end-to-end.
    """

    def test_datasets_accessible_with_mock_auth(self, authed_client: TestClient):
        """GET /api/v1/datasets/ returns 200 when auth is overridden with a valid user."""
        response = authed_client.get("/api/v1/datasets/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_leaderboard_accessible_with_mock_auth(self, authed_client: TestClient):
        """GET /api/v1/leaderboard/ returns 200 when auth is overridden."""
        response = authed_client.get("/api/v1/leaderboard/")
        assert response.status_code == 200

    def test_submissions_accessible_with_mock_auth(self, authed_client: TestClient):
        """GET /api/v1/submissions/ returns 200 when auth is overridden."""
        response = authed_client.get("/api/v1/submissions/")
        assert response.status_code == 200

    def test_results_accessible_with_mock_auth(self, authed_client: TestClient):
        """GET /api/v1/results/ returns 200 when auth is overridden."""
        response = authed_client.get("/api/v1/results/")
        assert response.status_code == 200

    def test_jobs_accessible_with_mock_auth(self, authed_client: TestClient):
        """GET /api/v1/jobs/ returns 200 when auth is overridden."""
        response = authed_client.get("/api/v1/jobs/")
        assert response.status_code == 200

    def test_dataset_not_found_returns_404_not_auth_error(self, authed_client: TestClient):
        """GET /api/v1/datasets/99999 returns 404 (not an auth error) when authenticated."""
        response = authed_client.get("/api/v1/datasets/99999")
        assert response.status_code == 404

    def test_submission_not_found_returns_404(self, authed_client: TestClient):
        """GET /api/v1/submissions/99999 returns 404 when authenticated."""
        response = authed_client.get("/api/v1/submissions/99999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# 7. Public endpoints remain accessible without auth
# ---------------------------------------------------------------------------


class TestPublicEndpoints:
    """
    Verify that truly public endpoints (root, health) work without any auth.
    """

    def test_root_endpoint_public(self, raw_client: TestClient):
        """GET / must be accessible without authentication."""
        response = raw_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_endpoint_public(self, raw_client: TestClient):
        """GET /health must be accessible without authentication."""
        response = raw_client.get("/health")
        # May return 200 or 503 depending on DB state, but never 401/403
        assert response.status_code in (200, 503)
        assert response.status_code not in (401, 403)


# ---------------------------------------------------------------------------
# 8. Auth user properties propagate correctly
# ---------------------------------------------------------------------------


class TestAuthUserPropagation:
    """
    Verify that the mock user identity is correctly available in endpoints
    that use it (e.g., feedback POST records reporter info).
    """

    def test_feedback_records_authenticated_user(
        self, authed_client: TestClient, auth_test_db: DatabaseManager
    ):
        """POST /api/v1/feedback with auth should record the reporter_id and email."""
        payload = {
            "description": "Testing that user identity is recorded.",
            "severity": "question",
        }
        response = authed_client.post("/api/v1/feedback", json=payload)
        assert response.status_code == 201

        feedback_id = response.json()["feedback_id"]

        # Query the database to verify reporter fields were stored
        result = auth_test_db.execute(
            "SELECT reporter_id, reporter_email FROM feedback WHERE id = ?",
            (feedback_id,),
        )
        row = result.fetchone()
        assert row is not None, "Feedback row should exist in the database"

        reporter_id, reporter_email = row
        assert reporter_id == "test-user-123"
        assert reporter_email == "test@example.com"

    def test_feedback_anonymous_has_null_reporter(
        self, anon_client: TestClient, auth_test_db: DatabaseManager
    ):
        """POST /api/v1/feedback without auth should have NULL reporter fields."""
        payload = {
            "description": "Anonymous feedback test.",
            "severity": "bug",
        }
        response = anon_client.post("/api/v1/feedback", json=payload)
        assert response.status_code == 201

        feedback_id = response.json()["feedback_id"]

        result = auth_test_db.execute(
            "SELECT reporter_id, reporter_email FROM feedback WHERE id = ?",
            (feedback_id,),
        )
        row = result.fetchone()
        assert row is not None
        reporter_id, reporter_email = row
        assert reporter_id is None
        assert reporter_email is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
