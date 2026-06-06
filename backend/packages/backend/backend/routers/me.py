"""
User profile router — ``/api/me`` and ``/api/providers`` endpoints.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from backend.auth import CurrentUserDep
from backend.dependencies import SessionDep
from backend.schemas import MeResponse, MeUpdateRequest, ProviderResponse
from db.models import Provider as ProviderDB
from db.models import User as UserDB

logger = structlog.getLogger(__name__)

me_router = APIRouter(tags=["me"])
provider_list_router = APIRouter(tags=["providers"])


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------


@me_router.get("/me")
async def get_me(current_user: CurrentUserDep) -> MeResponse:
    """Return the authenticated user's profile."""
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        is_early_access_user=current_user.is_early_access_user,
        pushover_token=current_user.pushover_token,
    )


# ---------------------------------------------------------------------------
# PATCH  /me
# ---------------------------------------------------------------------------


@me_router.patch("/me")
async def update_me(
    body: MeUpdateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> MeResponse:
    """Update the authenticated user's profile (pushover_token, …)."""
    result = await session.execute(
        select(UserDB).where(UserDB.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.pushover_token = body.pushover_token

    await session.commit()
    await session.refresh(user)

    return MeResponse(
        id=user.id,
        email=user.email,
        is_early_access_user=user.is_early_access_user,
        pushover_token=user.pushover_token,
    )


# ---------------------------------------------------------------------------
# GET /providers
# ---------------------------------------------------------------------------


@provider_list_router.get("/providers")
async def list_providers_api(session: SessionDep) -> list[ProviderResponse]:
    """List all supported providers."""
    result = await session.execute(select(ProviderDB))
    providers = result.scalars().all()
    return [
        ProviderResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            url=p.url,
            enabled=p.enabled,
        )
        for p in providers
    ]
