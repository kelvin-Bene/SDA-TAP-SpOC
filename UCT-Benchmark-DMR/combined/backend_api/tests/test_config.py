"""Tests for the centralized configuration module."""

import os
from unittest.mock import patch

from backend_api.config import AppConfig, DatabaseBackend, get_config, reset_config


class TestAppConfig:
    """Test AppConfig defaults and environment variable loading."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_default_db_backend_is_duckdb(self):
        config = AppConfig()
        assert config.db_backend == DatabaseBackend.DUCKDB

    def test_default_auth_disabled(self):
        config = AppConfig()
        assert config.auth_enabled is False

    def test_default_pool_settings(self):
        config = AppConfig()
        assert config.postgres_pool_min == 2
        assert config.postgres_pool_max == 10

    def test_default_supabase_empty(self):
        config = AppConfig()
        assert config.supabase_url == ""
        assert config.supabase_anon_key == ""
        assert config.supabase_service_role_key == ""
        assert config.supabase_jwt_secret == ""
        assert config.postgres_url == ""

    @patch.dict(os.environ, {"DB_BACKEND": "postgres"})
    def test_postgres_backend_from_env(self):
        config = AppConfig()
        assert config.db_backend == DatabaseBackend.POSTGRES

    @patch.dict(os.environ, {"AUTH_ENABLED": "true"})
    def test_auth_enabled_from_env(self):
        config = AppConfig()
        assert config.auth_enabled is True

    @patch.dict(os.environ, {"AUTH_ENABLED": "True"})
    def test_auth_enabled_case_insensitive(self):
        config = AppConfig()
        assert config.auth_enabled is True

    @patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co"})
    def test_supabase_url_from_env(self):
        config = AppConfig()
        assert config.supabase_url == "https://test.supabase.co"

    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/test"})
    def test_postgres_url_from_database_url(self):
        config = AppConfig()
        assert config.postgres_url == "postgresql://localhost/test"

    @patch.dict(os.environ, {"SUPABASE_DB_URL": "postgresql://sb.co/db"})
    def test_postgres_url_fallback_to_supabase_db_url(self):
        config = AppConfig()
        assert config.postgres_url == "postgresql://sb.co/db"

    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://primary",
        "SUPABASE_DB_URL": "postgresql://fallback",
    })
    def test_database_url_takes_precedence(self):
        config = AppConfig()
        assert config.postgres_url == "postgresql://primary"

    @patch.dict(os.environ, {"PG_POOL_MIN": "5", "PG_POOL_MAX": "20"})
    def test_pool_settings_from_env(self):
        config = AppConfig()
        assert config.postgres_pool_min == 5
        assert config.postgres_pool_max == 20

    @patch.dict(os.environ, {"CORS_ORIGINS": "https://app.com,https://api.com"})
    def test_cors_origins_from_env(self):
        config = AppConfig()
        assert config.cors_origins == ["https://app.com", "https://api.com"]

    def test_get_config_returns_singleton(self):
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_reset_config_clears_singleton(self):
        c1 = get_config()
        reset_config()
        c2 = get_config()
        assert c1 is not c2

    def test_database_backend_enum_values(self):
        assert DatabaseBackend.DUCKDB.value == "duckdb"
        assert DatabaseBackend.POSTGRES.value == "postgres"

    def test_database_backend_is_string_enum(self):
        assert isinstance(DatabaseBackend.DUCKDB, str)
        assert DatabaseBackend.DUCKDB == "duckdb"
