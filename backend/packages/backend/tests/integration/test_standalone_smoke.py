"""Opt-in clean-wheel, real HTTP, SQLite recovery, and Chromium verification."""

from __future__ import annotations

import datetime as dt
import os
import socket
import sqlite3
import subprocess
import threading
import time
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("CAMPLY_STANDALONE_SMOKE") != "1", reason="Run task standalone:test"
)


def _port() -> int:
    """Allocate a loopback port owned by this integration test."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait(check: Callable[[], bool], *, timeout: float = 30) -> None:
    """Bound asynchronous process/upstream readiness without fixed long sleeps."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except (httpx.HTTPError, OSError, sqlite3.OperationalError, ValueError):
            pass
        time.sleep(0.1)
    raise AssertionError("Standalone smoke readiness timed out")


def _stop(process: subprocess.Popen[bytes]) -> None:
    """Reap only the test-owned Python server."""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _login(client: httpx.Client, username: str, password: str) -> None:
    """Establish real session/CSRF cookies using synthetic test credentials."""
    response = client.post(
        "/api/login", json={"username": username, "password": password}
    )
    assert response.is_success, response.text
    client.headers["X-CSRF-Token"] = client.cookies["camply_csrf"]


def _exercise_scans(
    origin: str,
    stack: ExitStack,
    availability_gate: threading.Event,
    delivery_gate: threading.Event,
    checks: list[str],
    deliveries: list[bytes],
    start: Callable[[], subprocess.Popen[bytes]],
    rows: Callable[[str], list[tuple]],
    process: subprocess.Popen[bytes],
) -> None:
    """Verify shared-target HTTP checks and pending-alert recovery on restart."""
    client = stack.enter_context(
        httpx.Client(base_url=origin, headers={"Origin": origin})
    )
    _login(client, "synthetic-admin", "synthetic-password")
    assert client.post("/api/admin/operations/sync-providers").is_success
    _wait(lambda: bool(client.get("/api/search", params={"query": "Synthetic"}).json()))
    assert client.patch("/api/me", json={"pushover_token": "synthetic"}).is_success
    tomorrow = dt.datetime.now(dt.timezone.utc).date() + dt.timedelta(days=1)
    scan = {
        "provider_id": 1,
        "campground_id": "synthetic-cg",
        "start_date": tomorrow.isoformat(),
        "end_date": (tomorrow + dt.timedelta(days=2)).isoformat(),
        "min_stay_length": 2,
    }
    response = client.post("/api/scans", json=scan)
    assert response.is_success, response.text
    _wait(lambda: len(checks) == 1)
    started = time.monotonic()
    assert client.get("/api/health").is_success
    assert time.monotonic() - started < 2
    response = client.post(
        "/api/admin/users",
        json={
            "email": "second@example.test",
            "password": "synthetic-password",
            "is_invited": True,
        },
    )
    assert response.is_success, response.text
    second = stack.enter_context(
        httpx.Client(base_url=origin, headers={"Origin": origin})
    )
    _login(second, "second@example.test", "synthetic-password")
    assert second.patch("/api/me", json={"pushover_token": "synthetic"}).is_success
    response = second.post("/api/scans", json=scan)
    assert response.is_success, response.text
    availability_gate.set()
    _wait(lambda: len(deliveries) == 1)
    assert len(checks) == 1
    _wait(lambda: rows("SELECT COUNT(*) FROM notification_outbox")[0][0] == 2)
    _stop(process)
    assert (
        rows(
            "SELECT COUNT(*) FROM notification_outbox WHERE status IN ('pending','sending')"
        )[0][0]
        == 2
    )
    delivery_gate.set()
    process = start()
    _wait(
        lambda: (
            rows("SELECT COUNT(*) FROM notification_outbox WHERE status='sent'")[0][0]
            == 2
        )
    )
    assert rows("SELECT COUNT(*) FROM user_scans")[0][0] == 2
    assert client.get("/api/scans").is_success
    assert client.get("/api/admin/operations").json()["runtime_mode"] == "standalone"
    assert client.get("/api/admin/trends").json()["available"] is False
    assert client.get("/metrics").status_code == 404
    assert client.get("/api/missing").status_code == 404
    _verify_current_features(client, origin, deliveries)


def _verify_current_features(
    client: httpx.Client, origin: str, deliveries: list[bytes]
) -> None:
    """Exercise current maps, saved site details, and summary links on installed SQLite."""
    import json

    summary = client.get("/api/search/map/summary").json()
    assert summary["total"] == 1 and summary["mappable_total"] == 1
    mapped = client.get(
        "/api/search/map",
        params={"west": -120, "south": 37, "east": -119, "north": 38, "zoom": 10},
    )
    assert mapped.is_success, mapped.text
    assert mapped.json()["represented_total"] == 1
    scans = client.get("/api/scans").json()["scans"]
    detail = client.get(f"/api/scans/{scans[0]['id']}").json()
    assert detail["found_count"] == 1
    assert detail["results"][0]["campsite_name"] == "Synthetic Site"
    assert detail["results"][0]["campsite_type"] == "TENT"
    for sent in deliveries:
        payload = json.loads(sent)
        assert payload["url_title"] == "View campsites"
        assert payload["url"].startswith(origin + "/dashboard/scans/")
        response = client.get(
            urlparse(payload["url"]).path, headers={"Accept": "text/html"}
        )
        assert response.is_success and "text/html" in response.headers["content-type"]


def _verify_map_worker(core: Path, origin: str) -> None:
    """Serve the installed MapLibre worker with compression and immutable caching."""
    workers = list(
        core.glob(
            "lib/python*/site-packages/backend/static/assets/maplibre-gl-worker-*.js"
        )
    )
    assert len(workers) == 1, "The standalone wheel must bundle the map worker"
    resource = httpx.get(
        origin + "/assets/" + workers[0].name, headers={"Accept-Encoding": "gzip"}
    )
    assert resource.is_success
    assert "javascript" in resource.headers["content-type"]
    assert resource.headers["content-encoding"] == "gzip"
    assert "immutable" in resource.headers["cache-control"]


def test_installed_standalone_stack(tmp_path: Path) -> None:
    """Prove a core-only installed build serves browsers and recovers committed alerts."""
    root = Path(__file__).resolve().parents[5]
    wheels = sorted((root / "backend/dist").glob("*.whl"))
    assert len(wheels) == 4, "Run task standalone:build first"
    core = tmp_path / "core"
    subprocess.run(
        ["uv", "venv", "--python", "3.12", str(core)], check=True, capture_output=True
    )
    python = core / "bin/python"
    constraints = tmp_path / "constraints.txt"
    subprocess.run(
        [
            "uv",
            "export",
            "--project",
            str(root / "backend"),
            "--package",
            "backend",
            "--no-dev",
            "--no-emit-workspace",
            "--no-hashes",
            "--output-file",
            str(constraints),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--constraint",
            str(constraints),
            *map(str, wheels),
        ],
        check=True,
        capture_output=True,
    )
    availability_gate = threading.Event()
    delivery_gate = threading.Event()
    checks: list[str] = []
    deliveries: list[bytes] = []

    class Upstream(BaseHTTPRequestHandler):
        """Supply delayed generated provider/notification HTTP responses."""

        def log_message(self, format: str, *args: object) -> None:
            """Keep synthetic request logs out of normal test output."""

        def do_GET(self) -> None:
            """Hold provider I/O while testing unrelated API responsiveness."""
            checks.append(self.path)
            availability_gate.wait(timeout=30)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def do_POST(self) -> None:
            """Hold delivery until the test has interrupted the Python application."""
            deliveries.append(
                self.rfile.read(int(self.headers.get("Content-Length", "0")))
            )
            delivery_gate.wait(timeout=30)
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": 1}')
            except BrokenPipeError:
                pass

    database = tmp_path / "state.db"

    def rows(sql: str) -> list[tuple]:
        """Inspect only task-owned synthetic storage without touching user data."""
        with sqlite3.connect(database) as connection:
            return connection.execute(sql).fetchall()

    with ExitStack() as stack:
        upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        stack.callback(upstream.server_close)
        stack.callback(upstream.shutdown)
        stack.callback(availability_gate.set)
        stack.callback(delivery_gate.set)
        origin = f"http://127.0.0.1:{_port()}"
        env = {
            **os.environ,
            "PYTHONPATH": "",
            "CAMPLY_RUNTIME_MODE": "standalone",
            "CAMPLY_APP_URL": origin,
            "CAMPLY_DB_DRIVERNAME": "sqlite+aiosqlite",
            "CAMPLY_DB_HOST": str(database),
            "CAMPLY_AUTH_MODE": "session",
            "CAMPLY_LOGIN_USERNAME": "synthetic-admin",
            "CAMPLY_LOGIN_PASSWORD": "synthetic-password",
            "CAMPLY_SESSION_SECRET": "synthetic-session-signing-secret-for-smoke",
            "CAMPLY_SESSION_COOKIE_SECURE": "false",
            "CAMPLY_CORS_ORIGINS": f'["{origin}"]',
            "CAMPLY_HEARTBEAT_INTERVAL": "1",
            "CAMPLY_TARGET_COOLDOWN": "55",
            "CAMPLY_SENTRY_DSN": "",
            "PUSHOVER_APP_TOKEN": "synthetic",
            "CAMPLY_SYNTHETIC_ORIGIN": f"http://127.0.0.1:{upstream.server_port}",
        }
        audit = "import importlib.metadata as m; import sys; import backend.app; import worker.runtime; import worker.outbox; names={d.metadata['Name'].lower().replace('_','-') for d in m.distributions()}; assert not names & {'celery','redis','prometheus-client','psycopg','psycopg-binary'}; assert not any(n.split('.')[0] in {'celery','redis','prometheus_client','psycopg'} for n in sys.modules)"
        audited = subprocess.run(
            [str(python), "-c", audit],
            cwd=tmp_path,
            env=env,
            check=False,
            capture_output=True,
        )
        assert audited.returncode == 0, audited.stderr.decode()
        log = stack.enter_context((tmp_path / "application.log").open("wb"))

        def start() -> subprocess.Popen[bytes]:
            """Launch the installed app outside the checkout with real migrations."""
            process = subprocess.Popen(
                [
                    str(python),
                    str(Path(__file__).with_name("standalone_fixture.py")),
                    "--port",
                    origin.rsplit(":", 1)[1],
                ],
                cwd=tmp_path,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            stack.callback(_stop, process)
            _wait(lambda: httpx.get(origin + "/api/health").is_success)
            return process

        process = start()
        _verify_map_worker(core, origin)
        _exercise_scans(
            origin,
            stack,
            availability_gate,
            delivery_gate,
            checks,
            deliveries,
            start,
            rows,
            process,
        )
        screenshot = root / "tmp/standalone-smoke.png"
        screenshot.parent.mkdir(exist_ok=True)
        browser_result = subprocess.run(
            ["pnpm", "exec", "tsx", "scripts/standalone-live-smoke.ts"],
            cwd=root / "frontend",
            env={
                **os.environ,
                "CAMPLY_SMOKE_ORIGIN": origin,
                "CAMPLY_SMOKE_SCREENSHOT": str(screenshot),
            },
            check=False,
            timeout=90,
        )
        assert browser_result.returncode == 0
