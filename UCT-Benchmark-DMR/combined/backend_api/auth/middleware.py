"""JWT verification utilities for Supabase Auth tokens."""

from typing import Any, Dict, Optional

from loguru import logger


def verify_jwt(token: str, jwt_secret: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a Supabase JWT.

    Args:
        token: The raw JWT string (from Authorization: Bearer <token>).
        jwt_secret: The Supabase JWT secret (HS256).

    Returns:
        The decoded payload dict, or None if verification fails.
    """
    try:
        from jose import jwt as jose_jwt

        payload = jose_jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except Exception as exc:
        logger.debug(f"JWT verification failed: {exc}")
        return None
