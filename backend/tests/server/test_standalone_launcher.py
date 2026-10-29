"""Standalone launch validates resources before it starts an HTTP server."""

from pathlib import Path
from unittest.mock import patch

import pytest

from camply.db.config import DatabaseConfig, DatabaseDrivers
from camply.server import standalone
from camply.server.config import BackendConfig, RuntimeMode
from camply.server.standalone import validate_standalone


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


@pytest.mark.parametrize("configured", [None, "https://synthetic.example/prefix"])
def test_launcher_selects_local_alert_links(
    monkeypatch: pytest.MonkeyPatch, configured: str | None
) -> None:
    """Default summary links to the Python origin while preserving explicit public URLs."""
    monkeypatch.setattr("sys.argv", ["standalone", "--port", "8765"])
    monkeypatch.setattr(standalone, "backend_config", BackendConfig())
    monkeypatch.setenv("CAMPLY_RUNTIME_MODE", "standalone")
    if configured:
        monkeypatch.setenv("CAMPLY_APP_URL", configured)
    else:
        monkeypatch.delenv("CAMPLY_APP_URL", raising=False)
    with (
        patch.object(standalone, "validate_standalone"),
        patch.object(standalone, "upgrade_database"),
        patch("uvicorn.run") as serve,
    ):
        standalone.main()
    import os

    assert os.environ["CAMPLY_APP_URL"] == (configured or "http://127.0.0.1:8765")
    serve.assert_called_once_with(
        "camply.server.app:app", host="127.0.0.1", port=8765, workers=1
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
