"""
User profile router — ``/api/me`` endpoints.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from camply.db.models import User as UserDB
from camply.db.notification_config import ntfy_config
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
        notification_provider=current_user.notification_provider,
        ntfy_default_subscription_url=(
            ntfy_config.subscription_url
            if ntfy_config.subscription_url != "https://ntfy.sh"
            else None
        ),
        ntfy_topic=current_user.ntfy_topic,
        ntfy_server_url=current_user.ntfy_server_url,
        ntfy_subscription_url=ntfy_config.subscription_server(
            current_user.ntfy_server_url
        ),
        ntfy_access_token=current_user.ntfy_access_token,
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

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, (value or None) if field == "pushover_token" else value)

    await session.commit()
    await session.refresh(user)

    return MeResponse(
        id=user.id,
        email=user.email,
        is_invited=user.is_invited,
        is_admin=user.is_admin,
        scanning_enabled=user.scanning_enabled,
        pushover_token=user.pushover_token,
        notification_provider=user.notification_provider,
        ntfy_default_subscription_url=(
            ntfy_config.subscription_url
            if ntfy_config.subscription_url != "https://ntfy.sh"
            else None
        ),
        ntfy_topic=user.ntfy_topic,
        ntfy_server_url=user.ntfy_server_url,
        ntfy_subscription_url=ntfy_config.subscription_server(user.ntfy_server_url),
        ntfy_access_token=user.ntfy_access_token,
        must_change_password=user.must_change_password,
    )
