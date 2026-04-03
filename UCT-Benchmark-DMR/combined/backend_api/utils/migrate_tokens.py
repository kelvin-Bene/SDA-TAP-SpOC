"""
One-time migration script: encrypt existing plaintext tokens in the profiles table.

Idempotent — skips already-encrypted values. Safe to run multiple times.

Usage:
    python -m backend_api.utils.migrate_tokens
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from loguru import logger

from backend_api.utils.crypto import encrypt_token, is_encrypted


def migrate_tokens() -> None:
    """Encrypt all plaintext tokens in the profiles table."""
    from backend_api.database import get_db

    db = get_db()

    rows = db.execute(
        "SELECT id, udl_token, esa_token FROM profiles WHERE udl_token IS NOT NULL OR esa_token IS NOT NULL"
    ).fetchall()

    encrypted_count = 0
    skipped_count = 0

    for row_id, udl_token, esa_token in rows:
        updates = {}

        if udl_token and not is_encrypted(udl_token):
            updates["udl_token"] = encrypt_token(udl_token)
        elif udl_token:
            skipped_count += 1

        if esa_token and not is_encrypted(esa_token):
            updates["esa_token"] = encrypt_token(esa_token)
        elif esa_token:
            skipped_count += 1

        if updates:
            set_parts = []
            params = []
            for col, val in updates.items():
                set_parts.append(f"{col} = ?")
                params.append(val)
            params.append(row_id)

            db.execute(
                f"UPDATE profiles SET {', '.join(set_parts)} WHERE id = ?",
                tuple(params),
            )
            encrypted_count += 1

    logger.info(
        f"Token migration complete: {encrypted_count} profiles encrypted, "
        f"{skipped_count} tokens already encrypted"
    )


if __name__ == "__main__":
    migrate_tokens()
