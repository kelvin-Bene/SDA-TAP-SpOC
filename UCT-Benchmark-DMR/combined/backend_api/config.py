"""
Centralized configuration for the UCT Benchmark API.

Loads from environment variables with sensible defaults.
Supports a DB_BACKEND feature flag for gradual migration from DuckDB to PostgreSQL.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DatabaseBackend(str, Enum):
    DUCKDB = "duckdb"
    POSTGRES = "postgres"


@dataclass
class AppConfig:
    """Application configuration loaded from environment variables."""

    # Database backend selection (feature flag)
    db_backend: DatabaseBackend = field(
        default_factory=lambda: DatabaseBackend(os.getenv("DB_BACKEND", "duckdb"))
    )

    # DuckDB (existing)
    duckdb_path: Optional[str] = field(default_factory=lambda: os.getenv("DATABASE_PATH"))

    # Supabase / PostgreSQL
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_anon_key: str = field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", ""))
    supabase_service_role_key: str = field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    )
    supabase_jwt_secret: str = field(default_factory=lambda: os.getenv("SUPABASE_JWT_SECRET", ""))
    postgres_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", os.getenv("SUPABASE_DB_URL", ""))
    )
    postgres_pool_min: int = field(
        default_factory=lambda: int(os.getenv("PG_POOL_MIN", "2"))
    )
    postgres_pool_max: int = field(
        default_factory=lambda: int(os.getenv("PG_POOL_MAX", "10"))
    )

    # Auth
    auth_enabled: bool = field(
        default_factory=lambda: os.getenv("AUTH_ENABLED", "false").lower() == "true"
    )

    # Encryption (existing)
    credential_encryption_key: Optional[str] = field(
        default_factory=lambda: os.getenv("CREDENTIAL_ENCRYPTION_KEY")
    )

    # CORS origins
    cors_origins: list = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
        ).split(",")
    )


_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the application configuration singleton."""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reset_config() -> None:
    """Reset the configuration singleton (for testing)."""
    global _config
    _config = None
