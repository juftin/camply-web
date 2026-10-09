"""
admin_ui

Revision ID: 8a1b2c3d4e5f
Revises: 77984a1ae368
Create Date: 2026-10-08 23:55:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "77984a1ae368"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: add admin and scanning flags to users and create admin_audit_events.
    """
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "scanning_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.create_table(
        "admin_audit_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.UUID(), nullable=False),
        sa.Column("prev_value", sa.Boolean(), nullable=True),
        sa.Column("new_value", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_audit_events_actor_id"),
        "admin_audit_events",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_audit_events_subject_id"),
        "admin_audit_events",
        ["subject_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_audit_events_created_at"),
        "admin_audit_events",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """
    Downgrade schema: drop admin_audit_events and user columns.
    """
    op.drop_index(
        op.f("ix_admin_audit_events_created_at"),
        table_name="admin_audit_events",
    )
    op.drop_index(
        op.f("ix_admin_audit_events_subject_id"),
        table_name="admin_audit_events",
    )
    op.drop_index(
        op.f("ix_admin_audit_events_actor_id"),
        table_name="admin_audit_events",
    )
    op.drop_table("admin_audit_events")
    op.drop_column("users", "scanning_enabled")
    op.drop_column("users", "is_admin")
