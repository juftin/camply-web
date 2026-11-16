"""
add equipment metadata and filtering

Revision ID: f373bee1b42b
Revises: 2d7ab29d3a46
Create Date: 2026-11-16 02:57:17.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "f373bee1b42b"
down_revision: str | Sequence[str] | None = "2d7ab29d3a46"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add discovery amenity/RV columns and scan equipment/accessibility filters."""
    with op.batch_alter_table("campgrounds", recreate="auto") as batch_op:
        batch_op.add_column(
            sa.Column(
                "campsite_types",
                sa.ARRAY(sa.String()).with_variant(sa.JSON(), "sqlite"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "has_electric",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "has_water",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "has_sewer",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "pets_allowed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "ada_accessible",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(sa.Column("max_rv_length", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_campground_max_rv_length",
            "max_rv_length IS NULL OR max_rv_length > 0",
        )

    with op.batch_alter_table("scan_results", recreate="auto") as batch_op:
        batch_op.add_column(
            sa.Column(
                "permitted_equipment",
                JSONB().with_variant(sa.JSON(), "sqlite"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("max_vehicle_length", sa.Integer(), nullable=True)
        )
        batch_op.create_check_constraint(
            "ck_scan_result_max_vehicle_length",
            "max_vehicle_length IS NULL OR max_vehicle_length > 0",
        )

    with op.batch_alter_table("user_scans", recreate="auto") as batch_op:
        batch_op.add_column(
            sa.Column(
                "require_accessible",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(sa.Column("min_rv_length", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_scan_min_rv_length",
            "min_rv_length IS NULL OR (min_rv_length >= 1 AND min_rv_length <= 200)",
        )


def downgrade() -> None:
    """Remove equipment/accessibility filtering columns and constraints."""
    with op.batch_alter_table("user_scans", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_scan_min_rv_length", type_="check")
        batch_op.drop_column("min_rv_length")
        batch_op.drop_column("require_accessible")

    with op.batch_alter_table("scan_results", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_scan_result_max_vehicle_length", type_="check")
        batch_op.drop_column("max_vehicle_length")
        batch_op.drop_column("permitted_equipment")

    with op.batch_alter_table("campgrounds", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_campground_max_rv_length", type_="check")
        batch_op.drop_column("max_rv_length")
        batch_op.drop_column("ada_accessible")
        batch_op.drop_column("pets_allowed")
        batch_op.drop_column("has_sewer")
        batch_op.drop_column("has_water")
        batch_op.drop_column("has_electric")
        batch_op.drop_column("campsite_types")
