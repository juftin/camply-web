"""
merge ntfy and ReserveAmerica histories

Revision ID: f024d1e2f3a4
Revises: f024c1d2e3f4, f42d8b10c6aa
Create Date: 2026-11-13 03:48:42.857577+00:00
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "f024d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = ("f024c1d2e3f4", "f42d8b10c6aa")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Join ntfy settings and ReserveAmerica provider upgrade paths."""
    pass


def downgrade() -> None:
    """Keep both preceding branch revisions available without changing data."""
    pass
