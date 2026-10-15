"""Standalone launch validates resources before it starts an HTTP server."""

from pathlib import Path

import pytest

from backend.config import BackendConfig, RuntimeMode
from backend.standalone import validate_standalone
from db.config import DatabaseConfig, DatabaseDrivers


def test_required_frontend_and_database(tmp_path: Path) -> None:
    """Fail early on missing builds or server-backed storage."""
    config = BackendConfig(runtime_mode=RuntimeMode.STANDALONE, frontend_dir=tmp_path)
    database = DatabaseConfig(HOST=str(tmp_path / "state.db"))
    with pytest.raises(ValueError, match="frontend"):
        validate_standalone(config, database)
    (tmp_path / "index.html").write_text("<html></html>")
    assert validate_standalone(config, database) == tmp_path
    with pytest.raises(ValueError, match="SQLite"):
        validate_standalone(config, DatabaseConfig(DRIVERNAME=DatabaseDrivers.POSTGRES))


def test_reject_multiple_workers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multiple API workers would create duplicate local schedulers."""
    (tmp_path / "index.html").write_text("<html></html>")
    monkeypatch.setenv("WEB_CONCURRENCY", "2")
    with pytest.raises(ValueError, match="one worker"):
        validate_standalone(
            BackendConfig(runtime_mode=RuntimeMode.STANDALONE, frontend_dir=tmp_path),
            DatabaseConfig(HOST=str(tmp_path / "state.db")),
        )


@pytest.mark.parametrize(
    "invalid", ["memory", "relative_assets", "storage_directory", "reload"]
)
def test_actionable_local_resource_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: str
) -> None:
    """Reject resource mistakes before starting background tasks or serving HTTP."""
    (tmp_path / "index.html").write_text("<html></html>")
    config = BackendConfig(runtime_mode=RuntimeMode.STANDALONE, frontend_dir=tmp_path)
    database = DatabaseConfig(HOST=str(tmp_path / "state.db"))
    message = "SQLite"
    if invalid == "memory":
        database.HOST = ":memory:"
    elif invalid == "relative_assets":
        config.frontend_dir = Path("relative")
        message = "absolute"
    elif invalid == "storage_directory":
        database.HOST = str(tmp_path)
        message = "writable"
    else:
        monkeypatch.setenv("GUNICORN_RELOAD", "1")
        message = "reload"
    with pytest.raises(ValueError, match=message):
        validate_standalone(config, database)
