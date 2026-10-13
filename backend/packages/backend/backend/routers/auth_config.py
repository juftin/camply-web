"""
Public config router — ``/api/auth-config``.

Exposes non-sensitive configuration so the frontend can determine
whether to render in-app password login, Auth0, or automatic login.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import AuthMode, backend_config

auth_config_router = APIRouter(tags=["config"])


class AuthConfigResponse(BaseModel):
    """Public auth configuration exposed to the frontend."""

    auth_mode: AuthMode
    auth0_domain: str | None = None
    auth0_client_id: str | None = None
    auth0_audience: str | None = None
    invite_only: bool
    auto_login: bool
    signup_enabled: bool


@auth_config_router.get("/auth-config")
async def auth_config() -> AuthConfigResponse:
    """Return the current authentication mode and (if Auth0) the domain, client ID, audience, and login capabilities."""
    return AuthConfigResponse(
        auth_mode=backend_config.auth_mode,
        auth0_domain=backend_config.auth0_domain,
        auth0_client_id=backend_config.auth0_client_id,
        auth0_audience=backend_config.auth0_audience,
        invite_only=backend_config.invite_only,
        auto_login=backend_config.auto_login,
        signup_enabled=backend_config.signup_enabled,
    )
