"""
'user password credentials'

Revision ID: 36dbff1f679f
Revises: ed55b53b0cda
Create Date: 2026-10-13 13:45:14.944298+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "36dbff1f679f"
down_revision: Union[str, Sequence[str], None] = "ed55b53b0cda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: add password_hash and must_change_password to users.
    """
    op.add_column(
        "users", sa.Column("password_hash", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """
    Downgrade schema: drop password_hash and must_change_password from users.
    """
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "password_hash")
