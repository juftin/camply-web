"""Check effective file-mode channel selection and credential preflight."""

import json

import pytest

from camply.cli.yaml_config import ConfigError, prepare_searches
from tests.cli.test_yaml_config import SEARCH


def test_effective_channels(tmp_path, monkeypatch):
    path = tmp_path / "trips.yaml"
    path.write_text(
        json.dumps(
            {
                "defaults": {"notifications": ["ntfy"]},
                "version": 2,
                "searches": [
                    SEARCH | {"provider": "ReserveCaliforniaProvider"},
                    SEARCH | {"name": "push", "notifications": ["pushover"]},
                    SEARCH | {"name": "quiet", "notifications": []},
                ],
            }
        )
    )
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    with pytest.raises(
        ConfigError, match=r"'trip' \(ReserveCalifornia\).*notifications.*NTFY_TOPIC"
    ):
        prepare_searches(path)
    monkeypatch.setenv("NTFY_TOPIC", "synthetic")
    monkeypatch.setenv("PUSHOVER_USER_KEY", "synthetic")
    monkeypatch.setenv("PUSHOVER_APP_TOKEN", "synthetic")
    assert [item.notifications.channels for item in prepare_searches(path)] == [
        ("ntfy",),
        ("pushover",),
        (),
    ]
