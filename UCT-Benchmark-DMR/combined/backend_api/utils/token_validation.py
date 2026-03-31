"""
Validate UDL and ESA API tokens by making lightweight test requests.

These are sync functions — call from async FastAPI handlers via asyncio.to_thread().
"""

import time

import requests
from loguru import logger


def _request_with_retry(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    params: dict | None = None,
    timeout: int = 10,
    max_retries: int = 1,
) -> requests.Response:
    """Make an HTTP request with retry on timeout/connection errors."""
    last_exc: Exception | None = None
    for attempt in range(1 + max_retries):
        try:
            resp = requests.request(
                method, url, headers=headers, params=params, timeout=timeout,
            )
            return resp
        except (requests.Timeout, requests.ConnectionError) as e:
            last_exc = e
            if attempt < max_retries:
                wait = 2 ** attempt  # 1s, 2s, ...
                logger.debug(f"Retry {attempt + 1}/{max_retries} after {wait}s: {e}")
                time.sleep(wait)
    raise last_exc  # type: ignore[misc]


def validate_udl_token(token: str) -> tuple[bool, str]:
    """
    Validate a UDL API token by querying the ISS elset count.

    Retries once on timeout/connection errors before failing.

    Returns:
        (True, "Valid") on success, (False, "reason") on failure.
    """
    try:
        resp = _request_with_retry(
            "GET",
            "https://unifieddatalibrary.com/udl/elset/current",
            headers={"Authorization": "Basic " + token},
            params={"satNo": "25544"},
            timeout=10,
            max_retries=1,
        )
        if resp.status_code == 200:
            return True, "Valid"
        if resp.status_code in (401, 403):
            return False, "Invalid UDL credentials"
        if resp.status_code == 429:
            return False, "UDL API rate limited — try again shortly"
        return False, f"UDL API returned status {resp.status_code}"
    except requests.Timeout:
        return False, "UDL API timed out after retries — service may be unavailable"
    except requests.ConnectionError:
        return False, "Cannot reach UDL API after retries — check network connectivity"
    except Exception as e:
        logger.debug(f"UDL token validation error: {e}")
        return False, f"UDL validation error: {type(e).__name__}"


def validate_esa_token(token: str) -> tuple[bool, str]:
    """
    Validate an ESA DiscoWeb API token by querying a single ISS record.

    Retries once on timeout/connection errors before failing.

    Returns:
        (True, "Valid") on success, (False, "reason") on failure.
    """
    try:
        resp = _request_with_retry(
            "GET",
            "https://discosweb.esoc.esa.int/api/objects",
            headers={
                "Authorization": f"Bearer {token}",
                "DiscosWeb-Api-Version": "2",
            },
            params={"filter": "in(satno,(25544))", "page[size]": "1"},
            timeout=10,
            max_retries=1,
        )
        if resp.status_code == 200:
            return True, "Valid"
        if resp.status_code in (401, 403):
            return False, "Invalid ESA credentials"
        if resp.status_code == 429:
            return False, "ESA API rate limited — try again shortly"
        return False, f"ESA API returned status {resp.status_code}"
    except requests.Timeout:
        return False, "ESA API timed out after retries — service may be unavailable"
    except requests.ConnectionError:
        return False, "Cannot reach ESA API after retries — check network connectivity"
    except Exception as e:
        logger.debug(f"ESA token validation error: {e}")
        return False, f"ESA validation error: {type(e).__name__}"
