"""JWT verification utilities for Supabase Auth tokens."""

import os
from typing import Any, Dict, Optional

from loguru import logger

# Cache for JWKS keys so we don't fetch on every request
_jwks_cache: Optional[Dict] = None


def _get_jwks() -> Optional[Dict]:
    """Fetch JWKS from local Supabase for ES256 verification."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    try:
        import requests

        supabase_url = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
        resp = requests.get(
            f"{supabase_url}/auth/v1/.well-known/jwks.json", timeout=5
        )
        if resp.status_code == 200:
            _jwks_cache = resp.json()
            return _jwks_cache
    except Exception:
        pass
    return None


def verify_jwt(token: str, jwt_secret: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a Supabase JWT.

    Tries HS256 with the shared secret first, then falls back to ES256
    using the JWKS endpoint (required for local Supabase which signs
    with EC keys).

    Args:
        token: The raw JWT string (from Authorization: Bearer <token>).
        jwt_secret: The Supabase JWT secret.

    Returns:
        The decoded payload dict, or None if verification fails.
    """
    from jose import jwt as jose_jwt

    # Try HS256 first (hosted Supabase / legacy local)
    try:
        payload = jose_jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except Exception:
        pass

    # Try ES256 via JWKS (local Supabase with EC keys)
    try:
        jwks = _get_jwks()
        if jwks:
            payload = jose_jwt.decode(
                token,
                jwks,
                algorithms=["ES256"],
                options={"verify_aud": False},
            )
            return payload
    except Exception as exc:
        logger.debug(f"JWT verification failed (ES256): {exc}")

    logger.debug("JWT verification failed: no algorithm matched")
    return None
