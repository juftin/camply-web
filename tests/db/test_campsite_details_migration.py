"""Check that existing availability snapshots survive the site-details migration."""

import runpy
from importlib.resources import files

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_campsite_details_migration_preserves_old_snapshots() -> None:
    """Add unknown attributes to legacy rows and preserve their dates on downgrade."""
    migration = runpy.run_path(
        str(
            files("camply.db").joinpath(
                "migrations/versions/09367969f1a4_preserve_campsite_details.py"
            )
        )
    )
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "CREATE TABLE scan_results (campsite_id TEXT, available_dates TEXT)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO scan_results VALUES ('synthetic-site', '[\"2027-07-01\"]')"
            )
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration["upgrade"]()
            row = (
                connection.execute(sa.text("SELECT * FROM scan_results"))
                .mappings()
                .one()
            )
            assert row["campsite_name"] == ""
            assert row["campsite_type"] is None
            assert row["is_electric"] is None
            assert row["is_accessible"] is None
            migration["downgrade"]()
            assert connection.execute(sa.text("SELECT * FROM scan_results")).one() == (
                "synthetic-site",
                '["2027-07-01"]',
            )
            migration["upgrade"]()
