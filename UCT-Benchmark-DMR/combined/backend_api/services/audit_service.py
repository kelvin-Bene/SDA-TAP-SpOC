"""Audit and logging service.

Provides functions to persist audit events, API call logs, credential
access logs, and system events to the database.

All functions swallow exceptions — logging must never break the request.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger


def _get_db():
    """Get database instance, returning None if unavailable."""
    try:
        from backend_api.database import get_db
        return get_db()
    except Exception:
        return None


def _is_postgres() -> bool:
    """Check if the active backend is PostgreSQL."""
    try:
        from backend_api.config import DatabaseBackend, get_config
        return get_config().db_backend == DatabaseBackend.POSTGRES
    except Exception:
        return False


def log_audit_event(
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Write an entry to the audit_log table.

    Args:
        user_id: UUID of the acting user (may be None for system actions).
        action: One of CREATE, UPDATE, DELETE, ACCESS.
        resource_type: E.g. "dataset", "submission", "credential".
        resource_id: Primary key of the affected resource.
        details: Arbitrary JSON-serialisable context (old/new values).
        ip_address: Client IP.
        user_agent: Client user-agent string.
    """
    if not _is_postgres():
        return

    db = _get_db()
    if db is None:
        return

    try:
        import json
        db.execute(
            """
            INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, ip_address, user_agent, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                action,
                resource_type,
                resource_id,
                json.dumps(details) if details else None,
                ip_address,
                user_agent,
                datetime.now(timezone.utc),
            ),
        )
    except Exception as exc:
        logger.debug(f"Failed to log audit event: {exc}")


def log_api_call(
    user_id: Optional[str] = None,
    method: str = "",
    path: str = "",
    status_code: int = 0,
    request_body_size: int = 0,
    response_body_size: int = 0,
    duration_ms: float = 0.0,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """Write an entry to the api_call_log table."""
    if not _is_postgres():
        return

    db = _get_db()
    if db is None:
        return

    try:
        db.execute(
            """
            INSERT INTO api_call_log
                (user_id, method, path, status_code, request_body_size,
                 response_body_size, duration_ms, ip_address, user_agent,
                 error_message, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                method,
                path,
                status_code,
                request_body_size,
                response_body_size,
                duration_ms,
                ip_address,
                user_agent,
                error_message,
                datetime.now(timezone.utc),
            ),
        )
    except Exception as exc:
        logger.debug(f"Failed to log API call: {exc}")


def log_credential_access(
    user_id: Optional[str] = None,
    service_name: str = "",
    action: str = "resolve",
    source: str = "none",
    success: bool = True,
    ip_address: Optional[str] = None,
) -> None:
    """Write an entry to the credential_access_log table."""
    if not _is_postgres():
        return

    db = _get_db()
    if db is None:
        return

    try:
        db.execute(
            """
            INSERT INTO credential_access_log
                (user_id, service_name, action, source, success, ip_address, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                service_name,
                action,
                source,
                success,
                ip_address,
                datetime.now(timezone.utc),
            ),
        )
    except Exception as exc:
        logger.debug(f"Failed to log credential access: {exc}")


def log_system_event(
    level: str = "INFO",
    component: str = "",
    message: str = "",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Write an entry to the system_log table."""
    if not _is_postgres():
        return

    db = _get_db()
    if db is None:
        return

    try:
        import json
        db.execute(
            """
            INSERT INTO system_log (level, component, message, details, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                level,
                component,
                message,
                json.dumps(details) if details else None,
                datetime.now(timezone.utc),
            ),
        )
    except Exception as exc:
        logger.debug(f"Failed to log system event: {exc}")
