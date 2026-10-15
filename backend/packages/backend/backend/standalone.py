"""Launch a prepared application using Python, SQLite, and bundled frontend assets."""

import argparse
import os
import tempfile
from pathlib import Path

from backend.config import BackendConfig, RuntimeMode, backend_config
from db.config import DatabaseConfig, DatabaseDrivers, db
from db.migrate import upgrade_database


def validate_standalone(config: BackendConfig, database: DatabaseConfig) -> Path:
    """Reject incomplete builds, unsupported storage, and conflicting worker settings."""
    if database.DRIVERNAME != DatabaseDrivers.SQLITE or database.HOST == ":memory:":
        raise ValueError(
            "Standalone requires file-backed SQLite; configure CAMPLY_DB_DRIVERNAME and CAMPLY_DB_HOST"
        )
    for setting in ("WEB_CONCURRENCY", "GUNICORN_WORKERS", "UVICORN_WORKERS"):
        if os.environ.get(setting, "1") != "1":
            raise ValueError(
                f"Standalone requires one worker; unset {setting} or set it to 1"
            )
    if os.environ.get("GUNICORN_RELOAD", "0").lower() not in {"0", "false", ""}:
        raise ValueError("Standalone requires one worker without production reload")
    directory = config.frontend_dir or Path(__file__).resolve().parent / "static"
    if not directory.is_absolute():
        raise ValueError(
            "CAMPLY_FRONTEND_DIR must be an absolute frontend build directory"
        )
    try:
        with (directory / "index.html").open("rb") as index:
            index.read(1)
    except OSError as exc:
        raise ValueError(
            "Built frontend is missing or unreadable; run task standalone:build or configure CAMPLY_FRONTEND_DIR"
        ) from exc
    filename = Path(str(database.url.database))
    try:
        filename.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=filename.parent):
            pass
        if filename.exists() and (
            not filename.is_file() or not os.access(filename, os.W_OK)
        ):
            raise OSError("Database file is not writable")
    except OSError as exc:
        raise ValueError(
            "SQLite storage is not writable; configure CAMPLY_DB_HOST"
        ) from exc
    return directory


def main() -> None:
    """Migrate storage and start exactly one API/frontend/background process."""
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    os.environ["CAMPLY_RUNTIME_MODE"] = "standalone"
    backend_config.runtime_mode = RuntimeMode.STANDALONE
    try:
        validate_standalone(backend_config, db)
        upgrade_database(db)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    uvicorn.run("backend.app:app", host=args.host, port=args.port, workers=1)


if __name__ == "__main__":
    main()
