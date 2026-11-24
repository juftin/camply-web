"""Opt-in CLI health probes against real workers, beat, and an isolated Valkey."""

import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Callable
from contextlib import ExitStack
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("CAMPLY_HEALTHCHECK_SMOKE") != "1" or os.name == "nt",
    reason="Run task backend:healthcheck:test on Unix with Docker",
)


def _wait(check: Callable[[], bool], *, timeout: float = 30) -> None:
    """Wait for a probe to observe a service transition within a fixed deadline."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.2)
    raise AssertionError("CLI healthcheck transition timed out")


def _stop(process: subprocess.Popen[bytes]) -> None:
    """Resume, terminate, and reap only a test-owned process group."""
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGCONT)
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def _broker(stack: ExitStack) -> tuple[str, str]:
    """Start a disposable loopback broker and return its container and host port."""
    container = subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--rm",
            "--publish",
            "127.0.0.1::6379",
            "valkey/valkey:9-alpine",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout.strip()
    stack.callback(
        subprocess.run,
        ["docker", "rm", "--force", container],
        capture_output=True,
        check=False,
        timeout=30,
    )
    address = subprocess.run(
        ["docker", "port", container, "6379"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    ).stdout.strip()
    port = address.rsplit(":", 1)[1]
    return container, port


def test_cli_worker_and_beat_health(tmp_path: Path) -> None:
    """Detect missing local workers, frozen beat loops, and clean or forced shutdown."""
    with ExitStack() as stack:
        container, port = _broker(stack)
        env = {
            key: value
            for key, value in os.environ.items()
            if key in {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL"}
        }
        heartbeat = tmp_path / "beat.json"
        env.update(
            CAMPLY_VALKEY_URL=f"redis://127.0.0.1:{port}/0",
            CAMPLY_DB_HOST=str(tmp_path / "synthetic.sqlite"),
            CAMPLY_METRICS_PORT="0",
            CAMPLY_HEARTBEAT_INTERVAL="3600",
            CAMPLY_BEAT_HEALTH_FILE=str(heartbeat),
        )
        cli = [str(Path(sys.executable).with_name("camply")), "serve"]

        def launch(role: str, *args: str) -> subprocess.Popen[bytes]:
            """Launch a real role with private logs and register bounded cleanup."""
            log = stack.enter_context(
                (tmp_path / f"{role}-{time.monotonic_ns()}.log").open("wb")
            )
            process = subprocess.Popen(
                [*cli, role, *args],
                env=env,
                cwd=tmp_path,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            stack.callback(_stop, process)
            return process

        def healthy(role: str, *args: str) -> bool:
            """Run the public CLI probe in the same environment as its serving role."""
            result = subprocess.run(
                [*cli, "healthcheck", role, *args],
                env=env,
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            assert result.returncode in (0, 1), result.stderr
            return result.returncode == 0

        try:
            worker_args = (
                "--pool=solo",
                "--concurrency=1",
                "--without-gossip",
                "--without-mingle",
            )
            local = launch("worker", *worker_args)
            other = launch("worker", *worker_args, "--hostname=synthetic-other@%h")
            _wait(lambda: healthy("worker", "--timeout=3"))
            other_target = f"synthetic-other@{socket.gethostname()}"
            _wait(
                lambda: healthy("worker", "--destination", other_target, "--timeout=3")
            )
            local.terminate()
            local.wait(timeout=15)
            assert not healthy("worker", "--timeout=3")
            assert healthy("worker", "--destination", other_target, "--timeout=3")
            assert other.poll() is None

            beat = launch(
                "beat", "--schedule", str(tmp_path / "schedule"), "--max-interval=1"
            )
            _wait(lambda: healthy("beat", "--max-age=2"))
            beat.send_signal(signal.SIGSTOP)
            _wait(lambda: not healthy("beat", "--max-age=2"), timeout=10)
            assert beat.poll() is None
            beat.send_signal(signal.SIGCONT)
            _wait(lambda: healthy("beat", "--max-age=2"))
            beat.terminate()
            beat.wait(timeout=10)
            assert not heartbeat.exists()
            assert not healthy("beat")

            beat = launch(
                "beat", "--schedule", str(tmp_path / "schedule"), "--max-interval=1"
            )
            _wait(lambda: healthy("beat", "--max-age=2"))
            beat.kill()
            beat.wait(timeout=10)
            assert heartbeat.exists()
            assert not healthy("beat")
            subprocess.run(
                ["docker", "stop", "--time", "1", container],
                capture_output=True,
                check=True,
                timeout=10,
            )
            assert not healthy("worker", "--destination", other_target, "--timeout=3")
        except Exception:
            for log in tmp_path.glob("*.log"):
                print(log.name, log.read_text())
            raise
