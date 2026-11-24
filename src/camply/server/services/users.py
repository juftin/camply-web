"""Persist new accounts without letting generated topic collisions block signup."""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from camply.db.models import User


async def flush_new_user(session: AsyncSession, user: User) -> None:
    """Insert a new account, retrying only collisions of its generated ntfy topic.

    Call before adding related records: a failed insert rolls back the transaction.
    The caller retains responsibility for committing the account and audit records.
    Explicit topics and unrelated uniqueness failures are never rewritten.
    """
    max_attempts = 3
    default_topic = f"camply-{str(user.id)[:7]}"
    generated_topic = user.ntfy_topic == default_topic
    for attempt in range(max_attempts):
        session.add(user)
        try:
            await session.flush()
            return
        except IntegrityError as exc:
            await session.rollback()
            if (
                not generated_topic
                or "ntfy_topic" not in str(exc.orig)
                or attempt + 1 == max_attempts
            ):
                raise
            user.ntfy_topic = f"{default_topic}-{uuid.uuid4().hex}"
