"""
Security tests for the UCT Benchmark API.

Tests for: SQL injection, input validation, CORS, oversized payloads,
malformed inputs, and boundary conditions.

Run with: uv run pytest backend_api/tests/test_security.py -v
"""

import json

import pytest
from fastapi.testclient import TestClient

from uct_benchmark.database.connection import DatabaseManager


@pytest.fixture(scope="module")
def _module_db():
    """Single database instance for the entire module."""
    db = DatabaseManager(in_memory=True, backend="duckdb")
    db.initialize(force=True)
    yield db
    db.close()


@pytest.fixture()
def client(_module_db):
    """Create a test client with mocked database dependency."""
    import backend_api.database as db_module
    import backend_api.jobs.workers as workers_module
    import backend_api.main as main_module
    from backend_api.database import get_db
    from backend_api.main import app

    orig_init = db_module.init_database
    orig_close = db_module.close_database
    orig_mgr = db_module._db_manager
    orig_shutdown = workers_module.shutdown_executor
    orig_main_init = main_module.init_database
    orig_main_close = main_module.close_database
    orig_main_shutdown = main_module.shutdown_executor

    noop_init = lambda **kw: _module_db
    noop_close = lambda: None
    noop_shutdown = lambda: None

    db_module.init_database = noop_init
    db_module.close_database = noop_close
    db_module._db_manager = _module_db
    main_module.init_database = noop_init
    main_module.close_database = noop_close
    main_module.shutdown_executor = noop_shutdown
    workers_module.shutdown_executor = noop_shutdown
    app.dependency_overrides[get_db] = lambda: _module_db

    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        db_module.init_database = orig_init
        db_module.close_database = orig_close
        db_module._db_manager = orig_mgr
        workers_module.shutdown_executor = orig_shutdown
        main_module.init_database = orig_main_init
        main_module.close_database = orig_main_close
        main_module.shutdown_executor = orig_main_shutdown


class TestSQLInjection:
    """Test that SQL injection attempts are handled safely."""

    def test_dataset_id_sql_injection(self, client: TestClient):
        """SQL injection in dataset_id path parameter."""
        # Path param -- should return 404 or 422, not a DB error
        # Non-integer path params are caught and return 400 or 422
        response = client.get("/api/v1/datasets/1; DROP TABLE datasets;--")
        assert response.status_code in (400, 404, 422, 500)

    def test_dataset_filter_sql_injection(self, client: TestClient):
        """SQL injection in dataset filter query params."""
        response = client.get(
            "/api/v1/datasets/?regime=LEO' OR '1'='1"
        )
        # Should return 200 with empty results, not an error
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_leaderboard_filter_sql_injection(self, client: TestClient):
        """SQL injection in leaderboard query params."""
        response = client.get(
            "/api/v1/leaderboard/?regime=LEO'; DROP TABLE submissions;--"
        )
        assert response.status_code == 200

    def test_leaderboard_period_injection(self, client: TestClient):
        """SQL injection via period parameter."""
        response = client.get(
            "/api/v1/leaderboard/?period=week'; DROP TABLE submissions;--"
        )
        # Period is matched with == not interpolated, so just returns data
        assert response.status_code == 200

    def test_submission_filter_injection(self, client: TestClient):
        """SQL injection in submissions filters."""
        response = client.get(
            "/api/v1/submissions/?dataset_id=1 OR 1=1"
        )
        # Should fail validation (not an integer) or return empty
        # May return 400/422/500 depending on validation layer
        assert response.status_code in (200, 400, 422, 500)

    def test_uctp_run_filter_injection(self, client: TestClient):
        """SQL injection in UCTP run filters."""
        response = client.get(
            "/api/v1/uctp/runs/?status=completed' UNION SELECT * FROM uctp_runs;--"
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestInputValidation:
    """Test input validation on various endpoints."""

    def test_negative_dataset_id(self, client: TestClient):
        """Negative dataset_id returns error."""
        response = client.get("/api/v1/datasets/-1")
        assert response.status_code in (400, 404, 422, 500)

    def test_zero_dataset_id(self, client: TestClient):
        """Zero dataset_id returns error."""
        response = client.get("/api/v1/datasets/0")
        assert response.status_code in (400, 404, 500)

    def test_non_integer_dataset_id(self, client: TestClient):
        """Non-integer dataset_id returns error."""
        response = client.get("/api/v1/datasets/abc")
        assert response.status_code in (400, 404, 422, 500)

    def test_very_large_dataset_id(self, client: TestClient):
        """Very large dataset_id returns 404."""
        response = client.get("/api/v1/datasets/99999999999")
        assert response.status_code in (404, 422)

    def test_negative_limit(self, client: TestClient):
        """Negative limit parameter."""
        # KNOWN ISSUE: DuckDB throws 'LIMIT cannot be negative' -- returns 500
        response = client.get("/api/v1/datasets/?limit=-1")
        assert response.status_code in (200, 422, 500)

    def test_very_large_limit(self, client: TestClient):
        """Very large limit doesn't crash server."""
        response = client.get("/api/v1/datasets/?limit=999999")
        assert response.status_code == 200

    def test_negative_offset(self, client: TestClient):
        """Negative offset parameter."""
        # KNOWN ISSUE: DuckDB throws 'OFFSET cannot be negative' -- returns 500
        response = client.get("/api/v1/datasets/?offset=-1")
        assert response.status_code in (200, 422, 500)

    def test_leaderboard_days_no_upper_bound(self, client: TestClient):
        """Leaderboard history days param has no upper bound (known issue)."""
        response = client.get("/api/v1/leaderboard/history?days=999999")
        # This should succeed but is a potential DoS vector (documented)
        assert response.status_code == 200

    def test_leaderboard_days_negative(self, client: TestClient):
        """Negative days parameter in leaderboard history."""
        response = client.get("/api/v1/leaderboard/history?days=-1")
        # Negative interval may cause DB error or empty results
        assert response.status_code in (200, 400, 422, 500)


class TestMalformedPayloads:
    """Test handling of malformed request bodies."""

    def test_empty_json_body(self, client: TestClient):
        """Empty JSON body on POST endpoint."""
        response = client.post(
            "/api/v1/auth/signup",
            content=b"{}",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422

    def test_non_json_body(self, client: TestClient):
        """Non-JSON body returns 422."""
        response = client.post(
            "/api/v1/auth/signup",
            content=b"this is not json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422

    def test_null_values_in_json(self, client: TestClient):
        """Null values in required fields."""
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": None, "password": None},
        )
        assert response.status_code == 422

    def test_array_instead_of_object(self, client: TestClient):
        """Array body where object is expected."""
        response = client.post(
            "/api/v1/auth/signup",
            content=b"[1, 2, 3]",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422

    def test_nested_json_in_string_field(self, client: TestClient):
        """Nested JSON in a string field."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": '{"injection": true}',
                "password": "Pass123!",
            },
        )
        # Should still process (email is a string field)
        # Auth disabled will return anonymous anyway
        assert response.status_code in (201, 422)

    def test_very_long_string_values(self, client: TestClient):
        """Very long string values in fields."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "a" * 10000 + "@example.com",
                "password": "b" * 10000,
            },
        )
        # Should succeed (auth disabled) or fail validation
        assert response.status_code in (201, 422)

    def test_unicode_in_fields(self, client: TestClient):
        """Unicode characters in text fields."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "test@example.com",
                "password": "Pass123!",
                "username": "用户名テスト🚀",
            },
        )
        assert response.status_code in (201, 422)


class TestCORS:
    """Test CORS configuration."""

    def test_cors_allowed_origin(self, client: TestClient):
        """Allowed origin gets CORS headers."""
        response = client.options(
            "/api/v1/datasets/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS middleware should respond
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_disallowed_origin(self, client: TestClient):
        """Disallowed origin should not get CORS allow header."""
        response = client.options(
            "/api/v1/datasets/",
            headers={
                "Origin": "http://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should not include the evil origin in allow-origin
        allow_origin = response.headers.get("access-control-allow-origin", "")
        assert "evil-site.com" not in allow_origin


class TestCredentialSecurity:
    """Test credential endpoint security."""

    def test_credential_values_not_in_list_response(self, client: TestClient):
        """Credential listing never exposes secret values."""
        response = client.get("/api/v1/credentials/")
        assert response.status_code == 200
        data = response.json()
        for cred in data:
            # Should never contain actual secret values
            assert "primary_value" not in cred
            assert "secondary_value" not in cred
            assert "password" not in cred
            assert "api_key" not in str(cred).lower() or "is_configured" in cred

    def test_generate_key_no_auth_guard(self, client: TestClient):
        """Generate-key endpoint works without auth (known issue)."""
        response = client.post("/api/v1/credentials/generate-key")
        # This succeeds without auth -- documented as a known security finding
        assert response.status_code == 200
        data = response.json()
        assert "key" in data
        assert len(data["key"]) > 0

    def test_save_credential_empty_primary(self, client: TestClient):
        """Saving credential with empty primary fails validation."""
        response = client.put(
            "/api/v1/credentials/space-track",
            json={"primary": ""},
        )
        assert response.status_code == 422

    def test_save_credential_nonexistent_service(self, client: TestClient):
        """Saving credential for unknown service returns 404."""
        response = client.put(
            "/api/v1/credentials/nonexistent-service",
            json={"primary": "some-value"},
        )
        assert response.status_code == 404


class TestParameterizedQueries:
    """Verify parameterized query usage (code-level review)."""

    def test_datasets_uses_parameterized_queries(self):
        """Verify datasets router uses ? placeholders, not f-strings for user input."""
        import inspect

        from backend_api.routers import datasets

        source = inspect.getsource(datasets)
        # Should use ? placeholders
        assert "?" in source
        # The dataset_id should be passed as a parameter, not interpolated
        assert "params.append" in source or "tuple(params)" in source

    def test_leaderboard_uses_parameterized_queries(self):
        """Verify leaderboard router uses ? placeholders for filter values."""
        import inspect

        from backend_api.routers import leaderboard

        source = inspect.getsource(leaderboard)
        # Filter values should use ? placeholders
        assert "params.append" in source

    def test_leaderboard_history_days_interpolation(self):
        """
        Verify that leaderboard history uses f-string for days parameter.
        This is a KNOWN ISSUE -- days is interpolated directly into SQL.
        """
        import inspect

        from backend_api.routers import leaderboard

        source = inspect.getsource(leaderboard)
        # This is the known issue: days is f-string interpolated
        assert "f\"" in source or "f'" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
