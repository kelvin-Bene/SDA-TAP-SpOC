"""FastAPI dependency functions for authentication."""

import logging
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status

logger = logging.getLogger(__name__)


def _extract_token(request: Request) -> Optional[str]:
    """Extract bearer token from Authorization header."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Return the authenticated user's JWT payload, or None.

    When AUTH_ENABLED is false, always returns None (no auth required).
    When AUTH_ENABLED is true, decodes the JWT but does NOT raise on failure.
    Use ``require_auth`` for endpoints that must reject unauthenticated requests.
    """
    try:
        from backend_api.config import get_config

        config = get_config()
        if not config.auth_enabled:
            return None

        token = _extract_token(request)
        if not token or not config.supabase_jwt_secret:
            return None

        from backend_api.auth.middleware import verify_jwt

        return verify_jwt(token, config.supabase_jwt_secret)
    except Exception:
        return None


async def require_auth(request: Request) -> Dict[str, Any]:
    """Require a valid authenticated user.

    When AUTH_ENABLED is false, returns a synthetic anonymous admin payload
    so endpoints work without tokens during local development.

    When AUTH_ENABLED is true, raises 401 if the token is missing or invalid.
    """
    try:
        from backend_api.config import get_config

        config = get_config()
        if not config.auth_enabled:
            logger.warning("Auth disabled - granting anonymous admin access")
            return {"sub": "anonymous", "role": "admin", "email": "anonymous@localhost"}
    except Exception as e:
        logger.error(f"Config load failed during auth check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error.",
        )

    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        from backend_api.config import get_config

        config = get_config()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error.",
        )

    if not config.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret not configured.",
        )

    from backend_api.auth.middleware import verify_jwt

    payload = verify_jwt(token, config.supabase_jwt_secret)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def require_admin(request: Request) -> Dict[str, Any]:
    """Require an authenticated user with admin role."""
    user = await require_auth(request)
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user
