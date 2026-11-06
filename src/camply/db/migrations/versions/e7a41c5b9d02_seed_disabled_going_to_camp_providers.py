"""
seed disabled GoingToCamp providers

Revision ID: e7a41c5b9d02
Revises: c2f84b9d1a3e
Create Date: 2026-11-06 07:00:00.000000+00:00

Attributes
----------
_PROVIDERS : tuple
    Immutable provider IDs, names, descriptions, and public booking roots.
    Every row is seeded disabled because the deployments' public APIs sit behind
    bot challenges that prevented verification; a later migration enables each
    one after its endpoints are verified.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a41c5b9d02"
down_revision: str | Sequence[str] | None = "c2f84b9d1a3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PROVIDERS = (
    (
        13,
        "Wisconsin State Parks",
        "Wisconsin State Parks campsite reservations.",
        "https://wisconsin.goingtocamp.com",
    ),
    (
        14,
        "Michigan State Parks",
        "Michigan Department of Natural Resources campsite reservations.",
        "https://midnrreservations.com",
    ),
    (
        15,
        "Tacoma Power Parks",
        "Tacoma Power Parks campsite reservations.",
        "https://tacomapower.goingtocamp.com",
    ),
    (
        16,
        "Parks Canada",
        "Parks Canada campsite reservations.",
        "https://reservation.pc.gc.ca",
    ),
    (
        17,
        "BC Parks",
        "BC Parks campsite reservations.",
        "https://camping.bcparks.ca",
    ),
    (
        18,
        "Ontario Parks",
        "Ontario Parks campsite reservations.",
        "https://reservations.ontarioparks.ca",
    ),
    (
        19,
        "Nova Scotia Parks",
        "Nova Scotia Provincial Parks campsite reservations.",
        "https://novascotia.goingtocamp.com",
    ),
    (
        20,
        "Manitoba Parks",
        "Manitoba Provincial Parks campsite reservations.",
        "https://manitoba.goingtocamp.com",
    ),
    (
        21,
        "Newfoundland & Labrador Provincial Parks",
        "Newfoundland and Labrador Provincial Parks campsite reservations.",
        "https://nlcamping.ca",
    ),
    (
        22,
        "Gatineau Park (NCC)",
        "National Capital Commission Gatineau Park campsite reservations.",
        "https://reservations.ncc-ccn.gc.ca",
    ),
    (
        23,
        "Long Point Region Conservation Authority",
        "Long Point Region Conservation Authority campsite reservations.",
        "https://longpoint.goingtocamp.com",
    ),
    (
        24,
        "Maitland Valley Conservation Authority",
        "Maitland Valley Conservation Authority campsite reservations.",
        "https://maitlandvalley.goingtocamp.com",
    ),
    (
        25,
        "St. Clair Region Conservation Authority",
        "St. Clair Region Conservation Authority campsite reservations.",
        "https://stclair.goingtocamp.com",
    ),
)


def upgrade() -> None:
    """Register unverified GoingToCamp deployments as disabled providers."""
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
                "enabled": False,
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
                "GoingToCamp providers have dependent data; keep the provider seeds until that data is handled explicitly"
            )
    providers = sa.table("providers", sa.column("id", sa.Integer()))
    op.execute(providers.delete().where(providers.c.id.in_(provider_ids)))
