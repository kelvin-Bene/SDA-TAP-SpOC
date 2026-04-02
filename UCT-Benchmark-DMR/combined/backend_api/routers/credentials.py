"""
Credentials management REST API endpoints.

Provides CRUD operations for encrypted credential storage and
connectivity testing for external data services.
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from backend_api.auth import CurrentUser, get_current_user
from backend_api.database import get_db
from backend_api.services.credential_service import (
    VALID_SERVICES,
    CredentialService,
)
from uct_benchmark.database.connection import DatabaseManager

router = APIRouter()


# ============================================================
# Pydantic Models
# ============================================================


class CredentialServiceInfo(BaseModel):
    """Public metadata about a credential service (never contains secrets)."""

    service_name: str
    label: str
    description: str
    is_configured: bool = False
    source: str = "none"
    validation_status: str = "untested"
    last_tested_at: Optional[str] = None


class CredentialSaveRequest(BaseModel):
    """Request body for saving credentials."""

    primary: str = Field(..., min_length=1, description="Primary credential value (token, key, or path)")
    secondary: Optional[str] = Field(None, description="Secondary credential (e.g. password for Space-Track)")


class CredentialSaveResponse(BaseModel):
    """Response after saving or deleting credentials."""

    service_name: str
    is_configured: bool
    message: str


class CredentialTestResponse(BaseModel):
    """Response from testing credential connectivity."""

    service_name: str
    status: str
    message: str


# ============================================================
# Endpoints
# ============================================================


@router.get(
    "/",
    response_model=list[CredentialServiceInfo],
    summary="List all credential services",
    description="Returns metadata and configuration status for all 6 registered services.",
)
async def list_credentials(
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """List all credential services and their status for the current user."""
    services = CredentialService.list_services(db, user.id)
    return services


@router.get(
    "/{service_name}",
    response_model=CredentialServiceInfo,
    summary="Get credential service info",
    description="Returns metadata for a single service. Never returns secret values.",
)
async def get_credential(
    service_name: str,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """Get metadata for a single credential service."""
    if service_name not in VALID_SERVICES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown service '{service_name}'. "
            f"Valid services: {', '.join(sorted(VALID_SERVICES))}",
        )

    services = CredentialService.list_services(db, user.id)
    for svc in services:
        if svc["service_name"] == service_name:
            return svc

    # Should not reach here, but handle defensively
    raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")


@router.put(
    "/{service_name}",
    response_model=CredentialSaveResponse,
    summary="Save credentials",
    description="Encrypts and stores credentials for a service.",
)
async def save_credential(
    service_name: str,
    body: CredentialSaveRequest,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """Save encrypted credentials for a service."""
    try:
        CredentialService.save_credential(
            db, user.id, service_name, body.primary, body.secondary
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return CredentialSaveResponse(
        service_name=service_name,
        is_configured=True,
        message=f"Credentials for '{service_name}' saved successfully.",
    )


@router.delete(
    "/{service_name}",
    response_model=CredentialSaveResponse,
    summary="Delete credentials",
    description="Removes stored credentials for a service from the database.",
)
async def delete_credential(
    service_name: str,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """Delete stored credentials for a service."""
    try:
        CredentialService.delete_credential(db, user.id, service_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return CredentialSaveResponse(
        service_name=service_name,
        is_configured=False,
        message=f"Credentials for '{service_name}' deleted.",
    )


@router.post(
    "/{service_name}/test",
    response_model=CredentialTestResponse,
    summary="Test credential connectivity",
    description="Resolves credentials and runs a connectivity test against the service API.",
)
async def test_credential(
    service_name: str,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """Resolve credentials and test connectivity for a service."""
    try:
        result = await asyncio.to_thread(
            CredentialService.test_connectivity, db, user.id, service_name
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Credential test failed for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {e}")

    return CredentialTestResponse(**result)
