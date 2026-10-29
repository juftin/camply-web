"""
merge admin_ui and usedirect providers

Revision ID: ed55b53b0cda
Revises: 8a1b2c3d4e5f, ea6111bf3bed
Create Date: 2026-10-13 04:34:58.114908+00:00
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "ed55b53b0cda"
down_revision: Union[str, Sequence[str], None] = ("8a1b2c3d4e5f", "ea6111bf3bed")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.
    """
    pass


def downgrade() -> None:
    """
    Downgrade schema.
    """
    pass
