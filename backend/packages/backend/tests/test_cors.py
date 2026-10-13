"""
CORS origin tests for local, Tailscale, and Cloudflare Pages frontends.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://0.0.0.0:5173",
        "http://100.85.12.34:5173",
        "https://my-macbook.ts.net",
        "http://camply-server.tailnet-xyz.ts.net:5173",
        "https://camply.juftin.dev",
        "https://camply-81r.pages.dev",
        "https://da37cb45.camply-81r.pages.dev",
        "https://feature-branch.camply-81r.pages.dev",
    ],
)
def test_cors_allowed_origins(test_client: TestClient, origin: str) -> None:
    """
    Test that trusted local, Tailscale, and Pages origins receive CORS headers.

    Parameters
    ----------
    test_client : TestClient
        FastAPI test client fixture.
    origin : str
        The origin string to test.
    """
    response = test_client.options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin


@pytest.mark.parametrize(
    "origin",
    [
        "https://unauthorized-domain.com",
        "https://other-project.pages.dev",
        "https://da37cb45.other-project.pages.dev",
        "http://da37cb45.camply-81r.pages.dev",
        "https://da37cb45.camply-81r.pages.dev.evil.example",
        "https://da37cb45.evilcamply-81r.pages.dev",
        "https://nested.da37cb45.camply-81r.pages.dev",
    ],
)
def test_cors_disallowed_origin(test_client: TestClient, origin: str) -> None:
    """
    Test that unknown, untrusted external origins do not receive CORS allow headers.

    Parameters
    ----------
    test_client : TestClient
        FastAPI test client fixture.
    origin : str
        The untrusted origin to reject.
    """
    response = test_client.options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") is None
