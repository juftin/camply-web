"""Python hosting must preserve API errors and the frontend asset boundary."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.static import attach_frontend


@pytest.fixture
def site(tmp_path: Path) -> TestClient:
    """Host a synthetic build after a real API route."""
    (tmp_path / "index.html").write_text("<html>synthetic app</html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/app-123.js").write_text("export {}")
    app = FastAPI()

    @app.get("/api/health")
    def health() -> dict[str, bool]:
        """Represent an API route that must win over static serving."""
        return {"ready": True}

    attach_frontend(app, tmp_path)
    return TestClient(app)


def test_deep_link_and_asset_caching(site: TestClient) -> None:
    """Serve navigation and fingerprinted assets with different cache lifetimes."""
    assert (
        "synthetic app" in site.get("/dashboard", headers={"Accept": "text/html"}).text
    )
    assert site.get("/").headers["cache-control"] == "no-cache"
    assert "immutable" in site.get("/assets/app-123.js").headers["cache-control"]
    assert site.head("/").status_code == 200
    assert site.get("/api/health").json() == {"ready": True}


@pytest.mark.parametrize(
    "path",
    [
        "/api",
        "/api/missing",
        "/metrics",
        "/metrics/missing",
        "/assets/missing.js",
        "/missing.js",
        "/%2e%2e/private",
    ],
)
def test_missing_resources_never_become_spa(site: TestClient, path: str) -> None:
    """Unknown APIs, assets, and traversal must retain a real 404."""
    assert site.get(path, headers={"Accept": "text/html"}).status_code == 404


def test_non_navigation_and_mutations(site: TestClient) -> None:
    """Do not mask unsupported methods or non-browser requests with entry HTML."""
    assert (
        site.get("/missing", headers={"Accept": "application/json"}).status_code == 404
    )
    assert site.post("/dashboard").status_code == 405
