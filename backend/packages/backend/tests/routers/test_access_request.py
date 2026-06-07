# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Tests for the ``/api/request-access`` endpoint.
"""

from fastapi.testclient import TestClient


class TestRequestAccess:
    """Tests for POST /api/request-access."""

    def test_request_access_success(self, test_client: TestClient) -> None:
        """Submitting an access request should return 201."""
        response = test_client.post(
            "/api/request-access",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "created_at" in data

    def test_request_access_duplicate(self, test_client: TestClient) -> None:
        """Submitting the same email twice should return 409."""
        # First request
        response = test_client.post(
            "/api/request-access",
            json={"email": "duplicate@example.com"},
        )
        assert response.status_code == 201

        # Duplicate request
        response = test_client.post(
            "/api/request-access",
            json={"email": "duplicate@example.com"},
        )
        assert response.status_code == 409
        assert "already exists" in response.text

    def test_request_access_invalid_email(self, test_client: TestClient) -> None:
        """Submitting an invalid email should return 422."""
        response = test_client.post(
            "/api/request-access",
            json={"email": "not-an-email"},
        )
        assert response.status_code == 422
