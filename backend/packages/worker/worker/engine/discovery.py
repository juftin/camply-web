"""Shared due-target discovery with optional standalone date/invitation eligibility."""

import datetime
import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.eligibility import eligible_scan_condition
from db.models import UniqueTarget, User, UserScan


async def due_targets(
    *,
    sessions: Callable[[], AsyncSession],
    cooldown: int,
    limit: int | None = None,
    today: datetime.date | None = None,
    invite_only: bool = False,
    exclude: set[str] | None = None,
) -> list[UniqueTarget]:
    """Find current eligible shared targets without dispatching transport tasks."""
    from datetime import timezone

    now = datetime.datetime.now(tz=timezone.utc)
    cooldown_threshold = now - datetime.timedelta(seconds=cooldown)

    async with sessions() as session:
        # Find targets with eligible user scans that need checking
        stmt = (
            select(UniqueTarget)
            .join(UserScan, UserScan.target_id == UniqueTarget.id)
            .join(User, User.id == UserScan.user_id)
            .where(
                eligible_scan_condition(),
                (
                    (UniqueTarget.last_checked_at.is_(None))
                    | (UniqueTarget.last_checked_at < cooldown_threshold)
                ),
            )
            .distinct()
        )

        if today is not None:
            stmt = stmt.where(UniqueTarget.end_date > today)
        if invite_only:
            stmt = stmt.where(User.is_invited.is_(True))
        if exclude:
            stmt = stmt.where(
                UniqueTarget.id.not_in([uuid.UUID(value) for value in exclude])
            )
        if limit is not None:
            stmt = stmt.order_by(
                UniqueTarget.last_checked_at.asc(), UniqueTarget.id
            ).limit(limit)
        result = await session.execute(stmt)
        targets = result.scalars().all()

        return list(targets)
