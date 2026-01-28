"""
Authentication REST API endpoints.

Provides signup, login, logout, and profile management.
When AUTH_ENABLED is false the endpoints return mock / anonymous responses
so the application works without Supabase credentials.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from backend_api.auth.dependencies import require_auth
from backend_api.auth.models import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserProfile,
)
from backend_api.config import get_config

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory user store (replaced by Supabase / Postgres in production)
# ---------------------------------------------------------------------------
_users_db: Dict[str, Dict[str, Any]] = {}


def _anonymous_profile() -> UserProfile:
    """Return a synthetic profile used when auth is disabled."""
    return UserProfile(
        id="anonymous",
        email="anonymous@localhost",
        username="Anonymous User",
        organization="Local",
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def _anonymous_token_response() -> TokenResponse:
    """Return a mock token response for auth-disabled mode."""
    return TokenResponse(
        access_token="auth-disabled-mock-token",
        token_type="bearer",
        user=_anonymous_profile(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def signup(body: SignupRequest):
    """
    Create a new user account.

    When AUTH_ENABLED=true, proxies registration to Supabase Auth and stores
    the profile in the local users table. When disabled, returns an anonymous
    mock response.
    """
    config = get_config()

    if not config.auth_enabled:
        return _anonymous_token_response()

    # Check for duplicate email in local store
    for user_data in _users_db.values():
        if user_data.get("email") == body.email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

    # Try Supabase signup if configured
    if config.supabase_url and config.supabase_anon_key:
        try:
            from supabase import create_client

            sb = create_client(config.supabase_url, config.supabase_anon_key)
            result = sb.auth.sign_up({"email": body.email, "password": body.password})

            if result.user is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Supabase signup failed. Check your credentials.",
                )

            user_id = result.user.id
            access_token = result.session.access_token if result.session else ""
        except ImportError:
            logger.warning("supabase-py not installed; falling back to local signup")
            user_id = str(uuid.uuid4())
            access_token = f"local-{user_id}"
        except Exception as exc:
            logger.error(f"Supabase signup error: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Supabase signup failed: {exc}",
            )
    else:
        # No Supabase configured -- local-only signup
        user_id = str(uuid.uuid4())
        access_token = f"local-{user_id}"

    profile = UserProfile(
        id=user_id,
        email=body.email,
        username=body.username,
        organization=body.organization,
        role="developer",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    _users_db[user_id] = profile.model_dump()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=profile,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and obtain a token",
)
async def login(body: LoginRequest):
    """
    Authenticate with email + password.

    When AUTH_ENABLED=true, proxies to Supabase Auth. When disabled, returns
    an anonymous mock token.
    """
    config = get_config()

    if not config.auth_enabled:
        return _anonymous_token_response()

    # Try Supabase login if configured
    if config.supabase_url and config.supabase_anon_key:
        try:
            from supabase import create_client

            sb = create_client(config.supabase_url, config.supabase_anon_key)
            result = sb.auth.sign_in_with_password(
                {"email": body.email, "password": body.password}
            )

            if result.user is None or result.session is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password.",
                )

            user_id = result.user.id
            access_token = result.session.access_token

            # Upsert profile in local store
            if user_id not in _users_db:
                _users_db[user_id] = {
                    "id": user_id,
                    "email": body.email,
                    "username": result.user.user_metadata.get("username"),
                    "organization": result.user.user_metadata.get("organization"),
                    "role": result.user.role or "developer",
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }

            stored = _users_db[user_id]
            profile = UserProfile(**stored)

            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=profile,
            )
        except ImportError:
            logger.warning("supabase-py not installed; falling back to local login")
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Supabase login error: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Supabase login failed: {exc}",
            )

    # Fallback: look up local user store
    for uid, user_data in _users_db.items():
        if user_data.get("email") == body.email:
            profile = UserProfile(**user_data)
            return TokenResponse(
                access_token=f"local-{uid}",
                token_type="bearer",
                user=profile,
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )


@router.post(
    "/logout",
    summary="Log out the current user",
)
async def logout(user: Dict[str, Any] = Depends(require_auth)):
    """
    Log out the current session.

    When Supabase is configured, calls signOut on the server side.
    Always returns a success message so the client can clear its state.
    """
    config = get_config()

    if not config.auth_enabled:
        return {"message": "Logged out (auth disabled)."}

    # Attempt Supabase server-side sign-out (best effort)
    if config.supabase_url and config.supabase_service_role_key:
        try:
            from supabase import create_client

            sb = create_client(config.supabase_url, config.supabase_service_role_key)
            sb.auth.sign_out()
        except Exception as exc:
            logger.warning(f"Supabase sign-out error (non-fatal): {exc}")

    return {"message": "Logged out successfully."}


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
)
async def get_me(user: Dict[str, Any] = Depends(require_auth)):
    """
    Return the profile of the currently authenticated user.

    When auth is disabled, returns the anonymous profile.
    """
    config = get_config()

    if not config.auth_enabled:
        return _anonymous_profile()

    user_id = user.get("sub", "")
    stored = _users_db.get(user_id)

    if stored:
        return UserProfile(**stored)

    # Build a minimal profile from the JWT claims
    return UserProfile(
        id=user_id,
        email=user.get("email", ""),
        username=user.get("user_metadata", {}).get("username") if isinstance(user.get("user_metadata"), dict) else None,
        organization=user.get("user_metadata", {}).get("organization") if isinstance(user.get("user_metadata"), dict) else None,
        role=user.get("role", "developer"),
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@router.patch(
    "/me",
    response_model=UserProfile,
    summary="Update current user profile",
)
async def update_me(
    body: UpdateProfileRequest,
    user: Dict[str, Any] = Depends(require_auth),
):
    """
    Update editable fields on the current user's profile.

    When auth is disabled, returns the anonymous profile unchanged.
    """
    config = get_config()

    if not config.auth_enabled:
        return _anonymous_profile()

    user_id = user.get("sub", "")
    stored = _users_db.get(user_id)

    if stored is None:
        # Auto-create a profile entry from JWT claims
        stored = {
            "id": user_id,
            "email": user.get("email", ""),
            "username": None,
            "organization": None,
            "role": user.get("role", "developer"),
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _users_db[user_id] = stored

    # Apply updates (only non-None fields)
    update_data = body.model_dump(exclude_none=True)
    stored.update(update_data)

    return UserProfile(**stored)
