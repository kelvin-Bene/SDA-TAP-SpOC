"""
Tests for the audit service functions.

Verifies that each logging function:
- Executes the correct SQL with proper parameters
- Does not raise exceptions when the database is unavailable
- Handles None values gracefully
"""

from unittest.mock import MagicMock, patch

import pytest

from backend_api.services.audit_service import (
    log_api_call,
    log_audit_event,
    log_credential_access,
    log_system_event,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def _force_postgres():
    """Make _is_postgres() return True so the logging functions execute."""
    with patch("backend_api.services.audit_service._is_postgres", return_value=True):
        yield


@pytest.fixture
def mock_db():
    """Create a mock database manager."""
    db = MagicMock()
    db.execute = MagicMock()
    return db


def _patch_db(mock_db):
    """Patch _get_db to return the mock database."""
    return patch("backend_api.services.audit_service._get_db", return_value=mock_db)


# =============================================================================
# log_api_call TESTS
# =============================================================================


class TestLogApiCall:
    """Tests for the log_api_call function."""

    def test_log_api_call_basic(self, mock_db):
        """Test basic API call logging with all parameters."""
        with _patch_db(mock_db):
            log_api_call(
                user_id="user-123",
                method="POST",
                path="/api/v1/datasets",
                status_code=201,
                duration_ms=42.567,
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert "api_call_log" in sql
        assert "INSERT INTO" in sql
        assert params[0] == "user-123"
        assert params[1] == "POST"
        assert params[2] == "/api/v1/datasets"
        assert params[3] == 201

    def test_log_api_call_with_none_user(self, mock_db):
        """Test API call logging when user_id is None."""
        with _patch_db(mock_db):
            log_api_call(
                user_id=None,
                method="DELETE",
                path="/api/v1/datasets/1",
                status_code=204,
                duration_ms=10.0,
            )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[0] is None  # user_id should be None

    def test_log_api_call_db_unavailable(self):
        """Test that log_api_call does not raise when DB is unavailable."""
        with patch(
            "backend_api.services.audit_service._get_db",
            return_value=None,
        ):
            # Should not raise
            log_api_call(
                user_id="user-1",
                method="POST",
                path="/test",
                status_code=500,
                duration_ms=100.0,
            )

    def test_log_api_call_db_execute_fails(self, mock_db):
        """Test that log_api_call does not raise when execute fails."""
        mock_db.execute.side_effect = Exception("Connection lost")
        with _patch_db(mock_db):
            # Should not raise
            log_api_call(
                user_id="user-1",
                method="POST",
                path="/test",
                status_code=500,
                duration_ms=100.0,
            )


# =============================================================================
# log_audit_event TESTS
# =============================================================================


class TestLogAuditEvent:
    """Tests for the log_audit_event function."""

    def test_log_audit_event_basic(self, mock_db):
        """Test basic audit event logging."""
        with _patch_db(mock_db):
            log_audit_event(
                user_id="user-456",
                action="create",
                resource_type="dataset",
                resource_id="42",
                details={"name": "Test Dataset"},
                ip_address="10.0.0.1",
            )

        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert "audit_log" in sql
        assert "INSERT INTO" in sql
        assert params[0] == "user-456"
        assert params[1] == "create"
        assert params[2] == "dataset"
        assert params[3] == "42"
        assert '"name": "Test Dataset"' in params[4]
        assert params[5] == "10.0.0.1"

    def test_log_audit_event_none_details(self, mock_db):
        """Test audit event logging with no details."""
        with _patch_db(mock_db):
            log_audit_event(
                user_id="user-1",
                action="delete",
                resource_type="submission",
                resource_id="99",
            )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[4] is None  # details should be None

    def test_log_audit_event_none_resource_id(self, mock_db):
        """Test audit event logging with no resource_id."""
        with _patch_db(mock_db):
            log_audit_event(
                user_id="user-1",
                action="list",
                resource_type="datasets",
                resource_id=None,
            )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[3] is None  # resource_id should be None

    def test_log_audit_event_db_unavailable(self):
        """Test that log_audit_event does not raise when DB is unavailable."""
        with patch(
            "backend_api.services.audit_service._get_db",
            return_value=None,
        ):
            log_audit_event(
                user_id="user-1",
                action="create",
                resource_type="dataset",
                resource_id="1",
            )


# =============================================================================
# log_credential_access TESTS
# =============================================================================


class TestLogCredentialAccess:
    """Tests for the log_credential_access function."""

    def test_log_credential_access_basic(self, mock_db):
        """Test basic credential access logging."""
        with _patch_db(mock_db):
            log_credential_access(
                user_id="user-789",
                service_name="openai",
                action="read",
                source="db",
                success=True,
                ip_address="172.16.0.1",
            )

        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert "credential_access_log" in sql
        assert "INSERT INTO" in sql
        assert params[0] == "user-789"
        assert params[1] == "openai"
        assert params[2] == "read"
        assert params[3] == "db"
        assert params[4] is True

    def test_log_credential_access_failure(self, mock_db):
        """Test logging a failed credential access."""
        with _patch_db(mock_db):
            log_credential_access(
                user_id="user-1",
                service_name="aws",
                action="rotate",
                source="env",
                success=False,
            )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[4] is False  # success should be False

    def test_log_credential_access_none_user(self, mock_db):
        """Test credential access logging with None user_id."""
        with _patch_db(mock_db):
            log_credential_access(
                user_id=None,
                service_name="api-key",
                action="read",
            )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[0] is None

    def test_log_credential_access_db_unavailable(self):
        """Test that log_credential_access does not raise when DB is unavailable."""
        with patch(
            "backend_api.services.audit_service._get_db",
            return_value=None,
        ):
            log_credential_access(
                user_id="user-1",
                service_name="test",
                action="read",
            )


# =============================================================================
# log_system_event TESTS
# =============================================================================


class TestLogSystemEvent:
    """Tests for the log_system_event function."""

    def test_log_system_event_basic(self, mock_db):
        """Test basic system event logging."""
        with _patch_db(mock_db):
            log_system_event(
                level="INFO",
                component="jobs",
                message="Job manager initialized",
                details={"backend": "postgres"},
            )

        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert "system_log" in sql
        assert "INSERT INTO" in sql
        assert params[0] == "INFO"
        assert params[1] == "jobs"
        assert params[2] == "Job manager initialized"
        assert '"backend": "postgres"' in params[3]

    def test_log_system_event_no_details(self, mock_db):
        """Test system event logging without details."""
        with _patch_db(mock_db):
            log_system_event(
                level="WARNING",
                component="auth",
                message="Rate limit approaching",
            )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[3] is None  # details should be None

    def test_log_system_event_error_level(self, mock_db):
        """Test system event logging with ERROR level."""
        with _patch_db(mock_db):
            log_system_event(
                level="ERROR",
                component="database",
                message="Connection pool exhausted",
                details={"pool_size": 10, "active": 10},
            )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[0] == "ERROR"

    def test_log_system_event_db_unavailable(self):
        """Test that log_system_event does not raise when DB is unavailable."""
        with patch(
            "backend_api.services.audit_service._get_db",
            return_value=None,
        ):
            log_system_event(
                level="ERROR",
                component="startup",
                message="Failed to connect",
            )

    def test_log_system_event_db_execute_fails(self, mock_db):
        """Test that log_system_event does not raise when execute fails."""
        mock_db.execute.side_effect = Exception("Disk full")
        with _patch_db(mock_db):
            log_system_event(
                level="ERROR",
                component="disk",
                message="Write failed",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
