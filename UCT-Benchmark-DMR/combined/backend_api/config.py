"""Application configuration.

Provides a simple config object and DatabaseBackend enum used by the
audit service and other modules that need to know the active backend.
"""

import os
from dataclasses import dataclass
from enum import Enum


class DatabaseBackend(Enum):
    DUCKDB = "duckdb"
    POSTGRES = "postgres"


@dataclass
class AppConfig:
    db_backend: DatabaseBackend


def get_config() -> AppConfig:
    """Get application configuration from environment."""
    backend_str = os.getenv("DATABASE_BACKEND", "duckdb").lower()
    if backend_str in ("postgres", "postgresql"):
        backend = DatabaseBackend.POSTGRES
    else:
        backend = DatabaseBackend.DUCKDB
    return AppConfig(db_backend=backend)
