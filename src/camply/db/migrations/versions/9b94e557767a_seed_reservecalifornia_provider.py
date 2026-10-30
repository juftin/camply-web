"""
seed ReserveCalifornia provider

Revision ID: 9b94e557767a
Revises: 77984a1ae368
Create Date: 2026-10-13 01:23:50.502169+00:00

Attributes
----------
_PROVIDER_ID : int
    ReserveCalifornia's permanent registry ID, fixed within this migration.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b94e557767a"
down_revision: Union[str, Sequence[str], None] = "77984a1ae368"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PROVIDER_ID = 2


def upgrade() -> None:
    """Register ReserveCalifornia under its stable provider ID."""
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
                "name": "ReserveCalifornia",
                "description": "California State Parks campsite reservations.",
                "url": "https://www.reservecalifornia.com",
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
                "ReserveCalifornia has dependent data; keep the provider seed until that data is handled explicitly"
            )
    providers = sa.table("providers", sa.column("id", sa.Integer()))
    op.execute(providers.delete().where(providers.c.id == _PROVIDER_ID))
