"""
seed Washington State Parks GoingToCamp provider

Revision ID: c2f84b9d1a3e
Revises: 4d64e0e4ae18
Create Date: 2026-11-04 05:15:00.000000+00:00

Attributes
----------
_PROVIDER_ID : int
    Washington State Parks' permanent registry ID, fixed within this migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2f84b9d1a3e"
down_revision: str | Sequence[str] | None = "4d64e0e4ae18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PROVIDER_ID = 12


def upgrade() -> None:
    """Register Washington State Parks under its stable provider ID."""
    providers = sa.table(
        "providers",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("url", sa.String()),
        sa.column("enabled", sa.Boolean()),
    )
    op.bulk_insert(
        providers,
        [
            {
                "id": _PROVIDER_ID,
                "name": "Washington State Parks",
                "description": "Washington State Parks campsite reservations.",
                "url": "https://washington.goingtocamp.com",
                "enabled": True,
            }
        ],
    )


def downgrade() -> None:
    """Remove an unused seed without orphaning data on SQLite or PostgreSQL."""
    connection = op.get_bind()
    for name in ("campgrounds", "recreation_areas", "unique_targets", "search"):
        table = sa.table(name, sa.column("provider_id", sa.Integer()))
        references = connection.execute(
            sa.select(table.c.provider_id)
            .where(table.c.provider_id == _PROVIDER_ID)
            .limit(1)
        )
        if references.first() is not None:
            raise RuntimeError(
                "Washington State Parks has dependent data; keep the provider seed until that data is handled explicitly"
            )
    providers = sa.table("providers", sa.column("id", sa.Integer()))
    op.execute(providers.delete().where(providers.c.id == _PROVIDER_ID))
