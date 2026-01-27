"""External API connectors for UCTP Lab."""

from typing import Callable, Dict, List, Optional, Tuple

from .base import AbstractConnector, ConnectionResult
from .celestrak_connector import CelesTrakConnector
from .orbdetpy_connector import OrbdetpyConnector
from .orekit_connector import OrekitConnector
from .satnogs_connector import SatNOGSConnector
from .spacetrack_connector import SpaceTrackConnector
from .udl_connector import UDLConnector

ALL_CONNECTORS: List[AbstractConnector] = [
    OrekitConnector(),
    OrbdetpyConnector(),
    SpaceTrackConnector(),
    SatNOGSConnector(),
    CelesTrakConnector(),
    UDLConnector(),
]

_CONNECTOR_MAP: Dict[str, AbstractConnector] = {
    c.service_name: c for c in ALL_CONNECTORS
}


def get_connector(service_name: str) -> AbstractConnector:
    """Look up a connector by service name."""
    if service_name not in _CONNECTOR_MAP:
        raise KeyError(f"Unknown service: {service_name}")
    return _CONNECTOR_MAP[service_name]


def test_all_connections() -> List[ConnectionResult]:
    """Test every registered connector and return results."""
    return [c.test_connection() for c in ALL_CONNECTORS]


def init_credential_resolver(
    resolver_fn: Callable[[str], Tuple[Optional[str], Optional[str], str]],
) -> None:
    """Wire a credential resolver into all connectors.

    Args:
        resolver_fn: A callable that takes a service_name and returns
                     (primary, secondary, source).
    """
    AbstractConnector.set_credential_resolver(resolver_fn)


__all__ = [
    "AbstractConnector",
    "ConnectionResult",
    "ALL_CONNECTORS",
    "get_connector",
    "test_all_connections",
    "init_credential_resolver",
]
