"""Opt-in admin smoke test with real Celery, Valkey, Prometheus, HTTP, and Chromium."""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import threading
import time
from contextlib import ExitStack
from pathlib import Path
from typing import Callable, cast

import httpx
import pytest
import redis
import uvicorn
from celery import Celery

from backend.app import app
from backend.config import backend_config
from backend.services import operations, trends

pytestmark = pytest.mark.skipif(
    os.environ.get("CAMPLY_ADMIN_SMOKE") != "1", reason="Run task admin:smoke"
)


def _port() -> int:
    """Choose an unused host port for an isolated test process."""
    with socket.socket() as listener:
        listener.bind(("", 0))
        return int(listener.getsockname()[1])


def _wait(check: Callable[[], bool], timeout: float = 30) -> None:
    """Wait for a real service or worker to satisfy a bounded readiness check."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except (httpx.HTTPError, redis.RedisError, OSError, ValueError):
            pass
        time.sleep(0.25)
    raise AssertionError("Admin smoke readiness check timed out")


def _container(stack: ExitStack, image: str, port: int, args: list[str]) -> int:
    """Start and clean up only a test-owned container on a random loopback port."""
    result = subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--rm",
            "--publish",
            f"127.0.0.1::{port}",
            *args,
            image,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    container_id = result.stdout.strip()
    stack.callback(
        subprocess.run,
        ["docker", "rm", "--force", container_id],
        check=False,
        capture_output=True,
    )
    published = subprocess.check_output(
        ["docker", "port", container_id, str(port)], text=True
    )
    return int(published.strip().rsplit(":", 1)[1])


def _stop(process: subprocess.Popen[bytes]) -> None:
    """Terminate and reap a test-owned worker process."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _verify_task_attempts(celery: Celery, client: redis.Redis) -> None:
    """Verify real failure/retry signals write one event per attempt."""
    failure = celery.send_task("admin_smoke.failure")
    retry = celery.send_task("admin_smoke.retry")
    _wait(lambda: cast(int, client.xlen("camply:telemetry:tasks")) >= 3)
    records = [
        record
        for _, record in cast(
            list[tuple[str, dict[str, str]]], client.xrange("camply:telemetry:tasks")
        )
    ]
    failed = [record for record in records if record["task_id"] == failure.id]
    retried = [record for record in records if record["task_id"] == retry.id]
    assert len(failed) == 1
    assert [record["outcome"] for record in retried] == ["retrying", "success"]
    assert [record["attempt"] for record in retried] == ["1", "2"]
    assert len({record["event_id"] for record in records}) == 3


def _start_api(stack: ExitStack, port: int) -> str:
    """Serve the actual FastAPI app over HTTP and clean up its server thread."""
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    def stop_api() -> None:
        """Stop the test-owned HTTP server before restoring dependencies."""
        server.should_exit = True
        thread.join(timeout=10)

    stack.callback(stop_api)
    origin = f"http://127.0.0.1:{port}"
    _wait(lambda: httpx.get(f"{origin}/api/health").is_success)
    return origin


def test_admin_live_stack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify attempt counts, real inspection, trend queries, and browser suspension flows."""
    root = Path(__file__).resolve().parents[5]
    metrics_port, api_port = _port(), _port()
    with ExitStack() as stack:
        valkey_port = _container(stack, "valkey/valkey:8-alpine", 6379, [])
        broker = f"redis://127.0.0.1:{valkey_port}/0"
        client = redis.Redis.from_url(broker, decode_responses=True)
        stack.callback(client.close)
        _wait(lambda: client.ping() is True)
        monkeypatch.setattr(backend_config, "valkey_url", broker)
        monkeypatch.setattr(backend_config, "admin_email", "admin-smoke@example.test")
        monkeypatch.setattr(operations, "_cached_overview", None)
        monkeypatch.setattr(operations, "_cached_overview_time", 0)
        monkeypatch.setattr(operations, "_cache_lock", asyncio.Lock())
        monkeypatch.setattr(trends, "_TRENDS_CACHE", {})

        log = stack.enter_context((tmp_path / "worker.log").open("wb"))
        worker = subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name("smoke_worker.py"))],
            cwd=root,
            env={
                **os.environ,
                "CAMPLY_VALKEY_URL": broker,
                "CAMPLY_SMOKE_METRICS_PORT": str(metrics_port),
            },
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        stack.callback(_stop, worker)
        celery = Celery("admin_smoke_client", broker=broker)
        stack.callback(celery.close)
        _wait(lambda: bool(celery.control.ping(timeout=0.5)))
        _verify_task_attempts(celery, client)

        config = tmp_path / "prometheus.yml"
        config.write_text(
            f"global:\n  scrape_interval: 1s\nscrape_configs:\n  - job_name: smoke-worker\n    static_configs:\n      - targets: ['host.docker.internal:{metrics_port}']\n"
        )
        extra = ["--volume", f"{config}:/etc/prometheus/prometheus.yml:ro"]
        if sys.platform == "linux":
            extra += ["--add-host", "host.docker.internal:host-gateway"]
        prom_port = _container(
            stack,
            "prom/prometheus@sha256:efd719c99d83b060d9daefdcf00360461adf279f45ef5391f8d111892118753e",
            9090,
            extra,
        )
        monkeypatch.setattr(
            backend_config, "prometheus_url", f"http://127.0.0.1:{prom_port}"
        )
        _wait(
            lambda: httpx.get(
                f"http://127.0.0.1:{prom_port}/api/v1/query",
                params={"query": "camply_application_outcomes_total"},
            )
            .json()
            .get("data", {})
            .get("result", [])
            != []
        )

        failure_count = httpx.get(
            f"http://127.0.0.1:{prom_port}/api/v1/query",
            params={"query": 'sum(camply_celery_tasks_total{status="failure"})'},
        ).json()["data"]["result"][0]["value"][1]
        assert float(failure_count) == 1

        origin = _start_api(stack, api_port)
        profile = httpx.get(f"{origin}/api/me").json()
        scan = httpx.post(
            f"{origin}/api/scans",
            json={
                "provider_id": 1,
                "campground_id": "cg_1",
                "start_date": "2027-06-01",
                "end_date": "2027-06-03",
            },
        )
        assert scan.is_success, scan.text
        overview = httpx.get(f"{origin}/api/admin/operations", timeout=10).json()
        assert overview["inspection_available"]
        assert overview["active_tasks_total"] == 0
        history = httpx.get(f"{origin}/api/admin/operations/tasks").json()
        assert history["total"] == 3
        charts = httpx.get(f"{origin}/api/admin/trends?group=worker", timeout=10).json()
        assert charts["available"]
        assert any(metric["series"] for metric in charts["metrics"])

        subprocess.run(
            ["pnpm", "exec", "tsx", "scripts/admin-live-smoke.ts"],
            cwd=root / "frontend",
            env={
                **os.environ,
                "CAMPLY_API_URL": origin,
                "CAMPLY_SMOKE_USER_ID": profile["id"],
            },
            check=True,
            timeout=90,
        )
        _stop(worker)
        monkeypatch.setattr(operations, "_cached_overview_time", 0)
        stopped = httpx.get(f"{origin}/api/admin/operations", timeout=10).json()
        assert not stopped["inspection_available"]
        assert stopped["stale"]
