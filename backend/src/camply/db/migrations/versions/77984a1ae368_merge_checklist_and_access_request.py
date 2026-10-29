"""
merge_checklist_and_access_request

Revision ID: 77984a1ae368
Revises: 36b6b307eef5, abc123access
Create Date: 2026-06-08 04:12:00.953725+00:00
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "77984a1ae368"
down_revision: Union[str, Sequence[str], None] = ("36b6b307eef5", "abc123access")
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
