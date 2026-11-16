"""
convert search.campsite_types to a native string array on PostgreSQL

Revision ID: a1c3e5f7b9d2
Revises: f373bee1b42b
Create Date: 2026-11-16 06:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c3e5f7b9d2"
down_revision: str | Sequence[str] | None = "f373bee1b42b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Align ``search.campsite_types`` with ``campgrounds.campsite_types``.

    The search table originally created this column as JSON, but the ORM model and the
    ``INSERT ... SELECT`` that populates it from ``campgrounds`` use ``VARCHAR[]``,
    which PostgreSQL refuses to assign to a JSON column. SQLite keeps JSON.
    """
    if op.get_bind().dialect.name != "postgresql":
        return
    # PostgreSQL forbids subqueries in ``USING``, so convert through a temp function.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION pg_temp.json_to_text_array(value json)
        RETURNS varchar[]
        LANGUAGE sql IMMUTABLE AS $$
            SELECT CASE
                WHEN value IS NULL OR json_typeof(value) <> 'array' THEN NULL
                ELSE ARRAY(SELECT json_array_elements_text(value))
            END
        $$
        """
    )
    op.execute(
        """
        ALTER TABLE search
        ALTER COLUMN campsite_types TYPE VARCHAR[]
        USING pg_temp.json_to_text_array(campsite_types)
        """
    )
    op.execute("DROP FUNCTION IF EXISTS pg_temp.json_to_text_array(json)")


def downgrade() -> None:
    """Restore the JSON column type on PostgreSQL."""
    if op.get_bind().dialect.name != "postgresql":
        return
    op.alter_column(
        "search",
        "campsite_types",
        type_=sa.JSON(),
        postgresql_using="to_json(campsite_types)",
    )
