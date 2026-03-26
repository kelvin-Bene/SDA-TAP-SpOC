"""
Structured audit logging for security-sensitive operations (S12).

Logs who accessed/modified data with structured fields for analysis.
"""

import time
from typing import Optional

from loguru import logger


def audit_log(
    action: str,
    user_id: str = "anonymous",
    resource_type: str = "",
    resource_id: str = "",
    details: Optional[str] = None,
) -> None:
    """
    Emit a structured audit log entry.

    Args:
        action: What happened (e.g., "dataset.create", "submission.upload")
        user_id: Who did it (from JWT sub claim)
        resource_type: What kind of resource (dataset, submission, result)
        resource_id: Which specific resource
        details: Optional additional context
    """
    logger.bind(
        audit=True,
        action=action,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        timestamp=time.time(),
    ).info(
        f"AUDIT: {action} by={user_id} resource={resource_type}/{resource_id}"
        + (f" detail={details}" if details else "")
    )
