"""Add optional per-subscriber booking weekdays without changing shared targets."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e818084258e6"
"""Add saved night-of-week selection."""
down_revision: str | None = "d027a1b2c3d4"
"""Previous shared migration head."""
branch_labels: str | Sequence[str] | None = None
"""No additional migration branch."""
depends_on: str | Sequence[str] | None = None
"""No external revision dependencies."""


def upgrade() -> None:
    """Leave existing scans unrestricted while allowing saved weekday selections."""
    op.add_column("user_scans", sa.Column("allowed_weekdays", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove only the night preference, retaining subscriptions and other filters."""
    op.drop_column("user_scans", "allowed_weekdays")
