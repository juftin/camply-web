"""
User profile router — ``/api/me`` endpoints.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from camply.db.models import User as UserDB
from camply.server.auth import CurrentUserDep
from camply.server.dependencies import SessionDep
from camply.server.schemas import MeResponse, MeUpdateRequest

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
        is_invited=current_user.is_invited,
        is_admin=current_user.is_admin,
        scanning_enabled=current_user.scanning_enabled,
        pushover_token=current_user.pushover_token,
        must_change_password=current_user.must_change_password,
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
    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ERR_PASSWORD_CHANGE_REQUIRED",
                "message": "Password change required before proceeding.",
            },
        )

    result = await session.execute(select(UserDB).where(UserDB.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.pushover_token = body.pushover_token or None

    await session.commit()
    await session.refresh(user)

    return MeResponse(
        id=user.id,
        email=user.email,
        is_invited=user.is_invited,
        is_admin=user.is_admin,
        scanning_enabled=user.scanning_enabled,
        pushover_token=user.pushover_token,
        must_change_password=user.must_change_password,
    )
