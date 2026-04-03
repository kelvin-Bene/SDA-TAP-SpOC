"""
Fernet-based token encryption for API credentials stored in the profiles table.

Reads ENCRYPTION_KEY from environment. Without it, operates in plaintext
passthrough mode (suitable for local dev).
"""

import os
from typing import Optional

from loguru import logger

_fernet = None
_warned_no_key = False


def _get_fernet():
    """Lazily initialize and cache the Fernet instance."""
    global _fernet, _warned_no_key

    if _fernet is not None:
        return _fernet

    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        if not _warned_no_key:
            logger.warning(
                "ENCRYPTION_KEY not set — tokens will be stored in plaintext. "
                "Set ENCRYPTION_KEY for production use."
            )
            _warned_no_key = True
        return None

    from cryptography.fernet import Fernet

    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token string. Refuses to store plaintext in production (postgres backend)."""
    if not plaintext:
        return plaintext
    f = _get_fernet()
    if f is None:
        # In production (postgres), refuse to store tokens unencrypted
        if os.getenv("DATABASE_BACKEND", "").lower() in ("postgres", "supabase"):
            raise RuntimeError(
                "ENCRYPTION_KEY must be set when using PostgreSQL. "
                "Refusing to store API tokens in plaintext."
            )
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> Optional[str]:
    """
    Decrypt a token string.

    Handles migration transparently: plaintext values pass through,
    Fernet ciphertext is decrypted. Returns None on decryption failure
    (e.g. key was rotated).
    """
    if not ciphertext:
        return ciphertext
    if not is_encrypted(ciphertext):
        return ciphertext

    f = _get_fernet()
    if f is None:
        # Encrypted value but no key available — can't decrypt
        logger.error("Found encrypted token but ENCRYPTION_KEY is not set — cannot decrypt")
        return None

    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        logger.error("Failed to decrypt token — encryption key may have been rotated")
        return None


def is_encrypted(value: str) -> bool:
    """Check if a value looks like Fernet ciphertext (gAAAAA prefix, length >= 100)."""
    return bool(value and value.startswith("gAAAAA") and len(value) >= 100)


def generate_key() -> str:
    """Generate a new Fernet encryption key. For initial setup / key rotation."""
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()
