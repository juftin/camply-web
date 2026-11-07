"""Add per-user ntfy settings and independent outbox delivery channels."""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "f024a1b2c3d4"
down_revision = "c2f84b9d1a3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Assign unpredictable topics to existing accounts without enabling delivery."""
    op.add_column(
        "users",
        sa.Column("ntfy_topic", sa.String(64), nullable=False, server_default=""),
    )
    op.add_column(
        "users",
        sa.Column(
            "notification_provider",
            sa.String(16),
            nullable=False,
            server_default="pushover",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "ntfy_server_url",
            sa.String(2048),
            nullable=True,
        ),
    )
    op.add_column(
        "users", sa.Column("ntfy_access_token", sa.String(1024), nullable=True)
    )
    users = sa.table(
        "users", sa.column("id", sa.Uuid()), sa.column("ntfy_topic", sa.String())
    )
    connection = op.get_bind()
    for user_id in connection.execute(sa.select(users.c.id)).scalars().all():
        connection.execute(
            users.update()
            .where(users.c.id == user_id)
            .values(ntfy_topic=f"camply-{uuid.uuid4().hex}")
        )
    op.create_index("ix_users_ntfy_topic", "users", ["ntfy_topic"], unique=True)
    op.add_column(
        "notification_outbox",
        sa.Column("channel", sa.String(16), nullable=False, server_default="pushover"),
    )


def downgrade() -> None:
    """Remove ntfy settings and pending ntfy intents."""
    op.execute(sa.text("DELETE FROM notification_outbox WHERE channel = 'ntfy'"))
    op.drop_column("notification_outbox", "channel")
    op.drop_index("ix_users_ntfy_topic", table_name="users")
    for name in (
        "ntfy_topic",
        "notification_provider",
        "ntfy_server_url",
        "ntfy_access_token",
    ):
        op.drop_column("users", name)
