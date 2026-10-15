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


class TestSearchBounds:
    """Bound live-search requests without changing successful response shapes."""

    def test_search_limit_bounds(self, test_client: TestClient) -> None:
        """Reject limits that exceed the supported autocomplete range."""
        for limit in (0, -1, 101):
            response = test_client.get(
                "/api/search", params={"q": "Pines", "limit": limit}
            )
            assert response.status_code == 422

    def test_search_query_bounds(self, test_client: TestClient) -> None:
        """Bound token work for both endpoints and query aliases."""
        for path in ("/api/search", "/api/search/explore", "/api/search/map/summary"):
            for alias in ("q", "query"):
                response = test_client.get(path, params={alias: "x" * 201})
                assert response.status_code == 422


class TestSearchMap:
    """Public map endpoints preserve catalog discovery and validate bounds."""

    def test_empty_summary(self, test_client: TestClient) -> None:
        """No catalog locations is an explicit successful empty summary."""
        response = test_client.get("/api/search/map/summary")
        assert response.status_code == 200
        assert response.json()["bounds"] is None
        assert response.json()["mappable_total"] == 0

    def test_invalid_viewports(self, test_client: TestClient) -> None:
        """Missing, reversed, equal and nonfinite map bounds are rejected."""
        invalid_params: list[dict[str, str | int]] = [
            {},
            {"west": 0, "east": 0, "south": -1, "north": 1, "zoom": 1},
            {"west": -1, "east": 1, "south": 2, "north": 1, "zoom": 1},
            {"west": 180, "east": -180, "south": -1, "north": 1, "zoom": 1},
            {"west": "nan", "east": 1, "south": 0, "north": 1, "zoom": 1},
        ]
        for params in invalid_params:
            assert test_client.get("/api/search/map", params=params).status_code == 422

    def test_valid_world_and_invalid_cells(self, test_client: TestClient) -> None:
        """World view is valid but malformed member identifiers are not."""
        params = {"west": -180, "east": 180, "south": -90, "north": 90, "zoom": 19}
        result = test_client.get("/api/search/map", params=params)
        assert result.status_code == 200
        assert len(result.json()["features"]) <= 512
        for cell in ["bad", "21:0:0", "1:2:0", "1:0:1"]:
            assert (
                test_client.get(
                    "/api/search/map/members", params={**params, "cell_id": cell}
                ).status_code
                == 422
            )


class TestExploreViewport:
    """Validate optional list extents with the same rules as map requests."""

    def test_optional_bounds(self, test_client: TestClient) -> None:
        """Accept complete dateline bounds, rejecting partial or invalid extents."""
        valid = {"west": 179, "south": -1, "east": -179, "north": 1}
        assert test_client.get("/api/search/explore", params=valid).status_code == 200
        invalid: tuple[dict[str, int | str], ...] = (
            {"west": 0},
            {**valid, "north": -2},
            {**valid, "west": 181},
            {**valid, "south": "nan"},
            {**valid, "east": 179},
        )
        for bounds in invalid:
            assert (
                test_client.get("/api/search/explore", params=bounds).status_code == 422
            )
