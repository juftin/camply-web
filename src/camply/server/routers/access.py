"""
Access request router — ``/api/request-access`` endpoint.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from camply.db.models import AccessRequest, User
from camply.db.notification_config import ntfy_config
from camply.notifications.base import NotificationDTO
from camply.notifications.ntfy import NtfyProvider
from camply.notifications.pushover import PushoverProvider
from camply.server.dependencies import SessionDep
from camply.server.metrics import ACCESS_REQUESTS_TOTAL
from camply.server.schemas import AccessRequestCreate, AccessRequestResponse

logger = structlog.getLogger(__name__)

access_router = APIRouter(tags=["access"])


async def _load_admin_notification_targets(
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """
    Collect plain notification target configs for eligible administrators.

    Parameters
    ----------
    session : AsyncSession
        Active database session.

    Returns
    -------
    list[dict[str, Any]]
        Serializable per-admin target dictionaries ready for background delivery.
    """
    result = await session.execute(
        select(User).where(
            User.is_admin.is_(True),
            User.scanning_enabled.is_(True),
        )
    )
    admins = result.scalars().all()
    targets: list[dict[str, Any]] = []
    has_pushover_app_token = bool(PushoverProvider.config.app_token)
    for admin in admins:
        if admin.notification_provider == "ntfy":
            if admin.ntfy_topic and admin.ntfy_topic.strip():
                targets.append(
                    {
                        "provider": "ntfy",
                        "user_id": str(admin.id),
                        "config": {
                            "topic": admin.ntfy_topic,
                            "server_url": ntfy_config.publish_server(
                                admin.ntfy_server_url
                            ),
                            "access_token": admin.ntfy_access_token,
                        },
                    }
                )
        elif (
            admin.notification_provider == "pushover"
            and admin.pushover_token
            and has_pushover_app_token
        ):
            targets.append(
                {
                    "provider": "pushover",
                    "user_id": str(admin.id),
                    "pushover_token": admin.pushover_token,
                }
            )
    return targets


def _build_access_request_notification(email: str, name: str | None) -> NotificationDTO:
    """
    Build the admin notification payload for a newly persisted access request.

    Parameters
    ----------
    email : str
        Normalized requester email address.
    name : str or None
        Optional requester name.

    Returns
    -------
    NotificationDTO
        Notification payload describing the new request.
    """
    today = dt.datetime.now(dt.timezone.utc).date()
    clean_name = name.strip() if name else ""
    requester = f"{clean_name} ({email})" if clean_name else email
    return NotificationDTO(
        title="New Camply access request",
        message=f"{requester} requested invitation access to Camply.",
        booking_url="",
        url_title="Open Camply",
        park_name="Access request",
        campsite_name=email,
        start_date=today,
        end_date=today + dt.timedelta(days=1),
    )


async def _notify_admins_of_access_request(
    targets: list[dict[str, Any]],
    payload: NotificationDTO,
) -> None:
    """
    Deliver best-effort admin alerts without failing requests or logging secrets.

    Parameters
    ----------
    targets : list[dict[str, Any]]
        Plain target dictionaries extracted from eligible admin records.
    payload : NotificationDTO
        Notification payload to send to each configured admin.
    """
    ntfy_provider = NtfyProvider()
    pushover_provider = PushoverProvider()
    for target in targets:
        provider_name = str(target["provider"])
        user_id = str(target["user_id"])
        try:
            if provider_name == "ntfy":
                accepted = await ntfy_provider.send_accepted(target["config"], payload)
            else:
                accepted = await pushover_provider.send_accepted(
                    target["pushover_token"], payload
                )
            if accepted is not True:
                logger.warning(
                    "Admin access request notification was not accepted",
                    admin_user_id=user_id,
                    provider=provider_name,
                )
        except Exception as exc:
            logger.warning(
                "Admin access request notification failed",
                admin_user_id=user_id,
                provider=provider_name,
                error_type=type(exc).__name__,
            )


@access_router.post("/request-access", status_code=status.HTTP_201_CREATED)
async def request_access(
    body: AccessRequestCreate,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> AccessRequestResponse:
    """Submit an invitation request.

    Duplicate emails are silently accepted (idempotent).
    """
    access_req = AccessRequest(email=body.email, name=body.name)
    normalized_email = access_req.email
    session.add(access_req)
    created = False
    try:
        await session.commit()
        ACCESS_REQUESTS_TOTAL.inc()
        created = True
    except IntegrityError:
        await session.rollback()
        logger.info("Duplicate access request ignored", email=body.email)

    if created:
        try:
            targets = await _load_admin_notification_targets(session=session)
        except Exception as exc:
            logger.warning(
                "Failed to load admin notification targets",
                error_type=type(exc).__name__,
            )
        else:
            if targets:
                payload = _build_access_request_notification(
                    email=normalized_email,
                    name=body.name,
                )
                background_tasks.add_task(
                    _notify_admins_of_access_request,
                    targets=targets,
                    payload=payload,
                )

    logger.info("Invitation requested", email=body.email, name=body.name)
    return AccessRequestResponse(
        message="Thank you! Your invitation request has been received."
    )
