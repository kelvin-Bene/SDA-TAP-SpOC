"""UDL (Unified Data Library) connectivity tester."""

import os
import time
from datetime import datetime, timedelta, timezone

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

            # Resolve token: credential service -> env var fallback
            token, _ = self._get_credential()
            if not token:
                token = os.environ.get("UDL_TOKEN", "")
            if not token:
                return self._make_result(
                    status="unauthorized",
                    error_message="UDL_TOKEN environment variable not set",
                    metadata={"authenticated": False},
                )

            headers = {"Authorization": f"Basic {token}"}

            # UDL has no /health endpoint; use a lightweight data query
            yesterday = (
                datetime.now(timezone.utc) - timedelta(days=1)
            ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            resp = requests.get(
                f"{self.BASE_URL}/elset/history",
                headers=headers,
                params={"epoch": f">{yesterday}", "satNo": "25544"},
                timeout=15,
            )
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                count = len(data) if isinstance(data, list) else 0
                return self._make_result(
                    status="connected",
                    response_time_ms=elapsed,
                    metadata={"authenticated": True, "record_count": count},
                )
            elif resp.status_code == 401:
                return self._make_result(
                    status="unauthorized",
                    response_time_ms=elapsed,
                    error_message="UDL_TOKEN is invalid or expired",
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
