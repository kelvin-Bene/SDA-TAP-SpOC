"""Orekit JVM connectivity tester."""

import time

from .base import AbstractConnector, ConnectionResult


class OrekitConnector(AbstractConnector):
    """Tests whether the Orekit JVM is initialised and functional."""

    @property
    def service_name(self) -> str:
        return "orekit"

    def test_connection(self) -> ConnectionResult:
        start = time.time()
        try:
            import orekit

            vm = orekit.initVM()
            elapsed = (time.time() - start) * 1000

            from org.orekit.frames import FramesFactory

            _ = FramesFactory.getEME2000()

            return self._make_result(
                status="connected",
                response_time_ms=elapsed,
                metadata={"jvm_running": True},
            )
        except ImportError:
            return self._make_result(
                status="not_installed",
                error_message="orekit-jpype package is not installed",
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return self._make_result(
                status="failed",
                response_time_ms=elapsed,
                error_message=str(e),
            )
