"""Verify beat health reflects completed ticks and clean scheduler shutdown."""

import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from celery import Celery
from celery.beat import PersistentScheduler

from camply.worker.scheduler import HealthScheduler


def test_scheduler_heartbeat_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An idle native scheduler still reports progress and removes its marker on close."""
    path = tmp_path / "health" / "beat.json"
    monkeypatch.setenv("CAMPLY_BEAT_HEALTH_FILE", str(path))
    app = Celery("synthetic", broker="memory://")
    app.conf.timezone = "UTC"
    scheduler = HealthScheduler(
        app=app,
        schedule_filename=str(tmp_path / "schedule"),
        max_interval=30,
    )
    try:
        monkeypatch.setattr("camply.worker.scheduler.time.time", lambda: 100.0)
        assert scheduler.tick() <= 30
        assert json.loads(path.read_text()) == {"pid": os.getpid(), "timestamp": 100.0}
        monkeypatch.setattr("camply.worker.scheduler.time.time", lambda: 110.0)
        scheduler.tick()
        assert json.loads(path.read_text())["timestamp"] == 110.0
        assert list(path.parent.iterdir()) == [path]
    finally:
        scheduler.close()
        app.close()
    assert not path.exists()


def test_failed_tick_does_not_refresh_heartbeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A blocked or failed scheduling loop cannot be hidden by a separate heartbeat."""
    path = tmp_path / "beat.json"
    path.write_text("synthetic previous heartbeat")
    monkeypatch.setenv("CAMPLY_BEAT_HEALTH_FILE", str(path))
    monkeypatch.setattr(
        PersistentScheduler,
        "tick",
        Mock(side_effect=RuntimeError("synthetic tick failure")),
    )
    scheduler = object.__new__(HealthScheduler)
    with pytest.raises(RuntimeError, match="tick failure"):
        scheduler.tick()
    assert path.read_text() == "synthetic previous heartbeat"


def test_failed_replace_keeps_previous_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed atomic publish preserves the old heartbeat and removes temporary files."""
    path = tmp_path / "beat.json"
    path.write_text("synthetic previous heartbeat")
    monkeypatch.setenv("CAMPLY_BEAT_HEALTH_FILE", str(path))
    monkeypatch.setattr(PersistentScheduler, "tick", Mock(return_value=30))
    monkeypatch.setattr(
        os, "replace", Mock(side_effect=OSError("synthetic write failure"))
    )
    scheduler = object.__new__(HealthScheduler)
    with pytest.raises(OSError, match="write failure"):
        scheduler.tick()
    assert path.read_text() == "synthetic previous heartbeat"
    assert list(tmp_path.iterdir()) == [path]
