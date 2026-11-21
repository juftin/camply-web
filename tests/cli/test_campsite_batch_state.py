"""Check per-search state paths before batch startup."""

import json
import os
import stat
from pathlib import Path

import pytest

from camply.cli.notifications import StayDeduplicationState
from camply.cli.yaml_config import ConfigError, prepare_searches
from tests.cli.test_yaml_config import SEARCH


def test_relative_state_paths_and_conflicts(tmp_path):
    path = tmp_path / "trips.yaml"
    first = SEARCH | {"state_file": "alerts/first.json"}
    second = SEARCH | {"name": "second", "state_file": "alerts/second.json"}

    def write():
        path.write_text(json.dumps({"version": 2, "searches": [first, second]}))

    write()
    assert [search.state_file for search in prepare_searches(path)] == [
        tmp_path / "alerts/first.json",
        tmp_path / "alerts/second.json",
    ]
    second["state_file"] = "alerts/../alerts/first.json"
    write()
    with pytest.raises(ConfigError, match="another search"):
        prepare_searches(path)
    second["state_file"] = "trips.yaml"
    write()
    with pytest.raises(ConfigError, match="configuration file"):
        prepare_searches(path)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires a POSIX named pipe")
def test_special_file_uses_memory_only(tmp_path, monkeypatch):
    """Inspect a FIFO without blocking or replacing it on subsequent polls."""
    path = tmp_path / "state.fifo"
    os.mkfifo(path)

    def blocking_read(*args, **kwargs):
        pytest.fail("state loading tried to read the named pipe as a regular file")

    monkeypatch.setattr(Path, "read_text", blocking_read)
    state = StayDeduplicationState.load(path, label="trip")
    assert state.state_file is None
    state.record_cycle([])
    assert stat.S_ISFIFO(path.stat().st_mode)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires a POSIX named pipe")
def test_state_file_replaced_by_fifo_during_open(tmp_path, monkeypatch):
    """The opened descriptor is checked independently of the earlier path stat."""
    path = tmp_path / "state.json"
    path.write_text('{"seen_stays": []}')
    original_open = os.open

    def open_after_path_changes(file, flags, *args, **kwargs):
        if file == path:
            path.unlink()
            os.mkfifo(path)
            assert flags & os.O_NONBLOCK
        return original_open(file, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", open_after_path_changes)
    state = StayDeduplicationState.load(path, label="trip")
    assert state.state_file is None
    state.record_cycle([])
    assert stat.S_ISFIFO(path.stat().st_mode)


def test_failed_state_replace_removes_temporary_file(tmp_path, monkeypatch):
    """A failed publish leaves the prior history and no transient files."""
    path = tmp_path / "state.json"
    path.write_text('{"seen_stays": ["previous"]}')

    def deny_replace(self, target):
        raise PermissionError("synthetic write failure")

    monkeypatch.setattr(Path, "replace", deny_replace)
    state = StayDeduplicationState.load(path, label="trip")
    state.record_cycle([])
    assert list(tmp_path.iterdir()) == [path]
    assert json.loads(path.read_text())["seen_stays"] == ["previous"]


@pytest.mark.asyncio
async def test_failed_checks_preserve_state_and_reopening_alerts(tmp_path, monkeypatch):
    """Failure is distinct from a successful check that confirms closure."""
    from datetime import date
    from unittest.mock import AsyncMock

    from camply.cli.campsite_batch import execute_batch
    from camply.core.search import AvailabilityStay
    from tests.cli.test_search import campground

    path = tmp_path / "trips.yaml"
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "searches": [
                    SEARCH | {"state_file": "trip.json", "notifications": ["ntfy"]}
                ],
            }
        )
    )
    monkeypatch.setenv("NTFY_TOPIC", "synthetic")
    searches = prepare_searches(path)
    stay = AvailabilityStay(
        campground=campground(),
        campsite_id="site",
        campsite_name="Synthetic Campsite",
        arrival=date(2030, 6, 1),
        checkout=date(2030, 6, 2),
        booking_url="https://booking.example.invalid/site",
    )

    def initialize(provider):
        provider.async_client = AsyncMock()

    monkeypatch.setattr(searches[0].provider_class, "__init__", initialize)
    monkeypatch.setattr(
        "camply.cli.campsite_batch.resolve_targets", AsyncMock(return_value=[])
    )
    check = AsyncMock(side_effect=[[stay], RuntimeError("payload"), [stay], [], [stay]])
    monkeypatch.setattr("camply.cli.campsite_batch.check_availability", check)
    deliver = AsyncMock(return_value=True)
    monkeypatch.setattr("camply.cli.notifications.NtfyProvider.send_accepted", deliver)
    for expected in ("ok", "error", "ok", "ok", "ok"):
        assert (await execute_batch(searches, once=True, json_output=True))[0][
            "status"
        ] == expected
    assert deliver.await_count == 2
    assert all("'trip'" in call.args[-1].message for call in deliver.await_args_list)
