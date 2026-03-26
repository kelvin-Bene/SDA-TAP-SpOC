"""
Authentication router for UCT Benchmark API.

Provides endpoints for JWT verification and user profile management.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from backend_api.auth import CurrentUser, get_current_user
from backend_api.database import get_db
from uct_benchmark.database.connection import DatabaseManager

router = APIRouter()


# ============================================================
# Utilities
# ============================================================


def _mask_token(token: Optional[str]) -> Optional[str]:
    """Mask a token for safe display, showing only the last 4 characters."""
    if not token:
        return None
    if len(token) <= 4:
        return "****"
    return "****" + token[-4:]


# ============================================================
# Response / Request Models
# ============================================================


class UserProfile(BaseModel):
    """User profile response."""

    id: str
    email: str
    role: str
    display_name: Optional[str] = None
    organization: Optional[str] = None
    udl_token: Optional[str] = None
    esa_token: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProfileUpdate(BaseModel):
    """Request body for updating a user profile."""

    display_name: Optional[str] = Field(default=None, max_length=100)
    organization: Optional[str] = Field(default=None, max_length=200)
    udl_token: Optional[str] = Field(default=None, max_length=500)
    esa_token: Optional[str] = Field(default=None, max_length=500)


class VerifyResponse(BaseModel):
    """Response for the verify endpoint."""

    authenticated: bool
    user: UserProfile


# ============================================================
# Endpoints
# ============================================================


@router.post("/verify", response_model=VerifyResponse)
async def verify_token(
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Verify the JWT and return the authenticated user's profile.

    This endpoint validates the token (via the dependency) and returns
    the user profile from the database, creating one if it does not exist.
    """
    profile = _get_or_create_profile(db, user)

    return VerifyResponse(
        authenticated=True,
        user=UserProfile(
            id=profile["id"],
            email=profile["email"],
            role=profile["role"],
            display_name=profile.get("display_name"),
            organization=profile.get("organization"),
            udl_token=_mask_token(profile.get("udl_token")),
            esa_token=_mask_token(profile.get("esa_token")),
            created_at=profile.get("created_at"),
            updated_at=profile.get("updated_at"),
        ),
    )


@router.get("/me", response_model=UserProfile)
async def get_me(
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Return the current authenticated user's profile.

    Fetches the profile from the `profiles` table, creating a record
    if the user has authenticated for the first time.
    """
    profile = _get_or_create_profile(db, user)

    return UserProfile(
        id=profile["id"],
        email=profile["email"],
        role=profile["role"],
        display_name=profile.get("display_name"),
        organization=profile.get("organization"),
        udl_token=_mask_token(profile.get("udl_token")),
        esa_token=_mask_token(profile.get("esa_token")),
        created_at=profile.get("created_at"),
        updated_at=profile.get("updated_at"),
    )


@router.patch("/me", response_model=UserProfile)
async def update_me(
    updates: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Update the current user's profile.

    Updatable fields: `display_name`, `organization`, `udl_token`, `esa_token`.
    Tokens are stored as-is but masked in the response.
    """
    # Ensure the profile exists first
    _get_or_create_profile(db, user)

    # Build dynamic SET clause based on provided fields
    set_parts: list[str] = []
    params: list = []

    if updates.display_name is not None:
        set_parts.append("display_name = ?")
        params.append(updates.display_name)

    if updates.organization is not None:
        set_parts.append("organization = ?")
        params.append(updates.organization)

    if updates.udl_token is not None:
        set_parts.append("udl_token = ?")
        params.append(updates.udl_token)

    if updates.esa_token is not None:
        set_parts.append("esa_token = ?")
        params.append(updates.esa_token)

    if not set_parts:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_parts.append("updated_at = CURRENT_TIMESTAMP")
    set_clause = ", ".join(set_parts)
    params.append(user.id)

    db.execute(
        f"UPDATE profiles SET {set_clause} WHERE id = ?",
        tuple(params),
    )

    # Return the updated profile
    result = db.execute(
        "SELECT id, email, role, display_name, organization, udl_token, esa_token, created_at, updated_at "
        "FROM profiles WHERE id = ?",
        (user.id,),
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to read updated profile")

    row_dict = dict(zip(columns, row))
    row_dict["id"] = str(row_dict["id"])
    row_dict["udl_token"] = _mask_token(row_dict.get("udl_token"))
    row_dict["esa_token"] = _mask_token(row_dict.get("esa_token"))
    return UserProfile(**row_dict)


# ============================================================
# Helpers
# ============================================================


def _get_or_create_profile(db: DatabaseManager, user: CurrentUser) -> dict:
    """
    Fetch the user's profile from the database, creating it if necessary.

    Args:
        db: Database manager instance.
        user: The authenticated user from the JWT.

    Returns:
        A dictionary of profile columns.
    """
    result = db.execute(
        "SELECT id, email, role, display_name, organization, udl_token, esa_token, created_at, updated_at "
        "FROM profiles WHERE id = ?",
        (user.id,),
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is not None:
        profile = dict(zip(columns, row))
        # Ensure id is string (pg8000 returns UUID objects)
        profile["id"] = str(profile["id"])
        return profile

    # First login -- create a profile record
    logger.info(f"Creating profile for new user {user.id} ({user.email})")
    db.execute(
        """
        INSERT INTO profiles (id, email, role, created_at, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO NOTHING
        """,
        (user.id, user.email, user.role),
    )

    # Re-fetch after insert
    result = db.execute(
        "SELECT id, email, role, display_name, organization, udl_token, esa_token, created_at, updated_at "
        "FROM profiles WHERE id = ?",
        (user.id,),
    )
    columns = [desc[0] for desc in result.description]
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create user profile")

    profile = dict(zip(columns, row))
    profile["id"] = str(profile["id"])
    return profile
