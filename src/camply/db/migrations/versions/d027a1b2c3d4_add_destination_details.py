"""Add optional cached destination enrichment without changing catalog identities.

Revision ID: d027a1b2c3d4
Revises: f024d1e2f3a4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d027a1b2c3d4"
down_revision: str | Sequence[str] | None = "f024d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Leave existing destinations valid with absent enrichment."""
    for table in ("campgrounds", "recreation_areas"):
        op.add_column(
            table, sa.Column("details", sa.JSON(none_as_null=True), nullable=True)
        )
        op.add_column(
            table, sa.Column("details_attempted_at", sa.DateTime(), nullable=True)
        )


def downgrade() -> None:
    """Remove optional snapshots while preserving catalog data."""
    for table in ("campgrounds", "recreation_areas"):
        op.drop_column(table, "details_attempted_at")
        op.drop_column(table, "details")
