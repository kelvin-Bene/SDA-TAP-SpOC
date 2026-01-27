"""UDL (Unified Data Library) connectivity tester."""

import os
import time

from .base import AbstractConnector, ConnectionResult


class UDLConnector(AbstractConnector):
    """Tests connectivity to the Unified Data Library API."""

    BASE_URL = "https://unifieddatalibrary.com/udl"

    @property
    def service_name(self) -> str:
        return "udl"

    def test_connection(self) -> ConnectionResult:
        start = time.time()
        try:
            import requests

            # UDL requires authentication; test the base endpoint
            token = os.environ.get("UDL_TOKEN", "")
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            resp = requests.get(
                f"{self.BASE_URL}/health",
                headers=headers,
                timeout=10,
            )
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 200:
                return self._make_result(
                    status="connected",
                    response_time_ms=elapsed,
                    metadata={"authenticated": bool(token)},
                )
            elif resp.status_code == 401:
                return self._make_result(
                    status="unauthorized",
                    response_time_ms=elapsed,
                    error_message="UDL_TOKEN not set or invalid",
                    metadata={"authenticated": False},
                )
            else:
                return self._make_result(
                    status="failed",
                    response_time_ms=elapsed,
                    error_message=f"HTTP {resp.status_code}",
                )
        except ImportError:
            return self._make_result(
                status="not_installed",
                error_message="requests package is not installed",
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            msg = str(e)
            status = "timeout" if "timeout" in msg.lower() else "failed"
            return self._make_result(
                status=status,
                response_time_ms=elapsed,
                error_message=msg,
            )
