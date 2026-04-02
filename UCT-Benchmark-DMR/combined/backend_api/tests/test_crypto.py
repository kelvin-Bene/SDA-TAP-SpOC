"""Tests for Fernet-based token encryption utilities."""
import os

import pytest
from cryptography.fernet import Fernet

import backend_api.utils.crypto as crypto_mod
from backend_api.utils.crypto import (
    decrypt_token,
    encrypt_token,
    generate_key,
    is_encrypted,
)


@pytest.fixture(autouse=True)
def _reset_crypto_module():
    """Reset module-level caches between every test so env changes take effect."""
    crypto_mod._fernet = None
    crypto_mod._warned_no_key = False
    yield
    crypto_mod._fernet = None
    crypto_mod._warned_no_key = False


@pytest.fixture()
def fernet_key() -> str:
    """Generate a fresh Fernet key for use in tests."""
    return Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# generate_key
# ---------------------------------------------------------------------------

class TestGenerateKey:
    """Tests for the generate_key helper."""

    def test_returns_valid_fernet_key(self):
        """generate_key should produce a key that Fernet accepts."""
        key = generate_key()
        # Fernet() raises ValueError for invalid keys
        f = Fernet(key.encode())
        assert f is not None

    def test_generates_unique_keys(self):
        """Successive calls should produce different keys."""
        assert generate_key() != generate_key()

    def test_key_is_str(self):
        """Key should be returned as a plain string, not bytes."""
        assert isinstance(generate_key(), str)


# ---------------------------------------------------------------------------
# is_encrypted
# ---------------------------------------------------------------------------

class TestIsEncrypted:
    """Tests for the is_encrypted detection heuristic."""

    def test_detects_fernet_ciphertext(self, fernet_key, monkeypatch):
        """Real Fernet ciphertext should be recognised."""
        monkeypatch.setenv("ENCRYPTION_KEY", fernet_key)
        ct = encrypt_token("secret-api-token")
        assert is_encrypted(ct) is True

    def test_rejects_plaintext(self):
        """Normal plaintext strings must not be flagged."""
        assert is_encrypted("hf_ABCdef123456") is False

    def test_rejects_empty_string(self):
        """Empty string should return False."""
        assert is_encrypted("") is False

    def test_rejects_short_gAAAAA_prefix(self):
        """A short string starting with gAAAAA is not valid ciphertext."""
        assert is_encrypted("gAAAAA_short") is False

    def test_rejects_none_like_falsy_values(self):
        """None/empty values should not raise."""
        assert is_encrypted("") is False


# ---------------------------------------------------------------------------
# encrypt_token / decrypt_token round-trip
# ---------------------------------------------------------------------------

class TestEncryptDecryptRoundtrip:
    """Tests for the encrypt -> decrypt cycle."""

    def test_roundtrip_with_valid_key(self, fernet_key, monkeypatch):
        """Encrypting then decrypting should recover the original value."""
        monkeypatch.setenv("ENCRYPTION_KEY", fernet_key)
        plaintext = "hf_mySecretToken12345"
        ciphertext = encrypt_token(plaintext)
        assert decrypt_token(ciphertext) == plaintext

    def test_ciphertext_differs_from_plaintext(self, fernet_key, monkeypatch):
        """Encrypted output must not equal the original plaintext."""
        monkeypatch.setenv("ENCRYPTION_KEY", fernet_key)
        plaintext = "super-secret"
        ciphertext = encrypt_token(plaintext)
        assert ciphertext != plaintext

    def test_ciphertext_starts_with_gAAAAA(self, fernet_key, monkeypatch):
        """Fernet ciphertext has a recognisable prefix."""
        monkeypatch.setenv("ENCRYPTION_KEY", fernet_key)
        ct = encrypt_token("token")
        assert ct.startswith("gAAAAA")

    def test_empty_string_passthrough(self, fernet_key, monkeypatch):
        """Empty input should pass through unchanged for both encrypt and decrypt."""
        monkeypatch.setenv("ENCRYPTION_KEY", fernet_key)
        assert encrypt_token("") == ""
        assert decrypt_token("") == ""


# ---------------------------------------------------------------------------
# decrypt_token edge cases
# ---------------------------------------------------------------------------

class TestDecryptToken:
    """Tests for decrypt_token edge-case handling."""

    def test_wrong_key_returns_none(self, monkeypatch):
        """Decrypting ciphertext with a different key should return None."""
        key_a = Fernet.generate_key().decode()
        key_b = Fernet.generate_key().decode()

        # Encrypt with key A
        monkeypatch.setenv("ENCRYPTION_KEY", key_a)
        ct = encrypt_token("secret")

        # Reset cache, switch to key B
        crypto_mod._fernet = None
        monkeypatch.setenv("ENCRYPTION_KEY", key_b)

        assert decrypt_token(ct) is None

    def test_plaintext_passes_through_without_key(self, monkeypatch):
        """Plaintext values pass through decrypt_token unchanged (migration path)."""
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
        assert decrypt_token("hf_plaintext_token") == "hf_plaintext_token"

    def test_encrypted_value_without_key_returns_none(self, fernet_key, monkeypatch):
        """Encrypted value with no ENCRYPTION_KEY set should return None."""
        monkeypatch.setenv("ENCRYPTION_KEY", fernet_key)
        ct = encrypt_token("secret")

        # Remove key and reset cache
        crypto_mod._fernet = None
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

        assert decrypt_token(ct) is None


# ---------------------------------------------------------------------------
# encrypt_token without key (plaintext / production guard)
# ---------------------------------------------------------------------------

class TestEncryptTokenNoKey:
    """Tests for encrypt_token behaviour when ENCRYPTION_KEY is absent."""

    def test_plaintext_passthrough_non_postgres(self, monkeypatch):
        """Without a key and not on postgres, tokens pass through as plaintext."""
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
        monkeypatch.delenv("DATABASE_BACKEND", raising=False)
        assert encrypt_token("hf_token") == "hf_token"

    def test_raises_on_postgres_without_key(self, monkeypatch):
        """On postgres backend without a key, encrypt_token must refuse."""
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
        monkeypatch.setenv("DATABASE_BACKEND", "postgres")
        with pytest.raises(RuntimeError, match="ENCRYPTION_KEY must be set"):
            encrypt_token("hf_token")

    def test_raises_on_supabase_without_key(self, monkeypatch):
        """Supabase backend should also be guarded."""
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
        monkeypatch.setenv("DATABASE_BACKEND", "supabase")
        with pytest.raises(RuntimeError, match="ENCRYPTION_KEY must be set"):
            encrypt_token("hf_token")
