"""
Credential management service.

Provides encrypted storage, retrieval, and resolution of API credentials.
Credentials are encrypted at rest using Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).

Fallback chain: DB (encrypted) -> .env -> None
If CREDENTIAL_ENCRYPTION_KEY is not set, the service operates in env-only mode.
"""

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from loguru import logger

if TYPE_CHECKING:
    from uct_benchmark.database.connection import DatabaseManager

# Maps service_name -> (primary_env_var, secondary_env_var)
ENV_VAR_MAP: Dict[str, Tuple[str, Optional[str]]] = {
    "udl": ("UDL_TOKEN", None),
    "esa": ("ESA_TOKEN", None),
    "nasa_earthdata": ("NASA_EARTHDATA_TOKEN", None),
    "spacetrack": ("SPACETRACK_USER", "SPACETRACK_PASS"),
    "orekit": ("OREKIT_DATA_PATH", None),
}


class CredentialService:
    """Manages encrypted credential storage and resolution.

    Args:
        db: DatabaseManager instance for persistence.
    """

    def __init__(self, db: "DatabaseManager") -> None:
        self._db = db
        self._fernet = None
        self._init_encryption()

    def _init_encryption(self) -> None:
        """Initialize Fernet cipher from environment key."""
        key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
        if not key:
            logger.warning(
                "CREDENTIAL_ENCRYPTION_KEY not set — credential service running in env-only mode. "
                "Set the key to enable encrypted DB storage."
            )
            return
        try:
            from cryptography.fernet import Fernet

            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}. Falling back to env-only mode.")

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key.

        Returns:
            URL-safe base64-encoded 32-byte key as a string.
        """
        from cryptography.fernet import Fernet

        return Fernet.generate_key().decode()

    def _encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string.

        Args:
            plaintext: The value to encrypt.

        Returns:
            Encrypted ciphertext as a string.

        Raises:
            RuntimeError: If encryption is not available.
        """
        if self._fernet is None:
            raise RuntimeError("Encryption not available — CREDENTIAL_ENCRYPTION_KEY not set")
        return self._fernet.encrypt(plaintext.encode()).decode()

    def _decrypt(self, ciphertext: str) -> str:
        """Decrypt a ciphertext string.

        Args:
            ciphertext: The encrypted value.

        Returns:
            Decrypted plaintext string.

        Raises:
            RuntimeError: If encryption is not available or decryption fails.
        """
        if self._fernet is None:
            raise RuntimeError("Encryption not available — CREDENTIAL_ENCRYPTION_KEY not set")
        return self._fernet.decrypt(ciphertext.encode()).decode()

    def list_services(self) -> List[dict]:
        """List all credential services with metadata (never secrets).

        Returns:
            List of dicts with service metadata and status info.
        """
        rows = self._db.execute(
            """
            SELECT service_name, credential_type, label, description,
                   is_configured, last_validated, validation_status,
                   created_at, updated_at
            FROM credentials
            ORDER BY service_name
            """
        ).fetchall()

        result = []
        for row in rows:
            service_name = row[0]
            env_primary, env_secondary = ENV_VAR_MAP.get(service_name, (None, None))
            has_env = bool(os.environ.get(env_primary)) if env_primary else False

            source = "none"
            if row[4]:  # is_configured
                source = "database"
            elif has_env:
                source = "environment"

            result.append({
                "service_name": service_name,
                "credential_type": row[1],
                "label": row[2],
                "description": row[3],
                "is_configured": row[4],
                "last_validated": row[5].isoformat() if row[5] else None,
                "validation_status": row[6],
                "source": source,
                "has_env_fallback": has_env,
                "created_at": row[7].isoformat() if row[7] else None,
                "updated_at": row[8].isoformat() if row[8] else None,
            })
        return result

    def get_service(self, service_name: str) -> Optional[dict]:
        """Get metadata for a single service (never secrets).

        Args:
            service_name: The service identifier.

        Returns:
            Service metadata dict, or None if not found.
        """
        row = self._db.execute(
            """
            SELECT service_name, credential_type, label, description,
                   is_configured, last_validated, validation_status,
                   created_at, updated_at
            FROM credentials
            WHERE service_name = ?
            """,
            (service_name,),
        ).fetchone()

        if row is None:
            return None

        env_primary, env_secondary = ENV_VAR_MAP.get(service_name, (None, None))
        has_env = bool(os.environ.get(env_primary)) if env_primary else False

        source = "none"
        if row[4]:  # is_configured
            source = "database"
        elif has_env:
            source = "environment"

        return {
            "service_name": row[0],
            "credential_type": row[1],
            "label": row[2],
            "description": row[3],
            "is_configured": row[4],
            "last_validated": row[5].isoformat() if row[5] else None,
            "validation_status": row[6],
            "source": source,
            "has_env_fallback": has_env,
            "created_at": row[7].isoformat() if row[7] else None,
            "updated_at": row[8].isoformat() if row[8] else None,
        }

    def save_credentials(
        self,
        service_name: str,
        primary: str,
        secondary: Optional[str] = None,
    ) -> None:
        """Encrypt and store credentials for a service.

        Args:
            service_name: The service identifier.
            primary: Primary credential (token, username, or path).
            secondary: Optional secondary credential (password).

        Raises:
            RuntimeError: If encryption is not available.
            ValueError: If service_name is unknown.
        """
        existing = self._db.execute(
            "SELECT 1 FROM credentials WHERE service_name = ?", (service_name,)
        ).fetchone()
        if existing is None:
            raise ValueError(f"Unknown service: {service_name}")

        encrypted_primary = self._encrypt(primary)
        encrypted_secondary = self._encrypt(secondary) if secondary else None

        self._db.execute(
            """
            UPDATE credentials
            SET encrypted_primary = ?,
                encrypted_secondary = ?,
                is_configured = TRUE,
                validation_status = 'untested',
                updated_at = CURRENT_TIMESTAMP
            WHERE service_name = ?
            """,
            (encrypted_primary, encrypted_secondary, service_name),
        )

    def delete_credentials(self, service_name: str) -> None:
        """Clear stored credentials for a service.

        Args:
            service_name: The service identifier.
        """
        self._db.execute(
            """
            UPDATE credentials
            SET encrypted_primary = NULL,
                encrypted_secondary = NULL,
                is_configured = FALSE,
                validation_status = 'untested',
                last_validated = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE service_name = ?
            """,
            (service_name,),
        )

    def update_validation_status(self, service_name: str, status: str) -> None:
        """Update the validation status of a service.

        Args:
            service_name: The service identifier.
            status: New validation status (e.g. 'valid', 'invalid', 'untested').
        """
        self._db.execute(
            """
            UPDATE credentials
            SET validation_status = ?,
                last_validated = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE service_name = ?
            """,
            (status, service_name),
        )

    def resolve(self, service_name: str) -> Tuple[Optional[str], Optional[str], str]:
        """Resolve credentials for a service using the fallback chain: DB -> .env -> None.

        Args:
            service_name: The service identifier.

        Returns:
            Tuple of (primary, secondary, source) where source is 'database', 'environment', or 'none'.
        """
        # Try DB first
        row = self._db.execute(
            "SELECT encrypted_primary, encrypted_secondary, is_configured FROM credentials WHERE service_name = ?",
            (service_name,),
        ).fetchone()

        if row and row[2] and row[0] and self._fernet is not None:
            try:
                primary = self._decrypt(row[0])
                secondary = self._decrypt(row[1]) if row[1] else None
                return primary, secondary, "database"
            except Exception as e:
                logger.warning(
                    f"Failed to decrypt credentials for {service_name}: {e}. "
                    "Falling back to environment variables."
                )

        # Try environment
        env_primary, env_secondary = ENV_VAR_MAP.get(service_name, (None, None))
        primary_val = os.environ.get(env_primary) if env_primary else None
        secondary_val = os.environ.get(env_secondary) if env_secondary else None

        if primary_val:
            return primary_val, secondary_val, "environment"

        return None, None, "none"

    def resolve_or_raise(self, service_name: str) -> Tuple[str, Optional[str], str]:
        """Resolve credentials or raise if not found.

        Args:
            service_name: The service identifier.

        Returns:
            Tuple of (primary, secondary, source).

        Raises:
            ValueError: If no credentials are available.
        """
        primary, secondary, source = self.resolve(service_name)
        if primary is None:
            env_primary, _ = ENV_VAR_MAP.get(service_name, (None, None))
            raise ValueError(
                f"No credentials configured for '{service_name}'. "
                f"Set them via the Settings UI or the {env_primary or 'environment variable'}."
            )
        return primary, secondary, source
