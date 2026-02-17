"""Base connector interface for external service integrations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple


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

    _credential_resolver: Optional[Callable[[str], Tuple[Optional[str], Optional[str], str]]] = None

    @classmethod
    def set_credential_resolver(
        cls,
        resolver: Callable[[str], Tuple[Optional[str], Optional[str], str]],
    ) -> None:
        """Set a credential resolver callable for all connectors.

        Args:
            resolver: A callable that takes a service_name and returns
                      (primary, secondary, source).
        """
        cls._credential_resolver = resolver

    def _get_credential(
        self, service_name: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Resolve credentials using the injected resolver.

        Args:
            service_name: Override service name. Defaults to self.service_name.

        Returns:
            Tuple of (primary, secondary). Both None if no resolver or no credentials.
        """
        name = service_name or self.service_name
        if self._credential_resolver is not None:
            try:
                primary, secondary, _source = self._credential_resolver(name)
                return primary, secondary
            except Exception:
                pass
        return None, None

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
