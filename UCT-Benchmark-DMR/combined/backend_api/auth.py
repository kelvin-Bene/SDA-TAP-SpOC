"""
Authentication middleware for UCT Benchmark API.

Validates Supabase JWTs (ES256 asymmetric keys) and provides FastAPI
dependencies for protecting endpoints with authentication.

This module is the production auth layer (ES256 JWKS). The middleware/auth.py
module delegates here when SUPABASE_URL is set, and falls back to HS256
when only SUPABASE_JWT_SECRET is configured.
"""

import os
from dataclasses import dataclass
from typing import Optional

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request, status
from loguru import logger

# Cached JWKS client -- fetches public keys from Supabase's JWKS endpoint
_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> PyJWKClient:
    """
    Get or create the cached JWKS client for Supabase JWT verification.

    Uses the SUPABASE_URL env var to construct the JWKS endpoint.
    Falls back to SUPABASE_JWKS_URL if set directly.
    """
    global _jwks_client
    if _jwks_client is not None:
        return _jwks_client

    jwks_url = os.getenv("SUPABASE_JWKS_URL")
    if not jwks_url:
        supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        if not supabase_url:
            raise RuntimeError(
                "SUPABASE_URL environment variable must be set for JWT verification."
            )
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"

    _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    logger.info(f"JWKS client initialized: {jwks_url}")
    return _jwks_client


@dataclass
class CurrentUser:
    """Authenticated user extracted from a validated JWT."""

    id: str
    email: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _extract_token(request: Request) -> Optional[str]:
    """
    Extract the Bearer token from the Authorization header.

    Returns:
        The JWT string, or None if no Authorization header is present.

    Raises:
        HTTPException: If the header is present but malformed.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return parts[1]


def _decode_jwt(token: str) -> dict:
    """
    Decode and validate a Supabase JWT using the JWKS public key.

    Supports both ES256 (current) and HS256 (legacy) tokens.

    Returns:
        The decoded JWT claims dictionary.

    Raises:
        HTTPException: If the token is expired, invalid, or missing required claims.
    """
    # Build issuer URL for verification
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    issuer = f"{supabase_url}/auth/v1" if supabase_url else None

    # First try ES256 via JWKS (current Supabase default)
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        decode_opts = {
            "algorithms": ["ES256"],
            "audience": "authenticated",
        }
        if issuer:
            decode_opts["issuer"] = issuer
        payload = jwt.decode(
            token,
            signing_key.key,
            **decode_opts,
        )
        return _validate_claims(payload)
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
    except (jwt.InvalidTokenError, jwt.PyJWKClientError) as e:
        # Only fall back to HS256 if explicitly allowed (legacy support)
        hs256_secret = os.getenv("SUPABASE_JWT_SECRET")
        allow_hs256 = os.getenv("ALLOW_HS256_FALLBACK", "").lower() in ("true", "1", "yes")
        is_production = bool(os.getenv("SUPABASE_URL"))
        is_testing = os.getenv("TESTING", "").lower() in ("true", "1", "yes")
        if hs256_secret and (is_testing or (allow_hs256 and not is_production)):
            try:
                hs256_opts = {
                    "algorithms": ["HS256"],
                    "audience": "authenticated",
                }
                if issuer:
                    hs256_opts["issuer"] = issuer
                payload = jwt.decode(
                    token,
                    hs256_secret,
                    **hs256_opts,
                )
                logger.debug("JWT verified via HS256 fallback")
                return _validate_claims(payload)
            except jwt.InvalidTokenError:
                pass  # Fall through to error below

        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _validate_claims(payload: dict) -> dict:
    """Validate required JWT claims are present."""
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def _build_current_user(payload: dict) -> CurrentUser:
    """
    Build a CurrentUser from decoded JWT claims.

    Args:
        payload: The decoded JWT claims dictionary.

    Returns:
        A CurrentUser instance with id, email, and role.
    """
    user_id = payload["sub"]
    email = payload.get("email", "")

    # Only trust app_metadata for role (server-side only, not user-editable).
    # Do NOT trust top-level "role" claim or user_metadata -- those can be
    # modified by the client via supabase.auth.updateUser().
    role = "authenticated"
    app_metadata = payload.get("app_metadata", {})
    if isinstance(app_metadata, dict) and "role" in app_metadata:
        role = app_metadata["role"]

    return CurrentUser(id=user_id, email=email, role=role)


async def get_current_user(request: Request) -> CurrentUser:
    """
    FastAPI dependency that validates a Supabase JWT and returns the current user.

    Usage:
        @router.post("/protected")
        async def protected_endpoint(user: CurrentUser = Depends(get_current_user)):
            ...

    Raises:
        HTTPException(401): If the token is missing, expired, or invalid.
    """
    token = _extract_token(request)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Accept demo-token in demo mode without JWT validation
    if os.getenv("DEMO_MODE", "").lower() == "true" and token == "demo-token":
        return CurrentUser(id="demo-user", email="demo@uct-benchmark.org", role="authenticated")

    payload = _decode_jwt(token)
    return _build_current_user(payload)


async def get_optional_user(request: Request) -> Optional[CurrentUser]:
    """
    FastAPI dependency for public endpoints with optional authentication.

    Returns a CurrentUser if a valid token is present, or None if no
    Authorization header is provided.
    """
    token = _extract_token(request)
    if token is None:
        return None

    payload = _decode_jwt(token)
    return _build_current_user(payload)
