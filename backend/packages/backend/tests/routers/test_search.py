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
        response = test_client.get("/api/search", params={"query": "test", "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_search_with_q_alias(self, test_client: TestClient) -> None:
        """The 'q' query parameter is accepted."""
        response = test_client.get("/api/search", params={"q": "yellowstone"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_search_with_filters(self, test_client: TestClient) -> None:
        """Filter parameters (state, electric, pets, rv length) are accepted."""
        response = test_client.get(
            "/api/search",
            params={
                "q": "pines",
                "state": "CA",
                "has_electric": True,
                "pets_allowed": True,
                "min_rv_length": 30,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestSearchExplore:
    """Tests for GET /api/search/explore."""

    def test_search_explore_empty(self, test_client: TestClient) -> None:
        """Exploration on empty table returns zero results and default structure."""
        response = test_client.get("/api/search/explore", params={"query": "test"})
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "facets" in data
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_pages"] == 1

    def test_search_explore_pagination_params(self, test_client: TestClient) -> None:
        """Pagination and sorting parameters are accepted."""
        response = test_client.get(
            "/api/search/explore",
            params={
                "q": "yosemite",
                "page": 2,
                "page_size": 10,
                "sort_by": "name_asc",
                "state": "CA",
                "has_electric": True,
                "pets_allowed": True,
                "min_rv_length": 25,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert "providers" in data["facets"]
        assert "states" in data["facets"]
        assert "entity_types" in data["facets"]
