"""
Tests for the ``/api/search`` endpoint.
"""

from fastapi.testclient import TestClient


class TestSearch:
    """Tests for GET /api/search."""

    def test_search_basic(self, test_client: TestClient) -> None:
        """A basic search query returns a list (empty table = empty list)."""
        response = test_client.get("/api/search", params={"query": "test"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_search_empty_query(self, test_client: TestClient) -> None:
        """An empty query returns an empty list."""
        response = test_client.get("/api/search", params={"query": ""})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_search_custom_limit(self, test_client: TestClient) -> None:
        """The limit parameter is accepted."""
        response = test_client.get(
            "/api/search", params={"query": "test", "limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
