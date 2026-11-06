"""Existing accounts gain distinct topics without disrupting linked scans."""

import sqlite3
from pathlib import Path

import pytest
from alembic import command

from camply.db.config import DatabaseConfig
from camply.db.migration import get_alembic_config


def test_existing_user_topics_and_downgrade(tmp_path: Path) -> None:
    database = DatabaseConfig(HOST=str(tmp_path / "ntfy.db"))
    config = get_alembic_config(database)
    command.upgrade(config, "c2f84b9d1a3e")
    with sqlite3.connect(database.HOST) as connection:
        for index in (1, 2):
            connection.execute(
                "INSERT INTO users (id, email, is_early_access_user, pushover_token) VALUES (?, ?, 1, ?)",
                (
                    ("a" if index == 1 else "b") * 32,
                    f"user{index}@example.test",
                    "preserve-me",
                ),
            )
    command.upgrade(config, "head")
    with sqlite3.connect(database.HOST) as connection:
        rows = connection.execute(
            "SELECT ntfy_topic, notification_provider, ntfy_server_url, pushover_token FROM users"
        ).fetchall()
        assert len({row[0] for row in rows}) == 2
        assert {row[0] for row in rows} == {"aaaaaaa", "bbbbbbb"}
        assert all(row[1:] == ("pushover", None, "preserve-me") for row in rows)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    command.downgrade(config, "c2f84b9d1a3e")
    with sqlite3.connect(database.HOST) as connection:
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone() == (2,)


@pytest.mark.parametrize("prefix_claimed", [False, True])
def test_user_id_topic_upgrade_preserves_custom_topics(
    tmp_path: Path, prefix_claimed: bool
) -> None:
    database = DatabaseConfig(HOST=str(tmp_path / "topics.db"))
    config = get_alembic_config(database)
    command.upgrade(config, "f024a1b2c3d4")
    original = "camply-" + "d" * 32
    with sqlite3.connect(database.HOST) as connection:
        rows = [
            ("a" * 32, "generated@example.test", original),
            ("b" * 32, "custom@example.test", "custom-topic"),
        ]
        if prefix_claimed:
            rows.append(("c" * 32, "claimed@example.test", "aaaaaaa"))
        connection.executemany(
            "INSERT INTO users (id, email, ntfy_topic, is_early_access_user) VALUES (?, ?, ?, 1)",
            rows,
        )
    command.upgrade(config, "head")
    with sqlite3.connect(database.HOST) as connection:
        topics = dict(connection.execute("SELECT email, ntfy_topic FROM users"))
        assert topics["generated@example.test"] == (
            original if prefix_claimed else "aaaaaaa"
        )
        assert topics["custom@example.test"] == "custom-topic"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    command.downgrade(config, "f024a1b2c3d4")
    with sqlite3.connect(database.HOST) as connection:
        assert dict(connection.execute("SELECT email, ntfy_topic FROM users")) == topics
