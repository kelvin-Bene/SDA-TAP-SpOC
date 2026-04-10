"""
Unit tests for the feedback router.

Run with: uv run pytest backend_api/tests/test_feedback.py -v
"""

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional

import pytest
from fastapi.testclient import TestClient

from uct_benchmark.database.connection import DatabaseManager


# ---------------------------------------------------------------------------
# Fake user fixtures
# ---------------------------------------------------------------------------

@dataclass
class FakeUser:
    id: str
    email: str
    role: str


ADMIN_USER = FakeUser(id="admin-001", email="admin@test.com", role="admin")
REGULAR_USER = FakeUser(id="user-001", email="user@test.com", role="user")


# ---------------------------------------------------------------------------
# Auto-reset the in-process rate limiter between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset slowapi rate limiter storage between tests to avoid cross-test 429s."""
    from backend_api.middleware.rate_limit import limiter

    if hasattr(limiter, "_limiter") and hasattr(limiter._limiter, "storage"):
        limiter._limiter.storage.reset()
    yield
    if hasattr(limiter, "_limiter") and hasattr(limiter._limiter, "storage"):
        limiter._limiter.storage.reset()


# ---------------------------------------------------------------------------
# Database fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def feedback_db(tmp_path: Path) -> Generator[DatabaseManager, None, None]:
    """Create a file-based DuckDB test database with a feedback table.

    DuckDB in-memory databases are per-thread, so a file-based database
    is required to share state between the test thread and the ASGI
    server thread inside TestClient.
    """
    db_path = tmp_path / "test_feedback.duckdb"
    db = DatabaseManager(db_path=db_path, backend="duckdb")
    db.initialize(force=True)

    # The DuckDB schema is missing the app_version column that the router
    # writes to.  Add it so INSERT statements succeed.
    try:
        db.execute("ALTER TABLE feedback ADD COLUMN app_version VARCHAR(50)")
    except Exception:
        pass  # Column may already exist

    yield db
    db.close()


# ---------------------------------------------------------------------------
# Client fixtures with auth dependency overrides
# ---------------------------------------------------------------------------

def _make_client(
    db: DatabaseManager,
    *,
    user: Optional[FakeUser] = None,
    optional_user: Optional[FakeUser] = None,
) -> TestClient:
    """Build a TestClient with the given db and auth overrides.

    Uses create_test_app() to skip the production lifespan (which tries
    to connect to the configured PostgreSQL instance).
    """
    from backend_api.middleware.auth import get_current_user, get_optional_user
    from backend_api.database import get_db
    from backend_api.main import create_test_app

    app = create_test_app()

    app.dependency_overrides[get_db] = lambda: db

    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user

    if optional_user is not None:
        app.dependency_overrides[get_optional_user] = lambda: optional_user
    else:
        # Anonymous: get_optional_user returns None
        app.dependency_overrides[get_optional_user] = lambda: None

    return TestClient(app)


@pytest.fixture
def anon_client(feedback_db: DatabaseManager) -> Generator[TestClient, None, None]:
    """Client with no authenticated user (anonymous feedback submission)."""
    from backend_api.main import app, reset_test_mode

    client = _make_client(feedback_db, optional_user=None)
    with client:
        yield client
    app.dependency_overrides.clear()
    reset_test_mode()


@pytest.fixture
def admin_client(feedback_db: DatabaseManager) -> Generator[TestClient, None, None]:
    """Client authenticated as an admin user."""
    from backend_api.main import app, reset_test_mode

    client = _make_client(feedback_db, user=ADMIN_USER, optional_user=ADMIN_USER)
    with client:
        yield client
    app.dependency_overrides.clear()
    reset_test_mode()


@pytest.fixture
def regular_client(feedback_db: DatabaseManager) -> Generator[TestClient, None, None]:
    """Client authenticated as a non-admin user."""
    from backend_api.main import app, reset_test_mode

    client = _make_client(feedback_db, user=REGULAR_USER, optional_user=REGULAR_USER)
    with client:
        yield client
    app.dependency_overrides.clear()
    reset_test_mode()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_FEEDBACK = {
    "description": "The leaderboard page crashes when I click sort.",
    "severity": "bug",
}


def _create_feedback(client: TestClient, payload: dict | None = None) -> dict:
    """POST a feedback item and return the response JSON."""
    resp = client.post("/api/v1/feedback", json=payload or VALID_FEEDBACK)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ===================================================================
# POST /api/v1/feedback
# ===================================================================

class TestSubmitFeedback:
    """Tests for POST /api/v1/feedback."""

    def test_valid_feedback_returns_201(self, anon_client: TestClient):
        """A minimal valid payload should return 201 with a feedback_id."""
        resp = anon_client.post("/api/v1/feedback", json=VALID_FEEDBACK)
        assert resp.status_code == 201

        body = resp.json()
        assert body["success"] is True
        assert "feedback_id" in body
        assert body["message"] == "Feedback submitted successfully."

    def test_authenticated_user_feedback(self, regular_client: TestClient):
        """Authenticated users can also submit feedback."""
        resp = regular_client.post("/api/v1/feedback", json=VALID_FEEDBACK)
        assert resp.status_code == 201
        assert resp.json()["success"] is True

    def test_missing_description_returns_422(self, anon_client: TestClient):
        """Omitting the required 'description' field triggers a validation error."""
        resp = anon_client.post(
            "/api/v1/feedback",
            json={"severity": "bug"},
        )
        assert resp.status_code == 422

    def test_missing_severity_returns_422(self, anon_client: TestClient):
        """Omitting the required 'severity' field triggers a validation error."""
        resp = anon_client.post(
            "/api/v1/feedback",
            json={"description": "Something broke"},
        )
        assert resp.status_code == 422

    def test_invalid_severity_returns_422(self, anon_client: TestClient):
        """A severity value not in the Literal set is rejected."""
        resp = anon_client.post(
            "/api/v1/feedback",
            json={"description": "Hmm", "severity": "critical"},
        )
        assert resp.status_code == 422

    def test_empty_description_returns_422(self, anon_client: TestClient):
        """An empty string description should fail min_length validation."""
        resp = anon_client.post(
            "/api/v1/feedback",
            json={"description": "", "severity": "bug"},
        )
        assert resp.status_code == 422

    def test_xss_in_description_gets_sanitized(self, admin_client: TestClient):
        """Script tags in the description are stripped before storage."""
        xss_payload = {
            "description": 'Hello <script>alert("xss")</script> world',
            "severity": "bug",
        }
        resp = admin_client.post("/api/v1/feedback", json=xss_payload)
        assert resp.status_code == 201
        feedback_id = resp.json()["feedback_id"]

        # Retrieve via admin GET to verify stored value
        detail_resp = admin_client.get(f"/api/v1/feedback/{feedback_id}")
        assert detail_resp.status_code == 200
        stored = detail_resp.json()["description"]
        assert "<script>" not in stored
        assert "alert" not in stored
        assert "Hello" in stored
        assert "world" in stored

    def test_html_tags_stripped_from_description(self, admin_client: TestClient):
        """Non-script HTML tags are also removed from description."""
        payload = {
            "description": "<b>Bold</b> and <img src=x onerror=alert(1)> text",
            "severity": "suggestion",
        }
        resp = admin_client.post("/api/v1/feedback", json=payload)
        assert resp.status_code == 201
        feedback_id = resp.json()["feedback_id"]

        detail_resp = admin_client.get(f"/api/v1/feedback/{feedback_id}")
        assert detail_resp.status_code == 200
        stored = detail_resp.json()["description"]
        assert "<b>" not in stored
        assert "<img" not in stored

    def test_screenshot_size_limit_enforced(self, anon_client: TestClient):
        """A screenshot_base64 larger than the Pydantic max_length is rejected."""
        # Pydantic model has max_length=3_000_000 on screenshot_base64.
        oversized = "A" * 3_000_001
        payload = {
            "description": "With screenshot",
            "severity": "bug",
            "screenshot_base64": oversized,
        }
        resp = anon_client.post("/api/v1/feedback", json=payload)
        # Pydantic rejects before the router's own 5MB check
        assert resp.status_code == 422

    def test_small_screenshot_accepted(self, anon_client: TestClient):
        """A small valid base64 screenshot is accepted."""
        small_b64 = base64.b64encode(b"tiny image data").decode()
        payload = {
            "description": "Small screenshot",
            "severity": "bug",
            "screenshot_base64": small_b64,
        }
        resp = anon_client.post("/api/v1/feedback", json=payload)
        assert resp.status_code == 201

    def test_optional_fields_accepted(self, anon_client: TestClient):
        """All optional fields are accepted when provided."""
        payload = {
            "description": "Full payload test",
            "severity": "question",
            "page_url": "https://uct-benchmark.example.com/leaderboard",
            "user_agent": "TestAgent/1.0",
            "viewport": "1920x1080",
            "recent_actions": [{"action": "click", "target": "sort-button"}],
            "console_errors": ["TypeError: x is not a function"],
            "app_version": "2.0.0",
        }
        resp = anon_client.post("/api/v1/feedback", json=payload)
        assert resp.status_code == 201


# ===================================================================
# GET /api/v1/feedback  (list -- admin only)
# ===================================================================

class TestListFeedback:
    """Tests for GET /api/v1/feedback."""

    def test_non_admin_gets_403(self, regular_client: TestClient):
        """A regular (non-admin) user is forbidden from listing feedback."""
        resp = regular_client.get("/api/v1/feedback")
        assert resp.status_code == 403
        assert "admin" in resp.json()["detail"].lower()

    def test_admin_gets_empty_list(self, admin_client: TestClient):
        """Admin listing an empty feedback table returns an empty list."""
        resp = admin_client.get("/api/v1/feedback")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_admin_sees_submitted_feedback(self, admin_client: TestClient):
        """Feedback submitted via POST shows up in the admin list."""
        _create_feedback(admin_client)
        _create_feedback(admin_client, {
            "description": "Second item",
            "severity": "suggestion",
        })

        resp = admin_client.get("/api/v1/feedback")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2

        # Verify structure of list items
        item = items[0]
        assert "id" in item
        assert "severity" in item
        assert "description" in item
        assert "status" in item
        assert "created_at" in item

    def test_admin_list_respects_limit(self, admin_client: TestClient):
        """The limit query parameter caps the returned count."""
        for i in range(3):
            _create_feedback(admin_client, {
                "description": f"Item {i}",
                "severity": "bug",
            })

        resp = admin_client.get("/api/v1/feedback?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ===================================================================
# GET /api/v1/feedback/{id}  (detail -- admin only)
# ===================================================================

class TestGetFeedbackDetail:
    """Tests for GET /api/v1/feedback/{id}."""

    def test_non_admin_gets_403(self, regular_client: TestClient):
        """Non-admin users cannot view feedback detail."""
        resp = regular_client.get("/api/v1/feedback/some-id")
        assert resp.status_code == 403

    def test_nonexistent_id_returns_404(self, admin_client: TestClient):
        """Requesting a feedback ID that doesn't exist returns 404."""
        resp = admin_client.get("/api/v1/feedback/nonexistent-uuid")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_admin_gets_detail(self, admin_client: TestClient):
        """Admin can retrieve full details of a feedback entry."""
        created = _create_feedback(admin_client)
        feedback_id = created["feedback_id"]

        resp = admin_client.get(f"/api/v1/feedback/{feedback_id}")
        assert resp.status_code == 200

        detail = resp.json()
        assert detail["id"] == feedback_id
        assert detail["description"] == VALID_FEEDBACK["description"]
        assert detail["severity"] == "bug"
        assert detail["status"] == "open"


# ===================================================================
# PATCH /api/v1/feedback/{id}  (update -- admin only)
# ===================================================================

class TestUpdateFeedback:
    """Tests for PATCH /api/v1/feedback/{id}."""

    def test_non_admin_gets_403(self, regular_client: TestClient):
        """Non-admin users cannot update feedback."""
        resp = regular_client.patch(
            "/api/v1/feedback/some-id",
            json={"status": "resolved"},
        )
        assert resp.status_code == 403

    def test_nonexistent_id_returns_404(self, admin_client: TestClient):
        """Patching a non-existent feedback ID returns 404."""
        resp = admin_client.patch(
            "/api/v1/feedback/nonexistent-uuid",
            json={"status": "resolved"},
        )
        assert resp.status_code == 404

    def test_update_status_returns_501(self, admin_client: TestClient):
        """PATCH /feedback is retired until the cross-project schema sync lands.
        Admin attempts return 501 with a pointer to BACKLOG.md section A.
        The previous 200-success behaviour referenced legacy columns
        (resolution/updated_at) that no longer exist on production."""
        created = _create_feedback(admin_client)
        feedback_id = created["feedback_id"]

        resp = admin_client.patch(
            f"/api/v1/feedback/{feedback_id}",
            json={"status": "resolved"},
        )
        assert resp.status_code == 501
        detail = resp.json()["detail"].lower()
        assert "cross-project feedback schema" in detail
        assert "backlog.md" in detail

    def test_update_resolution_returns_501(self, admin_client: TestClient):
        """PATCH /feedback is retired (see test_update_status_returns_501)."""
        created = _create_feedback(admin_client)
        feedback_id = created["feedback_id"]

        resp = admin_client.patch(
            f"/api/v1/feedback/{feedback_id}",
            json={"resolution": "Fixed in v2.1.0"},
        )
        assert resp.status_code == 501

    def test_update_no_fields_returns_400(self, admin_client: TestClient):
        """Sending an empty update body (no status, no resolution) returns 400."""
        created = _create_feedback(admin_client)
        feedback_id = created["feedback_id"]

        resp = admin_client.patch(
            f"/api/v1/feedback/{feedback_id}",
            json={},
        )
        assert resp.status_code == 400
        assert "no fields" in resp.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
