"""Tests for the credential management system."""

import os
from unittest.mock import patch

import pytest

from uct_benchmark.database.connection import DatabaseManager

from backend_api.services.credential_service import CredentialService


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def fernet_key():
    """Generate a fresh Fernet key for testing."""
    return CredentialService.generate_key()


@pytest.fixture
def db():
    """Create an in-memory test database."""
    db = DatabaseManager(in_memory=True)
    db.initialize()
    yield db
    db.close()


@pytest.fixture
def cred_service(db, fernet_key):
    """Create a CredentialService with encryption enabled."""
    with patch.dict(os.environ, {"CREDENTIAL_ENCRYPTION_KEY": fernet_key}):
        yield CredentialService(db)


@pytest.fixture
def cred_service_no_key(db):
    """Create a CredentialService without an encryption key (env-only mode)."""
    env = os.environ.copy()
    env.pop("CREDENTIAL_ENCRYPTION_KEY", None)
    with patch.dict(os.environ, env, clear=True):
        yield CredentialService(db)


# ============================================================
# Encryption Tests
# ============================================================


class TestEncryption:
    def test_generate_key_returns_string(self):
        key = CredentialService.generate_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_encrypt_decrypt_roundtrip(self, cred_service):
        plaintext = "my-secret-token-12345"
        ciphertext = cred_service._encrypt(plaintext)
        assert ciphertext != plaintext
        assert cred_service._decrypt(ciphertext) == plaintext

    def test_wrong_key_fails_decrypt(self, db, fernet_key):
        with patch.dict(os.environ, {"CREDENTIAL_ENCRYPTION_KEY": fernet_key}):
            svc1 = CredentialService(db)
        ciphertext = svc1._encrypt("secret")

        other_key = CredentialService.generate_key()
        with patch.dict(os.environ, {"CREDENTIAL_ENCRYPTION_KEY": other_key}):
            svc2 = CredentialService(db)

        with pytest.raises(Exception):
            svc2._decrypt(ciphertext)

    def test_no_key_encrypt_raises(self, cred_service_no_key):
        with pytest.raises(RuntimeError, match="Encryption not available"):
            cred_service_no_key._encrypt("secret")


# ============================================================
# CRUD Tests
# ============================================================


class TestCRUD:
    def test_list_services_returns_seeded(self, cred_service):
        services = cred_service.list_services()
        names = {s["service_name"] for s in services}
        assert "udl" in names
        assert "esa" in names
        assert "nasa_earthdata" in names
        assert "spacetrack" in names
        assert "orekit" in names
        assert len(services) >= 5

    def test_get_service(self, cred_service):
        info = cred_service.get_service("udl")
        assert info is not None
        assert info["service_name"] == "udl"
        assert info["credential_type"] == "bearer_token"
        assert info["is_configured"] is False

    def test_get_unknown_service_returns_none(self, cred_service):
        assert cred_service.get_service("nonexistent") is None

    def test_save_and_resolve_roundtrip(self, cred_service):
        cred_service.save_credentials("udl", "my-udl-token")
        primary, secondary, source = cred_service.resolve("udl")
        assert primary == "my-udl-token"
        assert secondary is None
        assert source == "database"

    def test_save_username_password(self, cred_service):
        cred_service.save_credentials("spacetrack", "myuser", "mypass")
        primary, secondary, source = cred_service.resolve("spacetrack")
        assert primary == "myuser"
        assert secondary == "mypass"
        assert source == "database"

    def test_delete_clears_credentials(self, cred_service):
        cred_service.save_credentials("udl", "token-to-delete")
        cred_service.delete_credentials("udl")

        info = cred_service.get_service("udl")
        assert info["is_configured"] is False

    def test_save_unknown_service_raises(self, cred_service):
        with pytest.raises(ValueError, match="Unknown service"):
            cred_service.save_credentials("nonexistent", "value")

    def test_update_validation_status(self, cred_service):
        cred_service.update_validation_status("udl", "valid")
        info = cred_service.get_service("udl")
        assert info["validation_status"] == "valid"
        assert info["last_validated"] is not None


# ============================================================
# Resolve Fallback Chain Tests
# ============================================================


class TestResolveFallback:
    def test_resolve_from_env(self, cred_service):
        """DB not configured -> falls back to env var."""
        with patch.dict(os.environ, {"UDL_TOKEN": "env-token"}):
            primary, secondary, source = cred_service.resolve("udl")
        assert primary == "env-token"
        assert source == "environment"

    def test_resolve_db_over_env(self, cred_service):
        """DB configured -> DB wins over env."""
        cred_service.save_credentials("udl", "db-token")
        with patch.dict(os.environ, {"UDL_TOKEN": "env-token"}):
            primary, _, source = cred_service.resolve("udl")
        assert primary == "db-token"
        assert source == "database"

    def test_resolve_none_when_nothing(self, cred_service):
        """No DB, no env -> returns None."""
        env = os.environ.copy()
        env.pop("UDL_TOKEN", None)
        with patch.dict(os.environ, env, clear=True):
            primary, _, source = cred_service.resolve("udl")
        assert primary is None
        assert source == "none"

    def test_resolve_or_raise_error(self, cred_service):
        env = os.environ.copy()
        env.pop("UDL_TOKEN", None)
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="No credentials configured"):
                cred_service.resolve_or_raise("udl")

    def test_no_key_falls_back_to_env(self, cred_service_no_key):
        """Without encryption key, DB creds are skipped -> env fallback."""
        with patch.dict(os.environ, {"UDL_TOKEN": "env-only-token"}):
            primary, _, source = cred_service_no_key.resolve("udl")
        assert primary == "env-only-token"
        assert source == "environment"


# ============================================================
# API Endpoint Tests
# ============================================================


@pytest.fixture
def test_client(db, fernet_key):
    """Create a test client with credential service initialized."""
    import backend_api.database as db_module
    import backend_api.jobs.workers as workers_module
    from backend_api.database import get_db
    from backend_api.main import app

    def override_get_db():
        return db

    original_init = db_module.init_database
    original_close = db_module.close_database
    original_db_manager = db_module._db_manager
    original_cred_service = db_module._credential_service
    original_shutdown = workers_module.shutdown_executor

    def mock_init_database(db_path=None):
        db_module._db_manager = db
        return db

    def mock_close_database():
        db_module._db_manager = None
        db_module._credential_service = None

    def mock_shutdown_executor():
        pass

    db_module.init_database = mock_init_database
    db_module.close_database = mock_close_database
    db_module._db_manager = db
    workers_module.shutdown_executor = mock_shutdown_executor

    # Initialize credential service for tests
    with patch.dict(os.environ, {"CREDENTIAL_ENCRYPTION_KEY": fernet_key}):
        svc = CredentialService(db)
    db_module._credential_service = svc

    app.dependency_overrides[get_db] = override_get_db

    try:
        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        db_module.init_database = original_init
        db_module.close_database = original_close
        db_module._db_manager = original_db_manager
        db_module._credential_service = original_cred_service
        workers_module.shutdown_executor = original_shutdown


class TestAPIEndpoints:
    def test_list_credentials(self, test_client):
        resp = test_client.get("/api/v1/credentials/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 5
        names = {s["service_name"] for s in data}
        assert "udl" in names

    def test_get_single(self, test_client):
        resp = test_client.get("/api/v1/credentials/udl")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service_name"] == "udl"

    def test_get_not_found(self, test_client):
        resp = test_client.get("/api/v1/credentials/nonexistent")
        assert resp.status_code == 404

    def test_put_save(self, test_client):
        resp = test_client.put(
            "/api/v1/credentials/udl",
            json={"primary": "test-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_configured"] is True

    def test_put_empty_primary_validation(self, test_client):
        resp = test_client.put(
            "/api/v1/credentials/udl",
            json={"primary": ""},
        )
        assert resp.status_code == 422

    def test_delete(self, test_client):
        # Save first
        test_client.put("/api/v1/credentials/esa", json={"primary": "token"})
        resp = test_client.delete("/api/v1/credentials/esa")
        assert resp.status_code == 200
        assert resp.json()["is_configured"] is False

    def test_test_no_creds(self, test_client):
        resp = test_client.post("/api/v1/credentials/esa/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("not_configured", "connected", "failed", "error", "configured")

    def test_generate_key(self, test_client):
        resp = test_client.post("/api/v1/credentials/generate-key")
        assert resp.status_code == 200
        data = resp.json()
        assert "key" in data
        assert len(data["key"]) > 0
