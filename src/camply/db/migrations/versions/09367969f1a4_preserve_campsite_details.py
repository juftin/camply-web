"""
Preserve campsite details in availability snapshots.

Revision ID: 09367969f1a4
Revises: 2ac874f9d2ad
Create Date: 2026-10-25 13:05:34.209832+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "09367969f1a4"
down_revision: Union[str, Sequence[str], None] = "2ac874f9d2ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add provider site attributes; existing snapshots retain unknown values."""
    op.add_column(
        "scan_results",
        sa.Column(
            "campsite_name", sa.String(length=255), server_default="", nullable=False
        ),
    )
    op.add_column(
        "scan_results", sa.Column("campsite_type", sa.String(length=32), nullable=True)
    )
    op.add_column("scan_results", sa.Column("is_electric", sa.Boolean(), nullable=True))
    op.add_column(
        "scan_results", sa.Column("is_accessible", sa.Boolean(), nullable=True)
    )


def downgrade() -> None:
    """Remove site attributes without discarding availability snapshots."""
    op.drop_column("scan_results", "is_accessible")
    op.drop_column("scan_results", "is_electric")
    op.drop_column("scan_results", "campsite_type")
    op.drop_column("scan_results", "campsite_name")
