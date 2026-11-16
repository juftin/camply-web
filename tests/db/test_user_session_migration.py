"""Verify the ``user_sessions`` migration on SQLite and PostgreSQL."""

import io
import sqlite3
import uuid
from pathlib import Path

import sqlalchemy as sa
from alembic import command

from camply.db.config import DatabaseConfig, DatabaseDrivers
from camply.db.migration import get_alembic_config


def test_user_session_migration_round_trips(tmp_path: Path) -> None:
    """Upgrade, inspect schema/indexes, downgrade, and re-upgrade cleanly."""
    database_file = tmp_path / "sessions.db"
    config = get_alembic_config(
        DatabaseConfig(
            DRIVERNAME=DatabaseDrivers.SQLITE,
            HOST=f"/{database_file}",
        )
    )
    command.upgrade(config, revision="b9a4958c2f7c")
    command.upgrade(config, revision="5a4d254fafa9")

    engine = sa.create_engine(f"sqlite:///{database_file}")
    try:
        with engine.connect() as connection:
            inspector = sa.inspect(connection)
            assert "user_sessions" in inspector.get_table_names()

            columns = {
                column["name"]: column
                for column in inspector.get_columns("user_sessions")
            }
            assert set(columns) == {
                "id",
                "user_id",
                "user_agent",
                "ip_address",
                "created_at",
                "expires_at",
                "revoked_at",
            }
            assert columns["id"]["nullable"] is False
            assert columns["user_id"]["nullable"] is False
            assert columns["user_agent"]["nullable"] is True
            assert columns["ip_address"]["nullable"] is True
            assert columns["created_at"]["nullable"] is False
            assert columns["expires_at"]["nullable"] is False
            assert columns["revoked_at"]["nullable"] is True

            foreign_keys = inspector.get_foreign_keys("user_sessions")
            assert len(foreign_keys) == 1
            assert foreign_keys[0]["referred_table"] == "users"
            assert foreign_keys[0]["constrained_columns"] == ["user_id"]
            assert foreign_keys[0]["options"]["ondelete"] == "CASCADE"

            indexes = {
                idx["name"]: idx for idx in inspector.get_indexes("user_sessions")
            }
            assert indexes["ix_user_sessions_user_id"]["column_names"] == ["user_id"]
            assert indexes["ix_user_sessions_expires_at"]["column_names"] == [
                "expires_at"
            ]
    finally:
        engine.dispose()

    command.downgrade(config, revision="b9a4958c2f7c")
    with sqlite3.connect(database_file) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "user_sessions" not in tables
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchall() == [("b9a4958c2f7c",)]

    command.upgrade(config, revision="head")
    with sqlite3.connect(database_file) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchall() == [("2d7ab29d3a46",)]


def test_user_session_migration_cascades_on_user_delete(tmp_path: Path) -> None:
    """Deleting a user cascades to their ``user_sessions`` rows when FKs are enabled."""
    database_file = tmp_path / "sessions_cascade.db"
    config = get_alembic_config(
        DatabaseConfig(
            DRIVERNAME=DatabaseDrivers.SQLITE,
            HOST=f"/{database_file}",
        )
    )
    command.upgrade(config, revision="5a4d254fafa9")

    with sqlite3.connect(database_file) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        user_a = uuid.uuid4().hex
        user_b = uuid.uuid4().hex
        sess_a = uuid.uuid4().hex
        sess_b = uuid.uuid4().hex
        connection.execute(
            "INSERT INTO users (id, email, is_early_access_user, ntfy_topic) "
            "VALUES (?, ?, 0, ?), (?, ?, 0, ?)",
            (
                user_a,
                "a@example.test",
                f"camply-{user_a[:7]}",
                user_b,
                "b@example.test",
                f"camply-{user_b[:7]}",
            ),
        )
        connection.execute(
            "INSERT INTO user_sessions (id, user_id, user_agent, ip_address, expires_at) "
            "VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?)",
            (
                sess_a,
                user_a,
                "AgentA",
                "127.0.0.1",
                "2099-01-01 00:00:00",
                sess_b,
                user_b,
                "AgentB",
                "127.0.0.2",
                "2099-01-01 00:00:00",
            ),
        )
        connection.execute("DELETE FROM users WHERE id = ?", (user_a,))
        remaining = connection.execute(
            "SELECT id, user_id FROM user_sessions"
        ).fetchall()
        assert remaining == [(sess_b, user_b)]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_user_session_migration_compiles_for_postgresql() -> None:
    """PostgreSQL compiles ``user_sessions`` creation, indexes, and downgrade cleanly."""
    config = get_alembic_config(DatabaseConfig(DRIVERNAME=DatabaseDrivers.POSTGRES))
    output = io.StringIO()
    config.output_buffer = output
    command.upgrade(config, revision="b9a4958c2f7c:5a4d254fafa9", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE user_sessions" in sql
    assert "TIMESTAMP WITH TIME ZONE" in sql
    assert "FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE" in sql
    assert "CREATE INDEX ix_user_sessions_expires_at ON user_sessions" in sql
    assert "CREATE INDEX ix_user_sessions_user_id ON user_sessions" in sql

    output.truncate(0)
    output.seek(0)
    command.downgrade(config, revision="5a4d254fafa9:b9a4958c2f7c", sql=True)
    downgrade_sql = output.getvalue()
    assert "DROP INDEX ix_user_sessions_user_id" in downgrade_sql
    assert "DROP INDEX ix_user_sessions_expires_at" in downgrade_sql
    assert "DROP TABLE user_sessions" in downgrade_sql
