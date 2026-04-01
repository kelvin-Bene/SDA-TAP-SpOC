"""
Rate limiting configuration using slowapi.

The limiter is defined in a separate module to avoid circular imports
between main.py and the router modules.

Uses X-Forwarded-For to get the real client IP behind Railway's
load balancer / nginx reverse proxy.
"""

from starlette.requests import Request

from slowapi import Limiter


def _get_real_client_ip(request: Request) -> str:
    """
    Extract the real client IP from X-Forwarded-For header.

    Behind a reverse proxy (Railway, nginx), request.client.host is the
    proxy's IP. The real client IP is in X-Forwarded-For.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For is comma-separated: "client, proxy1, proxy2"
        return forwarded.split(",")[0].strip()
    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_get_real_client_ip)
