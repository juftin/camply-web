"""
seed verified UseDirect providers

Revision ID: ea6111bf3bed
Revises: 9b94e557767a
Create Date: 2026-10-13 03:58:59.111906+00:00

Attributes
----------
_PROVIDERS : tuple
    Immutable provider IDs, names, descriptions, and public booking endpoints.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ea6111bf3bed"
down_revision: Union[str, Sequence[str], None] = "9b94e557767a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PROVIDERS = (
    (
        3,
        "Florida State Parks",
        "Florida State Parks campsite reservations.",
        "https://reserve.floridastateparks.org/Web",
    ),
    (
        4,
        "Virginia State Parks",
        "Virginia State Parks campsite reservations.",
        "https://reservevaparks.com/Web",
    ),
    (
        5,
        "Minnesota State Parks",
        "Minnesota State Parks campsite reservations.",
        "https://reservemn.usedirect.com/MinnesotaWeb",
    ),
    (
        6,
        "Ohio State Parks",
        "Ohio State Parks campsite reservations.",
        "https://reserveohio.com/OhioCampWeb",
    ),
    (
        7,
        "Arizona State Parks",
        "Arizona State Parks campsite reservations.",
        "https://azstateparks.com/reserve",
    ),
    (
        8,
        "Missouri State Parks",
        "Missouri State Parks campsite reservations.",
        "https://icampmo.usedirect.com/MSPWeb",
    ),
    (
        9,
        "Fairfax County Parks",
        "Fairfax County Parks campsite reservations.",
        "https://fairfax.usedirect.com/FairfaxFCPAWeb",
    ),
    (
        10,
        "Oregon Metro",
        "Oregon Metro regional park campsite reservations.",
        "https://reservemetro.usedirect.com/MetroWeb",
    ),
    (
        11,
        "Northern Territory",
        "Australian Northern Territory park campsite reservations.",
        "https://parkbookings.nt.gov.au/Web",
    ),
)


def upgrade() -> None:
    """Seed verified deployments under permanent provider IDs."""
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
                "id": provider_id,
                "name": name,
                "description": description,
                "url": url,
                "enabled": True,
            }
            for provider_id, name, description, url in _PROVIDERS
        ],
    )


def downgrade() -> None:
    """Remove only unused seeds, preserving dependent data on every database."""
    provider_ids = [row[0] for row in _PROVIDERS]
    connection = op.get_bind()
    for name in ("campgrounds", "recreation_areas", "unique_targets", "search"):
        table = sa.table(name, sa.column("provider_id", sa.Integer()))
        references = connection.execute(
            sa.select(table.c.provider_id)
            .where(table.c.provider_id.in_(provider_ids))
            .limit(1)
        )
        if references.first() is not None:
            raise RuntimeError(
                "UseDirect providers have dependent data; keep the provider seeds until that data is handled explicitly"
            )
    providers = sa.table("providers", sa.column("id", sa.Integer()))
    op.execute(providers.delete().where(providers.c.id.in_(provider_ids)))
