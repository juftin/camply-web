"""
backfill search coordinates and locations

Revision ID: b1c97fce287e
Revises: 2ac874f9d2ad
Create Date: 2026-10-14 16:45:00.000000+00:00
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c97fce287e"
down_revision: Union[str, Sequence[str], None] = "2ac874f9d2ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill latitude, longitude, and location metadata into search rows."""
    op.execute(
        """
        UPDATE search
        SET latitude = (
                SELECT latitude FROM campgrounds c
                WHERE c.provider_id = search.provider_id AND c.id = search.campground_id
            ),
            longitude = (
                SELECT longitude FROM campgrounds c
                WHERE c.provider_id = search.provider_id AND c.id = search.campground_id
            ),
            city = (
                SELECT city FROM campgrounds c
                WHERE c.provider_id = search.provider_id AND c.id = search.campground_id
            ),
            state = (
                SELECT state FROM campgrounds c
                WHERE c.provider_id = search.provider_id AND c.id = search.campground_id
            ),
            country = (
                SELECT country FROM campgrounds c
                WHERE c.provider_id = search.provider_id AND c.id = search.campground_id
            ),
            reservable = (
                SELECT reservable FROM campgrounds c
                WHERE c.provider_id = search.provider_id AND c.id = search.campground_id
            )
        WHERE entity_type = 'Campground' AND (latitude IS NULL OR longitude IS NULL OR state IS NULL);
        """
    )
    op.execute(
        """
        UPDATE search
        SET latitude = (
                SELECT latitude FROM recreation_areas r
                WHERE r.provider_id = search.provider_id AND r.id = search.recreation_area_id
            ),
            longitude = (
                SELECT longitude FROM recreation_areas r
                WHERE r.provider_id = search.provider_id AND r.id = search.recreation_area_id
            ),
            city = (
                SELECT city FROM recreation_areas r
                WHERE r.provider_id = search.provider_id AND r.id = search.recreation_area_id
            ),
            state = (
                SELECT state FROM recreation_areas r
                WHERE r.provider_id = search.provider_id AND r.id = search.recreation_area_id
            ),
            country = (
                SELECT country FROM recreation_areas r
                WHERE r.provider_id = search.provider_id AND r.id = search.recreation_area_id
            ),
            reservable = (
                SELECT reservable FROM recreation_areas r
                WHERE r.provider_id = search.provider_id AND r.id = search.recreation_area_id
            )
        WHERE entity_type = 'RecreationArea' AND (latitude IS NULL OR longitude IS NULL OR state IS NULL);
        """
    )


def downgrade() -> None:
    """Preserve backfilled coordinates and metadata on downgrade."""
    pass
