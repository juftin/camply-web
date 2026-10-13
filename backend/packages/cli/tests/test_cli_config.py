"""
Tests for CLI configuration management.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from camply.app import cli
from camply.config import CamplySettings, load_settings, save_settings


def test_save_and_load_settings(tmp_path: Path) -> None:
    """Verify settings roundtrip to disk."""
    fake_config_file = tmp_path / "config.json"
    with patch("camply.config.get_config_file_path", return_value=fake_config_file):
        settings = CamplySettings(
            pushover_user_key="user_12345",
            pushover_app_token="app_token_67890",
        )
        save_settings(settings)
        assert fake_config_file.is_file()

        loaded = load_settings()
        assert loaded.pushover_user_key == "user_12345"
        assert loaded.pushover_app_token == "app_token_67890"


def test_configure_command_show(tmp_path: Path) -> None:
    """Verify configure --show prints current settings."""
    fake_config_file = tmp_path / "config.json"
    with patch("camply.config.get_config_file_path", return_value=fake_config_file):
        settings = CamplySettings(
            pushover_user_key="user_abc123",
            pushover_app_token="token_xyz789",
        )
        save_settings(settings)

        runner = CliRunner()
        result = runner.invoke(cli, ["configure", "--show"])
        assert result.exit_code == 0
        assert "user..." in result.output
        assert "toke..." in result.output


def test_configure_command_set_flags(tmp_path: Path) -> None:
    """Verify setting options via CLI flags saves to file."""
    fake_config_file = tmp_path / "config.json"
    with patch("camply.config.get_config_file_path", return_value=fake_config_file):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "configure",
                "--pushover-user-key",
                "new_user_key",
                "--pushover-app-token",
                "new_app_token",
            ],
        )
        assert result.exit_code == 0
        assert "Configuration successfully saved" in result.output

        loaded = load_settings()
        assert loaded.pushover_user_key == "new_user_key"
        assert loaded.pushover_app_token == "new_app_token"
