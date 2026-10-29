"""Shared async notification lookup and delivery, independent of task transports."""

import uuid as uuid_mod
from collections.abc import Callable
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from camply.db.models import User, UserScan
from camply.worker.notifications.base import NotificationDTO
from camply.worker.notifications.pushover import PushoverProvider

logger = structlog.getLogger(__name__)


async def send_notification(
    user_id: str,
    notification: dict,
    scan_id: Optional[str] = None,
    *,
    sessions: Callable[[], AsyncSession],
    provider_factory: Callable[[], PushoverProvider] = PushoverProvider,
) -> dict:
    """
    Async implementation of Pushover notification delivery.
    """
    user_uuid = uuid_mod.UUID(user_id)

    async with sessions() as session:
        stmt = select(User).where(User.id == user_uuid)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            logger.warning("User not found", user_id=user_id)
            return {"status": "error", "reason": "user_not_found"}

        if not user.scanning_enabled:
            logger.info(
                "User scanning disabled, skipping notification", user_id=user_id
            )
            return {"status": "skipped", "reason": "user_suspended"}

        if scan_id is not None:
            scan_uuid = uuid_mod.UUID(scan_id)
            scan_stmt = select(UserScan).where(UserScan.id == scan_uuid)
            scan_res = await session.execute(scan_stmt)
            scan = scan_res.scalar_one_or_none()
            if scan is None:
                logger.info("Scan not found, skipping notification", scan_id=scan_id)
                return {"status": "skipped", "reason": "scan_not_found"}
            if scan.user_id != user_uuid:
                logger.error("Scan owner mismatch", scan_id=scan_id, user_id=user_id)
                return {"status": "error", "reason": "scan_owner_mismatch"}
            if not scan.is_active:
                logger.info("Scan inactive, skipping notification", scan_id=scan_id)
                return {"status": "skipped", "reason": "scan_inactive"}

        if not user.pushover_token:
            logger.info(
                "User has no pushover_token, skipping",
                user_id=user_id,
            )
            return {"status": "skipped", "reason": "no_pushover_token"}

        pushover_token = user.pushover_token

    # Reconstruct NotificationDTO from dict
    try:
        payload = NotificationDTO.model_validate(notification)
    except Exception as exc:
        logger.error(
            "Invalid notification DTO",
            user_id=str(user_id),
            error=str(exc),
        )
        return {"status": "error", "reason": str(exc)}

    provider = provider_factory()
    try:
        await provider.send_alert(
            user_config={"user_key": pushover_token},
            payload=payload,
        )
        return {
            "status": "success",
            "provider_name": "Recreation.gov",
            "search_name": payload.park_name or "Campsite Alert",
            "search_dates": (
                f"{payload.start_date.isoformat()} → {payload.end_date.isoformat()}"
                if payload.start_date and payload.end_date
                else None
            ),
        }
    except Exception as exc:
        logger.error(
            "Pushover notification failed",
            user_id=str(user_id),
            error=str(exc),
        )
        raise
