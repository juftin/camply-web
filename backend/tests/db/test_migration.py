"""Exercise the packaged migration history independently of checkout paths."""

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.script import ScriptDirectory

from camply.db.config import DatabaseConfig, DatabaseDrivers
from camply.db.migration import get_alembic_config


def test_migration_config_uses_packaged_history() -> None:
    """Runtime configuration finds the unchanged graph without developer hooks."""
    config = get_alembic_config()
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["09367969f1a4"]
    assert len(list(scripts.walk_revisions())) == 15
    assert config.config_file_name is None
    assert config.get_section("post_write_hooks") is None
    assert (Path(scripts.dir) / "env.py").is_file()
    assert (Path(scripts.dir) / "script.py.mako").is_file()


@pytest.mark.parametrize("earlier_revision", [None, "067d9d721253"])
def test_migration_upgrade_is_cwd_independent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    earlier_revision: str | None,
) -> None:
    """Fresh and previously versioned SQLite databases upgrade from another cwd."""
    database_file = tmp_path / "synthetic.sqlite"
    config = get_alembic_config(
        DatabaseConfig(
            DRIVERNAME=DatabaseDrivers.SQLITE,
            HOST=f"/{database_file}",
        )
    )
    monkeypatch.chdir(tmp_path)
    if earlier_revision:
        command.upgrade(config, revision=earlier_revision)
        with sqlite3.connect(database_file) as connection:
            connection.execute(
                "INSERT INTO providers (id, name, url, enabled) VALUES (?, ?, ?, ?)",
                (999, "Synthetic provider", "https://synthetic.example.test", True),
            )
    command.upgrade(config, revision="head")
    with sqlite3.connect(database_file) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == ("09367969f1a4",)
        if earlier_revision:
            assert connection.execute(
                "SELECT name FROM providers WHERE id = 999"
            ).fetchone() == ("Synthetic provider",)
