"""
seed verified going to camp providers

Revision ID: 2d7ab29d3a46
Revises: d834b6f82260
Create Date: 2026-11-16 01:31:03.950710+00:00

Attributes
----------
_PROVIDERS : tuple
    Immutable provider IDs, names, descriptions, and public booking endpoints.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2d7ab29d3a46"
down_revision: str | Sequence[str] | None = "d834b6f82260"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PROVIDERS = (
    (
        14,
        "Wisconsin State Parks",
        "Wisconsin State Parks campsite reservations.",
        "https://wisconsin.goingtocamp.com",
    ),
    (
        15,
        "Michigan State Parks",
        "Michigan Department of Natural Resources campsite reservations.",
        "https://midnrreservations.com",
    ),
    (
        16,
        "Tacoma Power Parks",
        "Tacoma Power Parks campsite reservations.",
        "https://tacomapower.goingtocamp.com",
    ),
    (
        17,
        "Parks Canada",
        "Parks Canada campsite and backcountry reservations.",
        "https://reservation.pc.gc.ca",
    ),
    (
        18,
        "BC Parks",
        "British Columbia provincial parks campsite reservations.",
        "https://camping.bcparks.ca",
    ),
    (
        19,
        "Ontario Parks",
        "Ontario provincial parks campsite reservations.",
        "https://reservations.ontarioparks.ca",
    ),
    (
        20,
        "Nova Scotia Parks",
        "Nova Scotia provincial parks campsite reservations.",
        "https://novascotia.goingtocamp.com",
    ),
    (
        21,
        "Manitoba Parks",
        "Manitoba provincial parks campsite reservations.",
        "https://manitoba.goingtocamp.com",
    ),
    (
        22,
        "Newfoundland & Labrador Provincial Parks",
        "Newfoundland & Labrador provincial parks campsite reservations.",
        "https://www.nlcamping.ca",
    ),
    (
        23,
        "Gatineau Park",
        "National Capital Commission Gatineau Park campsite reservations.",
        "https://reservations.ncc-ccn.gc.ca",
    ),
    (
        24,
        "Long Point Region",
        "Long Point Region Conservation Authority campsite reservations.",
        "https://longpoint.goingtocamp.com",
    ),
    (
        25,
        "Maitland Valley",
        "Maitland Valley Conservation Authority campsite reservations.",
        "https://maitlandvalley.goingtocamp.com",
    ),
    (
        26,
        "St. Clair Region",
        "St. Clair Region Conservation Authority campsite reservations.",
        "https://stclair.goingtocamp.com",
    ),
)


def upgrade() -> None:
    """Seed verified GoingToCamp deployments under permanent provider IDs."""
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
                "GoingToCamp providers have dependent data; keep the provider seeds until that data is handled explicitly"
            )
    providers = sa.table("providers", sa.column("id", sa.Integer()))
    op.execute(providers.delete().where(providers.c.id.in_(provider_ids)))
