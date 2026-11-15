"""
Add access request review metadata

Revision ID: b9a4958c2f7c
Revises: e818084258e6
Create Date: 2026-11-15 11:41:46.845909+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9a4958c2f7c"
down_revision: Union[str, Sequence[str], None] = "e818084258e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: add requester name, review metadata, and user links.

    Existing rows keep their status; ``updated_at`` defaults to the migration
    time. Batch mode lets SQLite rebuild the table for the foreign keys while
    PostgreSQL applies plain ``ALTER TABLE`` statements.
    """
    with op.batch_alter_table("access_requests") as batch_op:
        batch_op.add_column(sa.Column("name", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.CURRENT_TIMESTAMP(),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("reviewed_by_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_access_requests_reviewed_by_id_users",
            "users",
            ["reviewed_by_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_access_requests_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """
    Downgrade schema: drop review metadata, user links, and requester name.
    """
    with op.batch_alter_table("access_requests") as batch_op:
        batch_op.drop_constraint("fk_access_requests_user_id_users", type_="foreignkey")
        batch_op.drop_constraint(
            "fk_access_requests_reviewed_by_id_users", type_="foreignkey"
        )
        batch_op.drop_column("user_id")
        batch_op.drop_column("reviewed_by_id")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("name")
