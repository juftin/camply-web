"""Python hosting must preserve API errors and the frontend asset boundary."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from camply.server.static import attach_frontend


@pytest.fixture
def site(tmp_path: Path) -> TestClient:
    """Host a synthetic build after a real API route."""
    (tmp_path / "index.html").write_text("<html>synthetic app</html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/app-123.js").write_text("export {}")
    (tmp_path / "docs/guide").mkdir(parents=True)
    (tmp_path / "docs/index.html").write_text("<html>camply documentation</html>")
    (tmp_path / "docs/guide/index.html").write_text("<html>installation guide</html>")
    (tmp_path / "docs/search.json").write_text('{"docs": []}')
    app = FastAPI(docs_url="/api/docs", redoc_url="/api/redoc")

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


def test_documentation_directory_pages_and_assets(site: TestClient) -> None:
    """Documentation redirects to directory URLs and serves its own HTML."""
    redirect = site.get("/docs", follow_redirects=False)
    assert redirect.status_code in {301, 307}
    assert redirect.headers["location"].endswith("/docs/")
    assert site.get("/docs/").text == "<html>camply documentation</html>"
    assert site.get("/docs/guide/").text == "<html>installation guide</html>"
    assert site.get("/docs/search.json").json() == {"docs": []}
    assert site.head("/docs/").status_code == 200


@pytest.mark.parametrize("path", ["/docs/missing/", "/docs/missing.js"])
def test_missing_documentation_never_becomes_spa(site: TestClient, path: str) -> None:
    """Unknown docs URLs remain 404s for ordinary browser requests."""
    assert site.get(path, headers={"Accept": "text/html"}).status_code == 404
