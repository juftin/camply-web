"""
merge standalone delivery with current availability schema

Revision ID: 4d64e0e4ae18
Revises: 09367969f1a4, ef2486672984
Create Date: 2026-10-28 00:25:21.668010
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d64e0e4ae18"
down_revision: Union[str, Sequence[str], None] = ("09367969f1a4", "ef2486672984")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge both upgrade paths and name delivery identities for summary/direct modes."""
    op.alter_column(
        "notification_outbox", "campsite_id", new_column_name="delivery_key"
    )


def downgrade() -> None:
    """Restore the original intent column without discarding pending alerts."""
    op.alter_column(
        "notification_outbox", "delivery_key", new_column_name="campsite_id"
    )
