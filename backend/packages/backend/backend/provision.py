"""
Provision Administrator CLI

Used to grant admin privileges to an existing user by their database UUID.
Particularly useful for bootstrapping Auth0 administrators.
"""

from __future__ import annotations

import asyncio
import sys
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.config import db
from db.models import User


async def provision_admin(
    user_id_str: str, session: AsyncSession | None = None
) -> None:
    """
    Grant administrator status to the user identified by user_id_str.
    """
    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        print(f"Error: Invalid UUID string: {user_id_str}", file=sys.stderr)
        sys.exit(1)

    async def _update(sess: AsyncSession) -> None:
        result = await sess.execute(select(User).where(User.id == user_uuid))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"Error: User with ID {user_uuid} not found.", file=sys.stderr)
            sys.exit(1)

        user.is_admin = True
        await sess.commit()
        print(f"Successfully provisioned admin privileges for {user.email} ({user.id})")

    if session is not None:
        await _update(session)
    else:
        async with db.get_session() as sess:
            await _update(sess)


REQUIRED_ARG_COUNT = 2


def main() -> None:
    """CLI entrypoint."""
    if len(sys.argv) < REQUIRED_ARG_COUNT:
        print("Usage: python -m backend.provision <user_uuid>", file=sys.stderr)
        sys.exit(1)

    asyncio.run(provision_admin(sys.argv[1]))


if __name__ == "__main__":
    main()
