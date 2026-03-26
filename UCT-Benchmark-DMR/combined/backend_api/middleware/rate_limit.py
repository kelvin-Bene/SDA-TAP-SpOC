"""
Rate limiting configuration using slowapi.

The limiter is defined in a separate module to avoid circular imports
between main.py and the router modules.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
