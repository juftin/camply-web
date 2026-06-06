# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
User profile router — ``/api/me`` endpoints.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from backend.auth import CurrentUserDep
from backend.dependencies import SessionDep
from backend.schemas import MeResponse, MeUpdateRequest
from db.models import User as UserDB

logger = structlog.getLogger(__name__)

me_router = APIRouter(tags=["me"])


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
    result = await session.execute(select(UserDB).where(UserDB.id == current_user.id))
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
