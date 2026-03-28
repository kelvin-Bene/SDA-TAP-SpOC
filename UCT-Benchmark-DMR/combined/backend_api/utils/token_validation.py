"""
Validate UDL and ESA API tokens by making lightweight test requests.

These are sync functions — call from async FastAPI handlers via asyncio.to_thread().
"""

import requests
from loguru import logger


def validate_udl_token(token: str) -> tuple[bool, str]:
    """
    Validate a UDL API token by querying the ISS elset count.

    Returns:
        (True, "Valid") on success, (False, "reason") on failure.
    """
    try:
        resp = requests.get(
            "https://unifieddatalibrary.com/udl/elset/current",
            headers={"Authorization": "Basic " + token},
            params={"satNo": "25544"},
            timeout=10,
        )
        if resp.status_code == 200:
            return True, "Valid"
        if resp.status_code in (401, 403):
            return False, "Invalid UDL credentials"
        if resp.status_code == 429:
            return False, "UDL API rate limited — try again shortly"
        return False, f"UDL API returned status {resp.status_code}"
    except requests.Timeout:
        return False, "UDL API timed out — service may be unavailable"
    except requests.ConnectionError:
        return False, "Cannot reach UDL API — check network connectivity"
    except Exception as e:
        logger.debug(f"UDL token validation error: {e}")
        return False, f"UDL validation error: {type(e).__name__}"


def validate_esa_token(token: str) -> tuple[bool, str]:
    """
    Validate an ESA DiscoWeb API token by querying a single ISS record.

    Returns:
        (True, "Valid") on success, (False, "reason") on failure.
    """
    try:
        resp = requests.get(
            "https://discosweb.esoc.esa.int/api/objects",
            headers={
                "Authorization": f"Bearer {token}",
                "DiscosWeb-Api-Version": "2",
            },
            params={"filter": "in(satno,(25544))", "page[size]": "1"},
            timeout=10,
        )
        if resp.status_code == 200:
            return True, "Valid"
        if resp.status_code in (401, 403):
            return False, "Invalid ESA credentials"
        if resp.status_code == 429:
            return False, "ESA API rate limited — try again shortly"
        return False, f"ESA API returned status {resp.status_code}"
    except requests.Timeout:
        return False, "ESA API timed out — service may be unavailable"
    except requests.ConnectionError:
        return False, "Cannot reach ESA API — check network connectivity"
    except Exception as e:
        logger.debug(f"ESA token validation error: {e}")
        return False, f"ESA validation error: {type(e).__name__}"
