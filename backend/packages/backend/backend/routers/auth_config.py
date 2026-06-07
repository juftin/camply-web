"""
Public config router — ``/api/auth-config``.

Exposes non-sensitive configuration so the frontend can determine
whether to render the Auth0 login flow or local-mode auto-login.
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


@auth_config_router.get("/auth-config")
async def auth_config() -> AuthConfigResponse:
    """Return the current authentication mode and (if Auth0) the domain / client ID."""
    return AuthConfigResponse(
        auth_mode=backend_config.auth_mode,
        auth0_domain=backend_config.auth0_domain,
        auth0_client_id=backend_config.auth0_client_id,
    )
