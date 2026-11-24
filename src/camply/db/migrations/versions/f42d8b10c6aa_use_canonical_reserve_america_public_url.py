"""Use ReserveAmerica's canonical public website for the registered provider.

Revision ID: f42d8b10c6aa
Revises: ab24e9f10d13

Attributes
----------
_PROVIDER_ID : int
    ReserveAmerica's permanent identity in the provider registry.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f42d8b10c6aa"
down_revision: str | Sequence[str] | None = "ab24e9f10d13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PROVIDER_ID = 13


def _replace_url(old: str, new: str) -> None:
    """Correct the seeded URL without replacing other providers or custom URLs."""
    providers = sa.table(
        "providers", sa.column("id", sa.Integer()), sa.column("url", sa.String())
    )
    op.execute(
        providers.update()
        .where(providers.c.id == _PROVIDER_ID, providers.c.url == old)
        .values(url=new)
    )


def upgrade() -> None:
    """Move public navigation off the API/session host for existing installations."""
    _replace_url("https://a1.reserveamerica.com", "https://www.reserveamerica.com")


def downgrade() -> None:
    """Restore the original seed URL when rolling back this correction."""
    _replace_url("https://www.reserveamerica.com", "https://a1.reserveamerica.com")
