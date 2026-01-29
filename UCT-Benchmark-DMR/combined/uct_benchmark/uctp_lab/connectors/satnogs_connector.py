"""SatNOGS API connectivity tester."""

import time

from .base import AbstractConnector, ConnectionResult


class SatNOGSConnector(AbstractConnector):
    """Tests connectivity to the SatNOGS Network and DB APIs."""

    DB_API_URL = "https://db.satnogs.org/api/satellites/"

    @property
    def service_name(self) -> str:
        return "satnogs"

    def test_connection(self) -> ConnectionResult:
        start = time.time()
        try:
            import requests

            resp = requests.get(
                self.DB_API_URL,
                params={"format": "json", "page": 1},
                timeout=10,
            )
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                count = len(data) if isinstance(data, list) else 0
                return self._make_result(
                    status="connected",
                    response_time_ms=elapsed,
                    metadata={"record_count": count, "api": "db"},
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
