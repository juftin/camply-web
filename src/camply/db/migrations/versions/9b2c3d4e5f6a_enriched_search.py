"""
Enriched search metadata and indexes

Revision ID: 9b2c3d4e5f6a
Revises: 8a1b2c3d4e5f
Create Date: 2026-10-12 23:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b2c3d4e5f6a"
down_revision: Union[str, Sequence[str], None] = "36dbff1f679f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: enrich search table with location, amenities, and indexes.
    """
    op.add_column("search", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("search", sa.Column("state", sa.String(length=50), nullable=True))
    op.add_column("search", sa.Column("country", sa.String(length=50), nullable=True))
    op.add_column("search", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("search", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column(
        "search",
        sa.Column(
            "reservable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column("search", sa.Column("campsite_types", sa.JSON(), nullable=True))
    op.add_column(
        "search",
        sa.Column(
            "has_electric",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "search",
        sa.Column(
            "has_water",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "search",
        sa.Column(
            "has_sewer",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "search",
        sa.Column(
            "pets_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "search",
        sa.Column(
            "ada_accessible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "search",
        sa.Column("max_rv_length", sa.Integer(), nullable=True),
    )

    op.create_index(op.f("ix_search_state"), "search", ["state"], unique=False)
    op.create_index(
        op.f("ix_search_entity_type"), "search", ["entity_type"], unique=False
    )
    op.create_index(
        op.f("ix_search_provider_id"), "search", ["provider_id"], unique=False
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_search_campground_trgm ON search USING gin (campground_name gin_trgm_ops);"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_search_rec_area_trgm ON search USING gin (recreation_area_name gin_trgm_ops);"
        )


def downgrade() -> None:
    """
    Downgrade schema: remove enriched columns and indexes.
    """
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_search_rec_area_trgm;")
        op.execute("DROP INDEX IF EXISTS ix_search_campground_trgm;")

    op.drop_index(op.f("ix_search_provider_id"), table_name="search")
    op.drop_index(op.f("ix_search_entity_type"), table_name="search")
    op.drop_index(op.f("ix_search_state"), table_name="search")

    op.drop_column("search", "max_rv_length")
    op.drop_column("search", "ada_accessible")
    op.drop_column("search", "pets_allowed")
    op.drop_column("search", "has_sewer")
    op.drop_column("search", "has_water")
    op.drop_column("search", "has_electric")
    op.drop_column("search", "campsite_types")
    op.drop_column("search", "reservable")
    op.drop_column("search", "longitude")
    op.drop_column("search", "latitude")
    op.drop_column("search", "country")
    op.drop_column("search", "state")
    op.drop_column("search", "city")
