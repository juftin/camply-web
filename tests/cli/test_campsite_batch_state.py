"""Check per-search state paths before batch startup."""

import json

import pytest

from camply.cli.yaml_config import ConfigError, prepare_searches
from tests.cli.test_yaml_config import SEARCH


def test_relative_state_paths_and_conflicts(tmp_path):
    path = tmp_path / "trips.yaml"
    first = SEARCH | {"state_file": "alerts/first.json"}
    second = SEARCH | {"name": "second", "state_file": "alerts/second.json"}

    def write():
        path.write_text(json.dumps({"searches": [first, second]}))

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
                "searches": [
                    SEARCH | {"state_file": "trip.json", "notifications": ["ntfy"]}
                ]
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
