"""
User profile router — ``/api/me`` endpoints.
"""

from __future__ import annotations

import datetime as dt

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from camply.db.models import User as UserDB
from camply.db.notification_config import ntfy_config
from camply.notifications.base import NotificationDTO
from camply.notifications.ntfy import NtfyProvider
from camply.notifications.pushover import PushoverProvider
from camply.server.auth import (
    CurrentUserDep,
    require_invitation,
    require_password_not_expired,
)
from camply.server.dependencies import SessionDep
from camply.server.schemas import MeResponse, MeUpdateRequest, NotificationTestResponse

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

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if "ntfy_topic" not in str(exc.orig):
            raise
        raise HTTPException(
            status_code=409,
            detail="That ntfy topic is already in use. Choose another topic.",
        ) from exc
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


@me_router.post(
    "/me/notifications/test",
    dependencies=[Depends(require_invitation), Depends(require_password_not_expired)],
)
async def test_notification(
    body: MeUpdateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> NotificationTestResponse:
    """Send one test using current form values without persisting preferences."""
    if not current_user.scanning_enabled:
        raise HTTPException(
            status_code=403, detail="Notifications are disabled for this account."
        )
    settings = MeUpdateRequest.model_validate(
        {
            "notification_provider": current_user.notification_provider,
            "pushover_token": current_user.pushover_token,
            "ntfy_server_url": current_user.ntfy_server_url,
            "ntfy_access_token": current_user.ntfy_access_token,
            **(
                {"ntfy_topic": current_user.ntfy_topic}
                if current_user.ntfy_topic
                else {}
            ),
            **body.model_dump(exclude_unset=True),
        }
    )
    topic = settings.ntfy_topic or f"camply-{str(current_user.id)[:7]}"
    if settings.notification_provider == "ntfy":
        claimed = await session.scalar(
            select(UserDB.id).where(
                UserDB.ntfy_topic == topic, UserDB.id != current_user.id
            )
        )
        await session.rollback()
        if claimed is not None:
            raise HTTPException(
                status_code=409,
                detail="That ntfy topic is already in use. Choose another topic.",
            )
    else:
        if not settings.pushover_token:
            raise HTTPException(
                status_code=400, detail="Enter a Pushover user key before testing."
            )
        if not PushoverProvider.config.app_token:
            raise HTTPException(
                status_code=503, detail="Pushover is not configured on this server."
            )

    today = dt.datetime.now(dt.timezone.utc).date()
    payload = NotificationDTO(
        title="Camply test notification",
        message="Your Camply notifications are working.",
        booking_url="",
        url_title="Open Camply",
        park_name="Notification test",
        campsite_name="Test",
        start_date=today,
        end_date=today + dt.timedelta(days=1),
    )
    try:
        if settings.notification_provider == "ntfy":
            accepted = await NtfyProvider().send_accepted(
                {
                    "topic": topic,
                    "server_url": ntfy_config.publish_server(settings.ntfy_server_url),
                    "access_token": settings.ntfy_access_token,
                },
                payload,
            )
        else:
            accepted = await PushoverProvider().send_accepted(
                str(settings.pushover_token), payload
            )
        if accepted is not True:
            raise ValueError("Provider did not accept the test message")
    except Exception as exc:
        logger.warning(
            "Test notification failed",
            user_id=str(current_user.id),
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail="Could not send the test notification. Check the selected provider settings and try again.",
        ) from None
    return NotificationTestResponse(provider=settings.notification_provider)
