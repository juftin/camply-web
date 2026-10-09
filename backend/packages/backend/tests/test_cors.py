"""
CORS and Tailscale origin tests for FastAPI backend.
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
    ],
)
def test_cors_allowed_origins(test_client: TestClient, origin: str) -> None:
    """
    Test that allowed origins (localhost, 0.0.0.0, Tailscale IPs and ts.net) receive CORS headers.

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


def test_cors_disallowed_origin(test_client: TestClient) -> None:
    """
    Test that unknown, untrusted external origins do not receive CORS allow headers.

    Parameters
    ----------
    test_client : TestClient
        FastAPI test client fixture.
    """
    response = test_client.options(
        "/api/health",
        headers={
            "Origin": "https://unauthorized-domain.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") is None
