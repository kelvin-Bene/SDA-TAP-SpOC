"""Space-Track.org connectivity tester."""

import time

from .base import AbstractConnector, ConnectionResult


class SpaceTrackConnector(AbstractConnector):
    """Tests connectivity to the Space-Track.org REST API."""

    BASE_URL = "https://www.space-track.org"

    @property
    def service_name(self) -> str:
        return "spacetrack"

    def test_connection(self) -> ConnectionResult:
        start = time.time()
        try:
            import requests

            resp = requests.get(self.BASE_URL, timeout=10)
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 200:
                return self._make_result(
                    status="connected",
                    response_time_ms=elapsed,
                    metadata={"status_code": resp.status_code},
                )
            elif resp.status_code == 401:
                return self._make_result(
                    status="unauthorized",
                    response_time_ms=elapsed,
                    error_message="Authentication required",
                    metadata={"status_code": resp.status_code},
                )
            else:
                return self._make_result(
                    status="failed",
                    response_time_ms=elapsed,
                    error_message=f"HTTP {resp.status_code}",
                    metadata={"status_code": resp.status_code},
                )
        except ImportError:
            return self._make_result(
                status="not_installed",
                error_message="requests package is not installed",
            )
        except requests.exceptions.Timeout:
            elapsed = (time.time() - start) * 1000
            return self._make_result(
                status="timeout",
                response_time_ms=elapsed,
                error_message="Connection timed out after 10s",
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return self._make_result(
                status="failed",
                response_time_ms=elapsed,
                error_message=str(e),
            )
