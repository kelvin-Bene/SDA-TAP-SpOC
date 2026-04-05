"""
Credential management service.

Provides encrypted storage, retrieval, and resolution of API credentials
for external data services (UDL, ESA, Space-Track, CelesTrak, Orekit).

Encryption reuses the existing Fernet utilities in backend_api.utils.crypto.
Fallback chain: credentials table (encrypted) -> environment variable -> None.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from loguru import logger

from backend_api.utils.crypto import decrypt_token, encrypt_token

if TYPE_CHECKING:
    from uct_benchmark.database.connection import DatabaseManager

# Maps service_name -> primary env var name
ENV_VAR_MAP: dict[str, str] = {
    "udl": "UDL_TOKEN",
    "esa": "ESA_DISCOSWEBAPI_TOKEN",
    "spacetrack": "SPACETRACK_USER",
    "celestrak": "CELESTRAK_TOKEN",
    "orekit": "OREKIT_DATA_PATH",
}

# Human-readable labels and descriptions for each service
SERVICE_METADATA: dict[str, dict[str, str]] = {
    "udl": {
        "label": "Unified Data Library (UDL)",
        "description": "US Space Command observation and elset data",
    },
    "esa": {
        "label": "ESA DISCOSweb",
        "description": "European Space Agency space object catalogue",
    },
    "spacetrack": {
        "label": "Space-Track",
        "description": "NORAD TLE and conjunction data (Optional - breakup event analysis only)",
    },
    "celestrak": {
        "label": "CelesTrak",
        "description": "Supplementary TLE and space data (Optional - breakup event analysis only)",
    },
    "orekit": {
        "label": "Orekit Data",
        "description": "Local path to Orekit astrodynamics data files",
    },
}

VALID_SERVICES = set(ENV_VAR_MAP.keys())


class CredentialService:
    """Manages encrypted credential storage and resolution.

    Uses the existing Fernet encryption from backend_api.utils.crypto
    (shared ENCRYPTION_KEY) so credentials are compatible with the
    profiles-table token encryption already in place.
    """

    # ------------------------------------------------------------------
    # List / metadata
    # ------------------------------------------------------------------

    @staticmethod
    def list_services(db: "DatabaseManager", user_id: str) -> list[dict]:
        """Return metadata for all services for a given user.

        Never returns secret values -- only configuration status.
        """
        services: list[dict] = []

        for service_name in ENV_VAR_MAP:
            meta = SERVICE_METADATA.get(service_name, {})
            env_var = ENV_VAR_MAP[service_name]
            has_env = bool(os.getenv(env_var))

            # Check credentials table
            row = db.execute(
                "SELECT is_valid, validation_status, last_tested_at, encrypted_primary "
                "FROM credentials WHERE user_id = ? AND service_name = ?",
                (user_id, service_name),
            ).fetchone()

            if row and row[3]:  # has encrypted_primary
                source = "db"
                is_configured = True
                is_valid = row[0]
                validation_status = row[1] or "untested"
                last_tested_at = row[2]
            elif has_env:
                source = "env"
                is_configured = True
                is_valid = None
                validation_status = "untested"
                last_tested_at = None
            else:
                source = "none"
                is_configured = False
                is_valid = None
                validation_status = "not_configured"
                last_tested_at = None

            services.append({
                "service_name": service_name,
                "label": meta.get("label", service_name),
                "description": meta.get("description", ""),
                "is_configured": is_configured,
                "source": source,
                "validation_status": validation_status,
                "last_tested_at": (
                    last_tested_at.isoformat()
                    if isinstance(last_tested_at, datetime)
                    else str(last_tested_at) if last_tested_at else None
                ),
            })

        return services

    # ------------------------------------------------------------------
    # Save / delete
    # ------------------------------------------------------------------

    @staticmethod
    def save_credential(
        db: "DatabaseManager",
        user_id: str,
        service_name: str,
        primary_value: str,
        secondary_value: Optional[str] = None,
    ) -> None:
        """Encrypt and upsert a credential into the credentials table.

        Raises:
            ValueError: If service_name is not one of the 6 known services.
        """
        if service_name not in VALID_SERVICES:
            raise ValueError(
                f"Unknown service '{service_name}'. "
                f"Valid services: {', '.join(sorted(VALID_SERVICES))}"
            )

        encrypted_primary = encrypt_token(primary_value)
        encrypted_secondary = encrypt_token(secondary_value) if secondary_value else None

        # Upsert: try update first, insert if no row exists
        if db.backend == "postgres":
            db.execute(
                """
                INSERT INTO credentials (user_id, service_name, encrypted_primary, encrypted_secondary,
                                         validation_status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 'untested', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, service_name) DO UPDATE SET
                    encrypted_primary = EXCLUDED.encrypted_primary,
                    encrypted_secondary = EXCLUDED.encrypted_secondary,
                    is_valid = NULL,
                    validation_status = 'untested',
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, service_name, encrypted_primary, encrypted_secondary),
            )
        else:
            # DuckDB uses INSERT OR REPLACE
            db.execute(
                """
                INSERT OR REPLACE INTO credentials
                    (user_id, service_name, encrypted_primary, encrypted_secondary,
                     validation_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'untested', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (user_id, service_name, encrypted_primary, encrypted_secondary),
            )

        logger.info(f"Saved credential for user={user_id} service={service_name}")

    @staticmethod
    def delete_credential(
        db: "DatabaseManager",
        user_id: str,
        service_name: str,
    ) -> None:
        """Remove a credential from the credentials table."""
        if service_name not in VALID_SERVICES:
            raise ValueError(
                f"Unknown service '{service_name}'. "
                f"Valid services: {', '.join(sorted(VALID_SERVICES))}"
            )
        db.execute(
            "DELETE FROM credentials WHERE user_id = ? AND service_name = ?",
            (user_id, service_name),
        )
        logger.info(f"Deleted credential for user={user_id} service={service_name}")

    # ------------------------------------------------------------------
    # Resolve (DB -> env -> None)
    # ------------------------------------------------------------------

    @staticmethod
    def resolve(
        db: "DatabaseManager",
        user_id: str,
        service_name: str,
    ) -> Optional[str]:
        """Resolve a credential value using the fallback chain: DB -> env -> None.

        Returns the decrypted primary value, or None if no credential is available.
        """
        # 1. Try credentials table
        row = db.execute(
            "SELECT encrypted_primary FROM credentials WHERE user_id = ? AND service_name = ?",
            (user_id, service_name),
        ).fetchone()

        if row and row[0]:
            decrypted = decrypt_token(row[0])
            if decrypted is not None:
                return decrypted
            logger.warning(
                f"Credential decryption failed for user={user_id} service={service_name}, "
                "falling back to environment variable"
            )

        # 2. Try environment variable
        env_var = ENV_VAR_MAP.get(service_name)
        if env_var:
            env_val = os.getenv(env_var)
            if env_val:
                return env_val

        return None

    @staticmethod
    def resolve_secondary(
        db: "DatabaseManager",
        user_id: str,
        service_name: str,
    ) -> Optional[str]:
        """Resolve the secondary credential value (e.g. Space-Track password)."""
        row = db.execute(
            "SELECT encrypted_secondary FROM credentials WHERE user_id = ? AND service_name = ?",
            (user_id, service_name),
        ).fetchone()

        if row and row[0]:
            decrypted = decrypt_token(row[0])
            if decrypted is not None:
                return decrypted

        return None

    # ------------------------------------------------------------------
    # Connectivity testing
    # ------------------------------------------------------------------

    @staticmethod
    def test_connectivity(
        db: "DatabaseManager",
        user_id: str,
        service_name: str,
    ) -> dict:
        """Resolve a credential and test connectivity to the service.

        Updates validation_status and last_tested_at in the credentials table.

        Returns:
            Dict with keys: service_name, status, message.
        """
        if service_name not in VALID_SERVICES:
            raise ValueError(f"Unknown service '{service_name}'")

        primary = CredentialService.resolve(db, user_id, service_name)
        if primary is None:
            return {
                "service_name": service_name,
                "status": "not_configured",
                "message": "No credentials configured (neither in DB nor environment).",
            }

        # Call the appropriate validator
        from backend_api.utils.token_validation import (
            validate_celestrak_token,
            validate_esa_token,
            validate_orekit_path,
            validate_spacetrack_credentials,
            validate_udl_token,
        )

        validators = {
            "udl": lambda: validate_udl_token(primary),
            "esa": lambda: validate_esa_token(primary),
            "spacetrack": lambda: validate_spacetrack_credentials(
                primary,
                CredentialService.resolve_secondary(db, user_id, service_name) or "",
            ),
            "celestrak": lambda: validate_celestrak_token(primary),
            "orekit": lambda: validate_orekit_path(primary),
        }

        validator = validators.get(service_name)
        if validator is None:
            return {
                "service_name": service_name,
                "status": "unknown",
                "message": f"No validator available for {service_name}.",
            }

        is_valid, message = validator()
        status = "valid" if is_valid else "invalid"

        # Update credentials table with the result
        _update_validation(db, user_id, service_name, is_valid, status)

        return {
            "service_name": service_name,
            "status": status,
            "message": message,
        }


def _update_validation(
    db: "DatabaseManager",
    user_id: str,
    service_name: str,
    is_valid: bool,
    validation_status: str,
) -> None:
    """Update validation_status and last_tested_at for a credential row."""
    row = db.execute(
        "SELECT 1 FROM credentials WHERE user_id = ? AND service_name = ?",
        (user_id, service_name),
    ).fetchone()

    if row:
        db.execute(
            "UPDATE credentials SET is_valid = ?, validation_status = ?, "
            "last_tested_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = ? AND service_name = ?",
            (is_valid, validation_status, user_id, service_name),
        )
    else:
        logger.debug(
            f"No credential row to update for user={user_id} service={service_name}"
        )
