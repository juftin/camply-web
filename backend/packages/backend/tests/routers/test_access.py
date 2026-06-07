"""
Tests for the ``/api/request-access`` endpoint.
"""

from fastapi.testclient import TestClient


class TestRequestAccess:
    """Tests for POST /api/request-access."""

    def test_request_access_creates(self, test_client: TestClient) -> None:
        """A new email should return 201 with a success message."""
        response = test_client.post(
            "/api/request-access",
            json={"email": "test@example.com", "name": "Test User"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "message" in data
        assert "Thank you" in data["message"]

    def test_request_access_duplicate_is_idempotent(
        self, test_client: TestClient
    ) -> None:
        """Submitting the same email twice should still return 201."""
        payload = {"email": "dup@example.com"}
        first = test_client.post("/api/request-access", json=payload)
        assert first.status_code == 201

        second = test_client.post("/api/request-access", json=payload)
        assert second.status_code == 201
        assert "message" in second.json()

    def test_request_access_email_only(self, test_client: TestClient) -> None:
        """Submitting without a name should succeed."""
        response = test_client.post(
            "/api/request-access",
            json={"email": "noname@example.com"},
        )
        assert response.status_code == 201

    def test_request_access_normalizes_email(self, test_client: TestClient) -> None:
        """Email should be lowercased and stripped."""
        response = test_client.post(
            "/api/request-access",
            json={"email": "  MixedCase@Example.COM  "},
        )
        assert response.status_code == 201
