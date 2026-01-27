"""
Credentials management REST API endpoints.

Provides CRUD operations for encrypted credential storage,
credential testing via connector integration, and encryption key generation.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from backend_api.database import get_credential_service

router = APIRouter()


# ============================================================
# Pydantic Models
# ============================================================


class CredentialServiceInfo(BaseModel):
    """Public metadata about a credential service (never contains secrets)."""

    service_name: str
    credential_type: str
    label: Optional[str] = None
    description: Optional[str] = None
    is_configured: bool = False
    last_validated: Optional[str] = None
    validation_status: str = "untested"
    source: str = "none"
    has_env_fallback: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CredentialSaveRequest(BaseModel):
    """Request body for saving credentials."""

    primary: str = Field(..., min_length=1, description="Primary credential value")
    secondary: Optional[str] = Field(None, description="Secondary credential (e.g. password)")


class CredentialSaveResponse(BaseModel):
    """Response after saving credentials."""

    service_name: str
    is_configured: bool
    message: str


class CredentialTestResponse(BaseModel):
    """Response from testing a credential."""

    service_name: str
    status: str
    message: str
    response_time_ms: Optional[float] = None


class GenerateKeyResponse(BaseModel):
    """Response with a generated encryption key."""

    key: str


# ============================================================
# Endpoints
# ============================================================


@router.get(
    "/",
    response_model=List[CredentialServiceInfo],
    summary="List all credential services",
    description="Returns metadata and configuration status for all registered services.",
)
async def list_credentials():
    """List all credential services and their status."""
    svc = get_credential_service()
    return svc.list_services()


@router.get(
    "/{service_name}",
    response_model=CredentialServiceInfo,
    summary="Get credential service info",
    description="Returns metadata for a single service. Never returns secret values.",
)
async def get_credential(service_name: str):
    """Get metadata for a single credential service."""
    svc = get_credential_service()
    info = svc.get_service(service_name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    return info


@router.put(
    "/{service_name}",
    response_model=CredentialSaveResponse,
    summary="Save credentials",
    description="Encrypts and stores credentials for a service.",
)
async def save_credential(service_name: str, body: CredentialSaveRequest):
    """Save encrypted credentials for a service."""
    svc = get_credential_service()
    try:
        svc.save_credentials(service_name, body.primary, body.secondary)
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
    description="Clears stored credentials for a service.",
)
async def delete_credential(service_name: str):
    """Clear stored credentials for a service."""
    svc = get_credential_service()
    info = svc.get_service(service_name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

    svc.delete_credentials(service_name)
    return CredentialSaveResponse(
        service_name=service_name,
        is_configured=False,
        message=f"Credentials for '{service_name}' cleared.",
    )


@router.post(
    "/{service_name}/test",
    response_model=CredentialTestResponse,
    summary="Test credentials",
    description="Resolves credentials and runs a connectivity test via the appropriate connector.",
)
async def test_credential(service_name: str):
    """Resolve credentials and test connectivity for a service."""
    svc = get_credential_service()

    info = svc.get_service(service_name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

    # Resolve credentials
    primary, secondary, source = svc.resolve(service_name)
    if primary is None:
        svc.update_validation_status(service_name, "not_configured")
        return CredentialTestResponse(
            service_name=service_name,
            status="not_configured",
            message="No credentials configured (neither in DB nor environment).",
        )

    # Run connector test
    try:
        from uct_benchmark.uctp_lab.connectors import get_connector

        connector = get_connector(service_name)
        result = connector.test_connection()

        status = result.status
        svc.update_validation_status(service_name, "valid" if status == "connected" else "invalid")

        return CredentialTestResponse(
            service_name=service_name,
            status=status,
            message=result.error_message or f"Connection {status} (source: {source}).",
            response_time_ms=result.response_time_ms,
        )
    except KeyError:
        # No connector registered for this service — just validate credentials exist
        svc.update_validation_status(service_name, "valid")
        return CredentialTestResponse(
            service_name=service_name,
            status="configured",
            message=f"Credentials found (source: {source}), but no connectivity test available.",
        )
    except Exception as e:
        logger.error(f"Credential test failed for {service_name}: {e}")
        svc.update_validation_status(service_name, "error")
        return CredentialTestResponse(
            service_name=service_name,
            status="error",
            message=str(e),
        )


@router.post(
    "/generate-key",
    response_model=GenerateKeyResponse,
    summary="Generate encryption key",
    description="Generates a new Fernet encryption key for CREDENTIAL_ENCRYPTION_KEY.",
)
async def generate_encryption_key():
    """Generate a new Fernet encryption key."""
    from backend_api.services.credential_service import CredentialService

    key = CredentialService.generate_key()
    return GenerateKeyResponse(key=key)
