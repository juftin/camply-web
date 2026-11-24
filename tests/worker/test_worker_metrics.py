"""Tests for worker Prometheus multiprocess metrics lifecycle."""

from __future__ import annotations

import multiprocessing
import os
import subprocess
import sys
from pathlib import Path

import pytest
from prometheus_client.parser import text_string_to_metric_families


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="Prefork worker multiprocess test requires POSIX fork",
)
def test_importing_celery_app_does_not_wipe_worker_metrics(tmp_path: Path) -> None:
    """Secondary CLI processes (like healthchecks) must not delete live worker .db files."""
    multiproc_dir = tmp_path / "multiproc"
    multiproc_dir.mkdir()
    script = f"""
import multiprocessing
import os
import subprocess
import sys

os.environ["PROMETHEUS_MULTIPROC_DIR"] = ""
os.environ["CAMPLY_PROMETHEUS_MULTIPROC_DIR"] = {str(multiproc_dir)!r}

import camply.worker.metrics as wm

ctx = multiprocessing.get_context("fork")
ready = ctx.Queue()
proceed = ctx.Queue()

def worker_child():
    wm.CELERY_TASKS_TOTAL.labels(task_name="search.schedule_checks", status="success").inc()
    ready.put("first")
    proceed.get()
    wm.CELERY_TASKS_TOTAL.labels(task_name="search.schedule_checks", status="success").inc()
    ready.put("second")

proc = ctx.Process(target=worker_child)
proc.start()
assert ready.get() == "first"

# Simulate a concurrent process importing celery_app (e.g. celery inspect / healthcheck)
subprocess.run([sys.executable, "-c", "import camply.worker.celery_app"], check=True)

proceed.put("go")
assert ready.get() == "second"
proc.join(timeout=5)
assert proc.exitcode == 0

from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client.multiprocess import MultiProcessCollector

reg = CollectorRegistry()
MultiProcessCollector(reg)
sys.stdout.write(generate_latest(reg).decode())
"""
    output = subprocess.check_output([sys.executable, "-c", script], text=True)
    samples = [
        sample
        for family in text_string_to_metric_families(output)
        for sample in family.samples
    ]
    assert any(
        s.name == "camply_celery_tasks_total"
        and s.labels == {"task_name": "search.schedule_checks", "status": "success"}
        and s.value == 2.0
        for s in samples
    ), output


def test_cleanup_stale_multiproc_files_and_shutdown_hook(tmp_path: Path) -> None:
    """Dead PIDs are cleaned on startup and exiting worker children drop live gauges."""
    dead_file = tmp_path / "counter_999999.db"
    live_file = tmp_path / f"counter_{os.getpid()}.db"
    dead_file.write_bytes(b"stale")
    live_file.write_bytes(b"live")
    child_gauge = tmp_path / "gauge_livesum_424242.db"
    child_gauge.write_bytes(b"gauge")

    script = f"""
import os
os.environ["PROMETHEUS_MULTIPROC_DIR"] = {str(tmp_path)!r}
from camply.worker.metrics import _cleanup_stale_multiproc_files, _on_worker_process_shutdown

_cleanup_stale_multiproc_files({str(tmp_path)!r})
_on_worker_process_shutdown(pid=424242)
_on_worker_process_shutdown(pid=424242)
"""
    subprocess.run([sys.executable, "-c", script], check=True)
    assert not dead_file.exists()
    assert live_file.exists()
    assert not child_gauge.exists()


def test_empty_multiproc_env_falls_back_to_in_process_metrics(
    tmp_path: Path,
) -> None:
    """Empty PROMETHEUS_MULTIPROC_DIR must not create .db files in cwd."""
    script = """
import os
os.environ["PROMETHEUS_MULTIPROC_DIR"] = ""
os.environ.pop("CAMPLY_PROMETHEUS_MULTIPROC_DIR", None)
import camply.worker.metrics as wm
wm.TARGETS_DISCOVERED_TOTAL.inc()
assert wm._multiproc_dir is None
assert "PROMETHEUS_MULTIPROC_DIR" not in os.environ
"""
    subprocess.run([sys.executable, "-c", script], cwd=tmp_path, check=True)
    assert list(tmp_path.glob("*.db")) == []
