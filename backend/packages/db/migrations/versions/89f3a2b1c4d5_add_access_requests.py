# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""Add access_requests table for early access requests

Revision ID: 89f3a2b1c4d5
Revises: 36b6b307eef5
Create Date: 2026-06-06 23:45:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "89f3a2b1c4d5"
down_revision: Union[str, None] = "36b6b307eef5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "access_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.CURRENT_TIMESTAMP(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_access_requests_email"), "access_requests", ["email"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_access_requests_email"), table_name="access_requests")
    op.drop_table("access_requests")
