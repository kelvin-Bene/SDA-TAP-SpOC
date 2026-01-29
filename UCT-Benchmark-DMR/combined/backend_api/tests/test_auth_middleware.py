"""
Tests for the authentication middleware, dependencies, and role guards.

Covers both AUTH_ENABLED=true and AUTH_ENABLED=false code paths.
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from jose import jwt

from backend_api.auth.middleware import verify_jwt
from backend_api.config import reset_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_JWT_SECRET = "test-jwt-secret-for-unit-tests-only"


def _make_token(payload: dict, secret: str = TEST_JWT_SECRET) -> str:
    """Create a signed HS256 JWT with the given payload."""
    defaults = {
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "sub": "user-123",
        "role": "developer",
    }
    defaults.update(payload)
    return jwt.encode(defaults, secret, algorithm="HS256")


def _make_request(token: str = None) -> MagicMock:
    """Create a mock FastAPI Request with an Authorization header."""
    request = MagicMock()
    if token:
        request.headers = {"authorization": f"Bearer {token}"}
    else:
        request.headers = {}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.url = MagicMock()
    request.url.path = "/test"
    request.method = "GET"
    return request


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_config():
    """Reset the config singleton before and after each test."""
    reset_config()
    yield
    reset_config()


# ---------------------------------------------------------------------------
# verify_jwt tests
# ---------------------------------------------------------------------------


class TestVerifyJWT:
    """Tests for backend_api.auth.middleware.verify_jwt."""

    def test_verify_jwt_valid_token_returns_payload(self):
        """A correctly signed, non-expired token should return its decoded payload."""
        token = _make_token({"sub": "user-abc", "role": "admin", "email": "a@b.com"})
        payload = verify_jwt(token, TEST_JWT_SECRET)
        assert payload is not None
        assert payload["sub"] == "user-abc"
        assert payload["role"] == "admin"
        assert payload["email"] == "a@b.com"

    def test_verify_jwt_invalid_token_returns_none(self):
        """An invalid token should return None."""
        result = verify_jwt("not-a-valid-jwt", TEST_JWT_SECRET)
        assert result is None

    def test_verify_jwt_expired_token_returns_none(self):
        """An expired token should return None."""
        token = _make_token(
            {"exp": datetime.now(timezone.utc) - timedelta(hours=1)}
        )
        result = verify_jwt(token, TEST_JWT_SECRET)
        assert result is None

    def test_verify_jwt_wrong_secret_returns_none(self):
        """A token signed with a different secret should return None."""
        token = _make_token({}, secret="wrong-secret")
        result = verify_jwt(token, TEST_JWT_SECRET)
        assert result is None

    def test_verify_jwt_empty_token_returns_none(self):
        """An empty token should return None."""
        result = verify_jwt("", TEST_JWT_SECRET)
        assert result is None


# ---------------------------------------------------------------------------
# require_auth tests
# ---------------------------------------------------------------------------


class TestRequireAuth:
    """Tests for backend_api.auth.dependencies.require_auth."""

    @pytest.mark.asyncio
    async def test_require_auth_disabled_returns_anonymous(self):
        """When auth is disabled, require_auth returns the anonymous admin dict."""
        from backend_api.auth.dependencies import require_auth

        with patch.dict(os.environ, {"AUTH_ENABLED": "false"}, clear=False):
            reset_config()
            request = _make_request()
            result = await require_auth(request)
            assert result["sub"] == "anonymous"
            assert result["role"] == "admin"

    @pytest.mark.asyncio
    async def test_require_auth_enabled_no_token_raises_401(self):
        """When auth is enabled and no token is provided, should raise 401."""
        from fastapi import HTTPException

        from backend_api.auth.dependencies import require_auth

        with patch.dict(
            os.environ,
            {"AUTH_ENABLED": "true", "SUPABASE_JWT_SECRET": TEST_JWT_SECRET},
            clear=False,
        ):
            reset_config()
            request = _make_request(token=None)
            with pytest.raises(HTTPException) as exc_info:
                await require_auth(request)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_require_auth_enabled_valid_token_returns_payload(self):
        """When auth is enabled and token is valid, should return the payload."""
        from backend_api.auth.dependencies import require_auth

        token = _make_token({"sub": "user-xyz", "role": "developer"})
        with patch.dict(
            os.environ,
            {"AUTH_ENABLED": "true", "SUPABASE_JWT_SECRET": TEST_JWT_SECRET},
            clear=False,
        ):
            reset_config()
            request = _make_request(token=token)
            result = await require_auth(request)
            assert result["sub"] == "user-xyz"
            assert result["role"] == "developer"

    @pytest.mark.asyncio
    async def test_require_auth_enabled_invalid_token_raises_401(self):
        """When auth is enabled and token is invalid, should raise 401."""
        from fastapi import HTTPException

        from backend_api.auth.dependencies import require_auth

        with patch.dict(
            os.environ,
            {"AUTH_ENABLED": "true", "SUPABASE_JWT_SECRET": TEST_JWT_SECRET},
            clear=False,
        ):
            reset_config()
            request = _make_request(token="bad-token")
            with pytest.raises(HTTPException) as exc_info:
                await require_auth(request)
            assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# require_admin tests
# ---------------------------------------------------------------------------


class TestRequireAdmin:
    """Tests for backend_api.auth.dependencies.require_admin."""

    @pytest.mark.asyncio
    async def test_require_admin_non_admin_raises_403(self):
        """A user without the admin role should be rejected with 403."""
        from fastapi import HTTPException

        from backend_api.auth.dependencies import require_admin

        token = _make_token({"sub": "user-1", "role": "developer"})
        with patch.dict(
            os.environ,
            {"AUTH_ENABLED": "true", "SUPABASE_JWT_SECRET": TEST_JWT_SECRET},
            clear=False,
        ):
            reset_config()
            request = _make_request(token=token)
            with pytest.raises(HTTPException) as exc_info:
                await require_admin(request)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_admin_admin_passes(self):
        """A user with role=admin should pass through."""
        from backend_api.auth.dependencies import require_admin

        token = _make_token({"sub": "user-1", "role": "admin"})
        with patch.dict(
            os.environ,
            {"AUTH_ENABLED": "true", "SUPABASE_JWT_SECRET": TEST_JWT_SECRET},
            clear=False,
        ):
            reset_config()
            request = _make_request(token=token)
            result = await require_admin(request)
            assert result["sub"] == "user-1"
            assert result["role"] == "admin"

    @pytest.mark.asyncio
    async def test_require_admin_auth_disabled_returns_anonymous_admin(self):
        """When auth is disabled, the anonymous user has admin role and passes."""
        from backend_api.auth.dependencies import require_admin

        with patch.dict(os.environ, {"AUTH_ENABLED": "false"}, clear=False):
            reset_config()
            request = _make_request()
            result = await require_admin(request)
            assert result["sub"] == "anonymous"
            assert result["role"] == "admin"


# ---------------------------------------------------------------------------
# get_current_user tests
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    """Tests for backend_api.auth.dependencies.get_current_user."""

    @pytest.mark.asyncio
    async def test_get_current_user_auth_disabled_returns_none(self):
        """When auth is disabled, get_current_user returns None."""
        from backend_api.auth.dependencies import get_current_user

        with patch.dict(os.environ, {"AUTH_ENABLED": "false"}, clear=False):
            reset_config()
            request = _make_request()
            result = await get_current_user(request)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token_returns_payload(self):
        """When auth is enabled and token is valid, returns the payload."""
        from backend_api.auth.dependencies import get_current_user

        token = _make_token({"sub": "user-abc"})
        with patch.dict(
            os.environ,
            {"AUTH_ENABLED": "true", "SUPABASE_JWT_SECRET": TEST_JWT_SECRET},
            clear=False,
        ):
            reset_config()
            request = _make_request(token=token)
            result = await get_current_user(request)
            assert result is not None
            assert result["sub"] == "user-abc"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token_returns_none(self):
        """When auth is enabled and token is invalid, returns None."""
        from backend_api.auth.dependencies import get_current_user

        with patch.dict(
            os.environ,
            {"AUTH_ENABLED": "true", "SUPABASE_JWT_SECRET": TEST_JWT_SECRET},
            clear=False,
        ):
            reset_config()
            request = _make_request(token="bad-token")
            result = await get_current_user(request)
            assert result is None
