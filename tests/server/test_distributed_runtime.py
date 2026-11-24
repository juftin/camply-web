"""Protect ordinary API startup from enabling standalone behavior implicitly."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


def test_default_runtime_in_fresh_process(tmp_path: Path) -> None:
    """Exercise import and lifespan with no runtime override or cached application."""
    frontend = tmp_path / "frontend"
    (frontend / "assets").mkdir(parents=True)
    (frontend / "index.html").write_text("<html>Standalone frontend</html>")
    (frontend / "assets/probe.js").write_text("console.log('standalone');")
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("CAMPLY_", "PROMETHEUS_"))
    }
    environment.update(
        CAMPLY_DB_DRIVERNAME="sqlite+aiosqlite",
        CAMPLY_DB_HOST=str(tmp_path / "distributed.db"),
        CAMPLY_FRONTEND_DIR=str(frontend),
    )
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _verify_default_runtime() -> None:
    """Run real API requests while forbidding standalone startup and migration."""
    from fastapi.testclient import TestClient
    from prometheus_client.parser import text_string_to_metric_families

    from camply.db.config import DatabaseConfig, db
    from camply.db.models import Base
    from camply.server.config import RuntimeMode, backend_config

    async def create_tables() -> None:
        """Prepare test-owned storage for the real database-backed metric gauges."""
        engine = db.create_async_engine()
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        finally:
            await engine.dispose()

    asyncio.run(create_tables())
    assert backend_config.runtime_mode == RuntimeMode.DISTRIBUTED
    with (
        patch("camply.worker.runtime.LocalRunner") as runner,
        patch.object(DatabaseConfig, "open") as open_database,
        patch.object(DatabaseConfig, "close") as close_database,
        patch("camply.server.standalone.upgrade_database") as migrate,
    ):
        from camply.server.app import app

        with TestClient(app) as client:
            assert client.get("/api/ping").status_code == 200
            for path in ("/", "/dashboard/scans/synthetic", "/assets/probe.js"):
                response = client.get(path, headers={"Accept": "text/html"})
                assert response.status_code == 404
                assert response.json() == {"detail": "Not Found"}

            metrics = client.get("/metrics")
            assert metrics.status_code == 200
            assert metrics.headers["content-type"].startswith("text/plain")
            samples = [
                sample
                for family in text_string_to_metric_families(metrics.text)
                for sample in family.samples
            ]
            assert any(
                sample.name == "camply_http_requests_total"
                and sample.labels
                == {"endpoint": "/api/ping", "method": "GET", "status": "200"}
                and sample.value == 1
                for sample in samples
            )
            assert any(
                sample.name == "camply_total_scans" and sample.value == 0
                for sample in samples
            )

        runner.assert_not_called()
        open_database.assert_not_called()
        close_database.assert_not_called()
        migrate.assert_not_called()


if __name__ == "__main__":
    _verify_default_runtime()
