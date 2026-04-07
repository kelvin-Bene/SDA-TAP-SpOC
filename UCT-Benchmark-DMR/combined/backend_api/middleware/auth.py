"""
JWT authentication middleware for Supabase integration.

Validates Bearer tokens from the frontend's Supabase auth session.
All protected routes should depend on `get_current_user`.

Authentication strategy:
  - When SUPABASE_URL is set (production): delegates to backend_api.auth
    which uses ES256 asymmetric keys via JWKS, with HS256 fallback.
  - When only SUPABASE_JWT_SECRET is set: uses HS256 symmetric key directly.
  - When neither is set: development mode with a stub user (no enforcement).

TODO: Consolidate with backend_api/auth.py into a single auth module.
Both paths produce identical CurrentUser results; keeping separate for now
because consolidation is high-risk for the auth-critical path.
"""

import os
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from backend_api.auth import CurrentUser

# Supabase JWT configuration
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")

# JWT algorithm used by Supabase (HS256 fallback)
JWT_ALGORITHM = "HS256"

# Security scheme - auto_error=False allows optional auth on some endpoints
security = HTTPBearer(auto_error=False)
security_required = HTTPBearer(auto_error=True)



class AuthUser:
    """Authenticated user context extracted from JWT.

    .. deprecated::
        Use ``backend_api.auth.CurrentUser`` instead. This class is retained
        only for backward compatibility and will be removed in a future release.
    """

    def __init__(self, payload: dict[str, Any]):
        self.id: str = payload.get("sub", "")
        self.email: str = payload.get("email", "")
        self.app_metadata: dict = payload.get("app_metadata", {})
        self.user_metadata: dict = payload.get("user_metadata", {})
        _am = self.app_metadata
        self.role: str = _am.get("role", "user") if isinstance(_am, dict) and "role" in _am else payload.get("role", "authenticated")
        self.is_admin: bool = self.role == "admin"

    def __repr__(self) -> str:
        return f"AuthUser(id={self.id}, email={self.email}, role={self.role})"


def _decode_token_hs256(token: str) -> dict[str, Any]:
    """
    Decode and validate a Supabase JWT token using HS256 (symmetric key).

    This is the fallback path for environments where only SUPABASE_JWT_SECRET
    is configured (no JWKS endpoint available).

    Args:
        token: The JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    if not SUPABASE_JWT_SECRET:
        # DEMO_MODE: return a read-only demo user without any auth
        if os.getenv("DEMO_MODE", "").lower() == "true":
            logger.info("DEMO_MODE active — returning demo user (read-only)")
            return {
                "sub": "demo-user",
                "email": "demo@uct-benchmark.example",
                "role": "authenticated",
                "app_metadata": {},
                "user_metadata": {"display_name": "Demo User"},
            }
        # DEV BYPASS — only triggers when ALL of these hold:
        #   1. SUPABASE_JWT_SECRET is empty (no real secret configured)
        #   2. ENVIRONMENT=development (explicit opt-in)
        #   3. SUPABASE_URL is NOT set (blocks bypass in production)
        #   4. DATABASE_BACKEND is NOT postgres/supabase (blocks bypass with prod DB)
        # Audit-verified 2026-04-05.
        if os.getenv("ENVIRONMENT", "").lower() == "development":
            # Safety: refuse dev bypass if a real SUPABASE_URL is configured
            if SUPABASE_URL:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="ENVIRONMENT=development is not allowed when SUPABASE_URL is set. "
                           "Configure SUPABASE_JWT_SECRET or remove ENVIRONMENT=development.",
                )
            # Safety: refuse dev bypass if using production database backend
            if os.getenv("DATABASE_BACKEND", "").lower() in ("postgres", "supabase"):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Dev auth bypass not available with PostgreSQL backend. "
                           "Set SUPABASE_JWT_SECRET for authentication.",
                )
            logger.warning("Auth disabled — ENVIRONMENT=development. Never use in production.")
            return {
                "sub": "dev-user",
                "email": "dev@localhost",
                "role": "authenticated",
                "app_metadata": {},
                "user_metadata": {},
            }
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not configured. Set SUPABASE_URL or SUPABASE_JWT_SECRET.",
        )

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience="authenticated",
            options={"verify_aud": True},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.debug(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _payload_to_current_user(payload: dict[str, Any]) -> CurrentUser:
    """
    Convert a decoded JWT payload (from either auth path) into a CurrentUser.

    Handles the role mapping differences between the production auth module
    (which checks app_metadata.role) and the HS256 path (which reads
    top-level role).
    """
    user_id = payload.get("sub", "")
    email = payload.get("email", "")
    app_metadata = payload.get("app_metadata", {})
    role = (
        app_metadata.get("role", "user")
        if isinstance(app_metadata, dict) and "role" in app_metadata
        else payload.get("role", "authenticated")
    )
    return CurrentUser(id=user_id, email=email, role=role)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """
    FastAPI dependency that extracts and validates the current user from JWT.

    In production (SUPABASE_URL set): uses ES256 JWKS via backend_api.auth,
    with automatic HS256 fallback.
    In development (only SUPABASE_JWT_SECRET or nothing): uses HS256 directly.

    DEMO_MODE short-circuit: when DEMO_MODE=true and no Authorization header
    is present, returns a synthetic demo user without requiring any token.
    This is the path the DGX Spark local edition uses (no Supabase session
    exists there). Cloud builds never set DEMO_MODE so the behavior is
    unchanged for production.

    Usage:
        @router.get("/protected")
        async def protected_route(user: CurrentUser = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    # DEMO_MODE: no token required — return a synthetic demo user.
    if credentials is None:
        if os.getenv("DEMO_MODE", "").lower() == "true":
            logger.debug("DEMO_MODE active with no Authorization header — returning demo user")
            return CurrentUser(id="demo-user", email="demo@uct-benchmark.example", role="authenticated")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    if bool(os.getenv("SUPABASE_URL", "")):
        # Delegate to production ES256 JWKS auth (with HS256 fallback built in)
        try:
            from backend_api.auth import _decode_jwt, _build_current_user
            payload = _decode_jwt(token)
            return _payload_to_current_user(payload)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Production auth failed, cannot fall back: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        # HS256-only path (development or SUPABASE_JWT_SECRET-only environments)
        payload = _decode_token_hs256(token)
        return _payload_to_current_user(payload)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[CurrentUser]:
    """
    FastAPI dependency for optional authentication.
    Returns None if no token is provided, validates if present.

    Usage for endpoints that work for both anonymous and authenticated users.
    """
    if credentials is None:
        return None

    token = credentials.credentials

    if bool(os.getenv("SUPABASE_URL", "")):
        try:
            from backend_api.auth import _decode_jwt
            payload = _decode_jwt(token)
            return _payload_to_current_user(payload)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Production auth failed for optional user: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        payload = _decode_token_hs256(token)
        return _payload_to_current_user(payload)


async def require_admin(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    FastAPI dependency that requires admin role.

    Usage:
        @router.delete("/admin-only")
        async def admin_route(user: CurrentUser = Depends(require_admin)):
            ...
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
