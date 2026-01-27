"""Base connector interface for external service integrations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ConnectionResult:
    """Result from a connectivity test."""

    service_name: str
    status: str  # connected, failed, timeout, unauthorized, not_installed
    response_time_ms: Optional[float] = None
    last_checked: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "status": self.status,
            "response_time_ms": self.response_time_ms,
            "last_checked": self.last_checked,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class AbstractConnector(ABC):
    """Base class for all external service connectors."""

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Unique service identifier."""
        ...

    @abstractmethod
    def test_connection(self) -> ConnectionResult:
        """Test connectivity to this service."""
        ...

    def _make_result(
        self,
        status: str,
        response_time_ms: Optional[float] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConnectionResult:
        return ConnectionResult(
            service_name=self.service_name,
            status=status,
            response_time_ms=response_time_ms,
            last_checked=datetime.utcnow().isoformat(),
            error_message=error_message,
            metadata=metadata or {},
        )
