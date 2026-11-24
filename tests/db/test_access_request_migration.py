"""Verify the access request review migration on SQLite and PostgreSQL."""

import io
import runpy
import uuid
from importlib.resources import files
from typing import Any

import sqlalchemy as sa
from alembic import command
from alembic.migration import MigrationContext
from alembic.operations import Operations

from camply.db.config import DatabaseConfig, DatabaseDrivers
from camply.db.migration import get_alembic_config

# Pre-migration schema, matching the original ``access_requests`` revision.
LEGACY_SCHEMA = (
    "CREATE TABLE users (id CHAR(32) PRIMARY KEY)",
    "CREATE TABLE access_requests ("
    "id CHAR(32) NOT NULL PRIMARY KEY, "
    "email VARCHAR(255) NOT NULL, "
    "status VARCHAR(20) NOT NULL, "
    "created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL)",
    "CREATE UNIQUE INDEX ix_access_requests_email ON access_requests (email)",
)


def _load_migration() -> dict[str, Any]:
    """Load the migration module by file name without importing the package tree.

    Returns
    -------
    dict[str, Any]
        Module globals including ``upgrade`` and ``downgrade``.
    """
    paths = files("camply.db").joinpath("migrations/versions").iterdir()
    path = next(p for p in paths if p.name.endswith("_access_request_review.py"))
    return runpy.run_path(str(path))


def test_access_request_migration_preserves_rows_and_round_trips() -> None:
    """Existing requests survive upgrade/downgrade/re-upgrade with new nullable columns."""
    migration = _load_migration()
    request_id = uuid.uuid4().hex
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        for statement in LEGACY_SCHEMA:
            connection.execute(sa.text(statement))
        connection.execute(
            sa.text(
                "INSERT INTO access_requests (id, email, status) "
                "VALUES (:id, 'synthetic@example.test', 'approved')"
            ),
            {"id": request_id},
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration["upgrade"]()
            columns = {
                column["name"]: column
                for column in sa.inspect(connection).get_columns("access_requests")
            }
            assert {"name", "updated_at", "reviewed_at", "reviewed_by_id"} <= set(
                columns
            )
            assert columns["user_id"]["nullable"] is True
            assert columns["updated_at"]["nullable"] is False
            foreign_keys = sa.inspect(connection).get_foreign_keys("access_requests")
            assert {fk["constrained_columns"][0] for fk in foreign_keys} == {
                "user_id",
                "reviewed_by_id",
            }
            assert {fk["options"]["ondelete"] for fk in foreign_keys} == {"SET NULL"}
            row = connection.execute(
                sa.text(
                    "SELECT email, status, name, reviewed_at, user_id, updated_at "
                    "FROM access_requests"
                )
            ).one()
            assert row[:5] == ("synthetic@example.test", "approved", None, None, None)
            assert row[5] is not None
            indexes = sa.inspect(connection).get_indexes("access_requests")
            assert [(i["name"], i["unique"]) for i in indexes] == [
                ("ix_access_requests_email", 1)
            ]

            migration["downgrade"]()
            assert [
                column["name"]
                for column in sa.inspect(connection).get_columns("access_requests")
            ] == ["id", "email", "status", "created_at"]
            assert connection.execute(
                sa.text("SELECT email, status FROM access_requests")
            ).one() == ("synthetic@example.test", "approved")

            migration["upgrade"]()
            assert (
                connection.execute(
                    sa.text("SELECT count(*) FROM access_requests")
                ).scalar()
                == 1
            )

    # Verify ON DELETE SET NULL clears user links without deleting the request.
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys = ON")
        connection.commit()
        with connection.begin():
            user_id = uuid.uuid4().hex
            reviewer_id = uuid.uuid4().hex
            connection.execute(
                sa.text("INSERT INTO users (id) VALUES (:u), (:r)"),
                {"u": user_id, "r": reviewer_id},
            )
            connection.execute(
                sa.text(
                    "UPDATE access_requests SET user_id = :u, reviewed_by_id = :r "
                    "WHERE id = :id"
                ),
                {"u": user_id, "r": reviewer_id, "id": request_id},
            )
            connection.execute(
                sa.text("DELETE FROM users WHERE id IN (:u, :r)"),
                {"u": user_id, "r": reviewer_id},
            )
            assert connection.execute(
                sa.text(
                    "SELECT user_id, reviewed_by_id FROM access_requests WHERE id = :id"
                ),
                {"id": request_id},
            ).one() == (None, None)
    engine.dispose()


def test_access_request_migration_compiles_for_postgresql() -> None:
    """PostgreSQL receives direct ``ALTER TABLE`` statements, not a table rebuild."""
    config = get_alembic_config(DatabaseConfig(DRIVERNAME=DatabaseDrivers.POSTGRES))
    output = io.StringIO()
    config.output_buffer = output
    command.upgrade(config, revision="e818084258e6:b9a4958c2f7c", sql=True)
    sql = output.getvalue()
    assert "ALTER TABLE access_requests ADD COLUMN name VARCHAR(255)" in sql
    assert "ADD COLUMN reviewed_at TIMESTAMP WITH TIME ZONE" in sql
    assert "FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL" in sql
    assert "CREATE TABLE _alembic_tmp" not in sql

    output.truncate(0)
    output.seek(0)
    command.downgrade(config, revision="b9a4958c2f7c:e818084258e6", sql=True)
    assert "DROP COLUMN user_id" in output.getvalue()
