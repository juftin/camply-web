"""
indexed native campground search

Revision ID: 2ac874f9d2ad
Revises: 9b2c3d4e5f6a
Create Date: 2026-10-14 04:28:51.469092+00:00
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ac874f9d2ad"
down_revision: Union[str, Sequence[str], None] = "9b2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Index native weighted token search and city typo matching on PostgreSQL."""
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE INDEX ix_search_text_vector ON search USING gin ((
            setweight(to_tsvector('simple'::regconfig, coalesce(campground_name, '')), 'A') ||
            setweight(to_tsvector('simple'::regconfig, coalesce(recreation_area_name, '')), 'B') ||
            setweight(to_tsvector('simple'::regconfig, coalesce(city, '')), 'C') ||
            setweight(to_tsvector('simple'::regconfig, coalesce(state, '')), 'D')
        ))
        """
    )
    op.execute(
        "CREATE INDEX ix_search_city_trgm ON search USING gin (city gin_trgm_ops)"
    )


def downgrade() -> None:
    """Remove the new PostgreSQL indexes while preserving catalog data."""
    if op.get_bind().dialect.name != "postgresql":
        return
    op.drop_index("ix_search_city_trgm", table_name="search")
    op.drop_index("ix_search_text_vector", table_name="search")
