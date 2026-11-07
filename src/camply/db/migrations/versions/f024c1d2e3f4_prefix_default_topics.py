"""Prefix generated ntfy topics with camply-, preserving custom topic choices."""

import re

import sqlalchemy as sa
from alembic import op

revision = "f024c1d2e3f4"
down_revision = "f024b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename earlier generated defaults where the prefixed topic is unclaimed."""
    users = sa.table(
        "users", sa.column("id", sa.Uuid()), sa.column("ntfy_topic", sa.String())
    )
    connection = op.get_bind()
    rows = connection.execute(sa.select(users.c.id, users.c.ntfy_topic)).all()
    occupied = {topic for _, topic in rows}
    for user_id, topic in rows:
        suffix = str(user_id)[:7]
        candidate = f"camply-{suffix}"
        generated = topic == suffix or re.fullmatch(r"camply-[0-9a-f]{32}", topic)
        if generated and candidate not in occupied:
            connection.execute(
                users.update().where(users.c.id == user_id).values(ntfy_topic=candidate)
            )
            occupied.discard(topic)
            occupied.add(candidate)


def downgrade() -> None:
    """Preserve saved topics rather than invalidating subscriptions on downgrade."""
