"""
Unit tests for WorkerConfig timing and interval settings.
"""

import pytest
from pydantic import ValidationError

from worker.config import WorkerConfig


def test_notification_defaults_and_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default to summaries and allow operator-configured booking links."""
    monkeypatch.delenv("CAMPLY_NOTIFICATION_MODE", raising=False)
    assert WorkerConfig().notification_mode == "summary"
    monkeypatch.setenv("CAMPLY_NOTIFICATION_MODE", "direct")
    monkeypatch.setenv("CAMPLY_APP_URL", "https://camply.example/prefix/")
    config = WorkerConfig()
    assert config.notification_mode == "direct"
    assert str(config.app_url) == "https://camply.example/prefix/"


@pytest.mark.parametrize(
    "value",
    [
        "ftp://camply.example",
        "/relative",
        "https://camply.example?query=1",
        "https://camply.example#hash",
    ],
)
def test_invalid_app_url(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """Reject non-HTTP URLs and query/fragment bases that would corrupt links."""
    monkeypatch.setenv("CAMPLY_APP_URL", value)
    with pytest.raises(ValidationError):
        WorkerConfig()


class TestWorkerConfigTiming:
    """
    Test suite for WorkerConfig timing intervals and environment overrides.
    """

    def test_default_timing_intervals(self) -> None:
        """
        Verify default timing values for heartbeat interval and target cooldown.

        Heartbeat interval should default to 300 seconds (5 minutes).
        Target cooldown should default to 55 seconds.
        """
        config = WorkerConfig()
        assert config.heartbeat_interval == 300
        assert config.target_cooldown == 55

    def test_heartbeat_interval_from_camply_heartbeat_interval_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Verify CAMPLY_HEARTBEAT_INTERVAL environment variable overrides default.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture to temporarily set environment variables.
        """
        monkeypatch.setenv("CAMPLY_HEARTBEAT_INTERVAL", "180")
        config = WorkerConfig()
        assert config.heartbeat_interval == 180

    def test_target_cooldown_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify CAMPLY_TARGET_COOLDOWN environment variable overrides default.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture to temporarily set environment variables.
        """
        monkeypatch.setenv("CAMPLY_TARGET_COOLDOWN", "120")
        config = WorkerConfig()
        assert config.target_cooldown == 120

    def test_explicit_keyword_arguments(self) -> None:
        """
        Verify WorkerConfig initialization via keyword arguments.
        """
        config_heartbeat = WorkerConfig(heartbeat_interval=150)
        assert config_heartbeat.heartbeat_interval == 150
