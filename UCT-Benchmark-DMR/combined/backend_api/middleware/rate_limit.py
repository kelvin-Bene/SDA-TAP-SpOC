"""
Rate limiting configuration using slowapi.

The limiter is defined in a separate module to avoid circular imports
between main.py and the router modules.

Uses X-Forwarded-For to get the real client IP behind Railway's
load balancer / nginx reverse proxy.
"""

import os

from starlette.requests import Request

from slowapi import Limiter

# Number of trusted reverse proxies in the chain.
# With depth=1 (default, single proxy like Railway/nginx), the last IP is trusted.
_TRUSTED_PROXY_DEPTH = int(os.getenv("TRUSTED_PROXY_DEPTH", "1"))


def _get_real_client_ip(request: Request) -> str:
    """
    Extract the real client IP from X-Forwarded-For header.

    Behind a reverse proxy (Railway, nginx), request.client.host is the
    proxy's IP. The real client IP is in X-Forwarded-For.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For is comma-separated: "client, proxy1, proxy2"
        # Trust the IP at position -(depth) from the right.
        ips = [ip.strip() for ip in forwarded.split(",")]
        index = max(0, len(ips) - _TRUSTED_PROXY_DEPTH)
        return ips[index]
    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


_storage_uri = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")
limiter = Limiter(key_func=_get_real_client_ip, storage_uri=_storage_uri)
