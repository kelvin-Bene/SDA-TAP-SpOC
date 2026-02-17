"""Pydantic models for authentication requests and responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    username: Optional[str] = None
    organization: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    organization: Optional[str] = None


class UserProfile(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    organization: Optional[str] = None
    role: str = "developer"
    is_active: bool = True
    created_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
