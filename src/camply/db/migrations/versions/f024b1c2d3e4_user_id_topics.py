"""Use user ID prefixes for generated ntfy topics, preserving edited topics."""

import re

import sqlalchemy as sa
from alembic import op

revision = "f024b1c2d3e4"
down_revision = "f024a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace generated defaults where the ID prefix is not already claimed."""
    users = sa.table(
        "users", sa.column("id", sa.Uuid()), sa.column("ntfy_topic", sa.String())
    )
    connection = op.get_bind()
    rows = connection.execute(sa.select(users.c.id, users.c.ntfy_topic)).all()
    occupied = {topic for _, topic in rows}
    for user_id, topic in rows:
        candidate = str(user_id)[:7]
        if re.fullmatch(r"camply-[0-9a-f]{32}", topic) and candidate not in occupied:
            connection.execute(
                users.update().where(users.c.id == user_id).values(ntfy_topic=candidate)
            )
            occupied.discard(topic)
            occupied.add(candidate)


def downgrade() -> None:
    """Retain saved subscription topics to avoid silently changing subscriptions."""
