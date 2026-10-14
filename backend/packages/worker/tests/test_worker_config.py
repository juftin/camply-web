"""
Unit tests for WorkerConfig timing and interval settings.
"""

import pytest

from worker.config import WorkerConfig


class TestWorkerConfigTiming:
    """
    Test suite for WorkerConfig timing intervals and alias overrides.
    """

    def test_default_timing_intervals(self) -> None:
        """
        Verify default timing values for heartbeat interval and target cooldown.

        Heartbeat interval should default to 300 seconds (5 minutes).
        Target cooldown should default to 55 seconds.
        """
        config = WorkerConfig()
        assert config.heartbeat_interval == 300
        assert config.search_interval == 300
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
        assert config.search_interval == 180

    def test_heartbeat_interval_from_camply_search_interval_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Verify CAMPLY_SEARCH_INTERVAL environment variable overrides default.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
            Pytest fixture to temporarily set environment variables.
        """
        monkeypatch.setenv("CAMPLY_SEARCH_INTERVAL", "600")
        config = WorkerConfig()
        assert config.heartbeat_interval == 600
        assert config.search_interval == 600

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
        assert config_heartbeat.search_interval == 150
