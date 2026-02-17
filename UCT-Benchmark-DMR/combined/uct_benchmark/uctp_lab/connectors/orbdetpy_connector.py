"""orbdetpy library connectivity tester."""

import time

from .base import AbstractConnector, ConnectionResult


class OrbdetpyConnector(AbstractConnector):
    """Tests whether orbdetpy is installed and functional."""

    @property
    def service_name(self) -> str:
        return "orbdetpy"

    def test_connection(self) -> ConnectionResult:
        start = time.time()
        try:
            import orbdetpy
            from orbdetpy import configure

            elapsed = (time.time() - start) * 1000

            return self._make_result(
                status="connected",
                response_time_ms=elapsed,
                metadata={"version": getattr(orbdetpy, "__version__", "unknown")},
            )
        except ImportError:
            return self._make_result(
                status="not_installed",
                error_message="orbdetpy package is not installed",
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return self._make_result(
                status="failed",
                response_time_ms=elapsed,
                error_message=str(e),
            )
