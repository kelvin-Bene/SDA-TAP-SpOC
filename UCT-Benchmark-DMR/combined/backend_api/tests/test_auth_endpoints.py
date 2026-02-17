"""
Tests for authentication REST API endpoints.

Covers: signup, login, logout, /me profile management.
Tests both auth-disabled (anonymous) and auth-enabled (mocked) modes.

Run with: uv run pytest backend_api/tests/test_auth_endpoints.py -v
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from uct_benchmark.database.connection import DatabaseManager


@pytest.fixture(scope="module")
def _module_db():
    """Single database instance for the entire module."""
    db = DatabaseManager(in_memory=True, backend="duckdb")
    db.initialize(force=True)
    yield db
    db.close()


@pytest.fixture()
def client(_module_db):
    """Create a test client with mocked database dependency."""
    import backend_api.database as db_module
    import backend_api.jobs.workers as workers_module
    import backend_api.main as main_module
    from backend_api.database import get_db
    from backend_api.main import app

    orig_init = db_module.init_database
    orig_close = db_module.close_database
    orig_mgr = db_module._db_manager
    orig_shutdown = workers_module.shutdown_executor
    orig_main_init = main_module.init_database
    orig_main_close = main_module.close_database
    orig_main_shutdown = main_module.shutdown_executor

    noop_init = lambda **kw: _module_db
    noop_close = lambda: None
    noop_shutdown = lambda: None

    db_module.init_database = noop_init
    db_module.close_database = noop_close
    db_module._db_manager = _module_db
    main_module.init_database = noop_init
    main_module.close_database = noop_close
    main_module.shutdown_executor = noop_shutdown
    workers_module.shutdown_executor = noop_shutdown
    app.dependency_overrides[get_db] = lambda: _module_db

    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        db_module.init_database = orig_init
        db_module.close_database = orig_close
        db_module._db_manager = orig_mgr
        workers_module.shutdown_executor = orig_shutdown
        main_module.init_database = orig_main_init
        main_module.close_database = orig_main_close
        main_module.shutdown_executor = orig_main_shutdown


class TestAuthDisabled:
    """Tests with AUTH_ENABLED=false (default dev mode)."""

    def test_signup_returns_anonymous(self, client: TestClient):
        """Signup with auth disabled returns anonymous token."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "test@example.com",
                "password": "password123",
                "username": "tester",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["access_token"] == "auth-disabled-mock-token"
        assert data["token_type"] == "bearer"
        assert data["user"]["id"] == "anonymous"
        assert data["user"]["email"] == "anonymous@localhost"

    def test_login_returns_anonymous(self, client: TestClient):
        """Login with auth disabled returns anonymous token."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "auth-disabled-mock-token"
        assert data["user"]["id"] == "anonymous"

    def test_get_me_returns_anonymous(self, client: TestClient):
        """GET /me with auth disabled returns anonymous profile."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "anonymous"
        assert data["email"] == "anonymous@localhost"
        assert data["username"] == "Anonymous User"
        assert data["role"] == "admin"

    def test_update_me_returns_anonymous(self, client: TestClient):
        """PATCH /me with auth disabled returns anonymous profile unchanged."""
        response = client.patch(
            "/api/v1/auth/me",
            json={"username": "NewName"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "anonymous"
        assert data["username"] == "Anonymous User"

    def test_logout_returns_success(self, client: TestClient):
        """Logout with auth disabled returns success."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "logged out" in data["message"].lower()


class TestAuthEnabled:
    """Tests with AUTH_ENABLED=true using mocked config."""

    @pytest.fixture(autouse=True)
    def enable_auth(self):
        """Enable auth for all tests in this class."""
        mock_config = MagicMock()
        mock_config.auth_enabled = True
        mock_config.supabase_url = None
        mock_config.supabase_anon_key = None
        mock_config.supabase_service_role_key = None
        mock_config.supabase_jwt_secret = "test-jwt-secret"

        with patch("backend_api.routers.auth.get_config", return_value=mock_config):
            with patch(
                "backend_api.config.get_config",
                return_value=mock_config,
            ):
                yield mock_config

    def test_signup_creates_local_user(self, client: TestClient):
        """Signup creates a user in local store when no Supabase configured."""
        from backend_api.routers.auth import _users_db

        _users_db.clear()

        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@test.com",
                "password": "SecurePass123!",
                "username": "newuser",
                "organization": "TestOrg",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "newuser@test.com"
        assert data["user"]["username"] == "newuser"
        assert data["user"]["organization"] == "TestOrg"
        assert data["user"]["role"] == "developer"
        assert data["access_token"].startswith("local-")

    def test_signup_duplicate_email_returns_409(self, client: TestClient):
        """Signup with duplicate email returns 409 Conflict."""
        from backend_api.routers.auth import _users_db

        _users_db.clear()

        client.post(
            "/api/v1/auth/signup",
            json={"email": "dupe@test.com", "password": "Pass123!"},
        )

        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "dupe@test.com", "password": "Pass123!"},
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    def test_login_with_local_user(self, client: TestClient):
        """Login succeeds for locally created user."""
        from backend_api.routers.auth import _users_db

        _users_db.clear()

        client.post(
            "/api/v1/auth/signup",
            json={"email": "login@test.com", "password": "Pass123!"},
        )

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "login@test.com", "password": "Pass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "login@test.com"
        assert data["access_token"].startswith("local-")

    def test_login_unknown_email_returns_401(self, client: TestClient):
        """Login with unknown email returns 401."""
        from backend_api.routers.auth import _users_db

        _users_db.clear()

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "unknown@test.com", "password": "Pass123!"},
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_get_me_without_token_returns_401(self, client: TestClient):
        """GET /me without auth token returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_logout_without_token_returns_401(self, client: TestClient):
        """Logout without auth token returns 401."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401


class TestAuthValidation:
    """Input validation tests for auth endpoints."""

    def test_signup_missing_email(self, client: TestClient):
        """Signup without email returns 422."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"password": "Pass123!"},
        )
        assert response.status_code == 422

    def test_signup_missing_password(self, client: TestClient):
        """Signup without password returns 422."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 422

    def test_login_missing_fields(self, client: TestClient):
        """Login with missing fields returns 422."""
        response = client.post(
            "/api/v1/auth/login",
            json={},
        )
        assert response.status_code == 422

    def test_signup_malformed_json(self, client: TestClient):
        """Signup with malformed JSON returns error."""
        response = client.post(
            "/api/v1/auth/signup",
            content=b"not json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422

    def test_update_me_empty_body(self, client: TestClient):
        """PATCH /me with empty update body succeeds (no fields to update)."""
        response = client.patch(
            "/api/v1/auth/me",
            json={},
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
