"""
JWT authentication middleware for Supabase integration.

Validates Bearer tokens from the frontend's Supabase auth session.
All protected routes should depend on `get_current_user`.

Authentication strategy:
  - When SUPABASE_URL is set (production): delegates to backend_api.auth
    which uses ES256 asymmetric keys via JWKS, with HS256 fallback.
  - When only SUPABASE_JWT_SECRET is set: uses HS256 symmetric key directly.
  - When neither is set: development mode with a stub user (no enforcement).
"""

import os
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

# Supabase JWT configuration
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")

# JWT algorithm used by Supabase (HS256 fallback)
JWT_ALGORITHM = "HS256"

# Security scheme - auto_error=False allows optional auth on some endpoints
security = HTTPBearer(auto_error=False)
security_required = HTTPBearer(auto_error=True)

# Flag: use production ES256 JWKS auth when SUPABASE_URL is available
_use_production_auth = bool(SUPABASE_URL)


class AuthUser:
    """Authenticated user context extracted from JWT."""

    def __init__(self, payload: dict[str, Any]):
        self.id: str = payload.get("sub", "")
        self.email: str = payload.get("email", "")
        self.role: str = payload.get("role", "authenticated")
        self.app_metadata: dict = payload.get("app_metadata", {})
        self.user_metadata: dict = payload.get("user_metadata", {})
        self.is_admin: bool = self.app_metadata.get("is_admin", False)

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
        logger.warning(
            "SUPABASE_JWT_SECRET not configured — auth enforcement disabled. "
            "Set this env var in production."
        )
        # Return a minimal payload when auth is not configured (development/demo mode)
        # Use admin role so all features (e.g. feedback review) are accessible
        return {
            "sub": "dev-user",
            "email": "dev@localhost",
            "role": "admin",
            "app_metadata": {"is_admin": True},
            "user_metadata": {},
        }

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


def _payload_to_auth_user(payload: dict[str, Any]) -> AuthUser:
    """
    Convert a decoded JWT payload (from either auth path) into an AuthUser.

    Handles the role mapping differences between the production auth module
    (which checks app_metadata.role) and the HS256 path (which reads
    top-level role).
    """
    # Normalise role: production module sets role from app_metadata,
    # but AuthUser also reads app_metadata in its __init__.
    # Just pass the payload through so AuthUser can pick up all fields.
    return AuthUser(payload)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_required),
) -> AuthUser:
    """
    FastAPI dependency that extracts and validates the current user from JWT.

    In production (SUPABASE_URL set): uses ES256 JWKS via backend_api.auth,
    with automatic HS256 fallback.
    In development (only SUPABASE_JWT_SECRET or nothing): uses HS256 directly.

    Usage:
        @router.get("/protected")
        async def protected_route(user: AuthUser = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    token = credentials.credentials

    if _use_production_auth:
        # Delegate to production ES256 JWKS auth (with HS256 fallback built in)
        try:
            from backend_api.auth import _decode_jwt, _build_current_user
            payload = _decode_jwt(token)
            # Convert the production CurrentUser fields into an AuthUser-compatible payload
            return _payload_to_auth_user(payload)
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
        return AuthUser(payload)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[AuthUser]:
    """
    FastAPI dependency for optional authentication.
    Returns None if no token is provided, validates if present.

    Usage for endpoints that work for both anonymous and authenticated users.
    """
    if credentials is None:
        return None

    token = credentials.credentials

    if _use_production_auth:
        try:
            from backend_api.auth import _decode_jwt
            payload = _decode_jwt(token)
            return _payload_to_auth_user(payload)
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
        return AuthUser(payload)


async def require_admin(
    user: AuthUser = Depends(get_current_user),
) -> AuthUser:
    """
    FastAPI dependency that requires admin role.

    Usage:
        @router.delete("/admin-only")
        async def admin_route(user: AuthUser = Depends(require_admin)):
            ...
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
