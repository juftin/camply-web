"""
Configuration management for the camply CLI.

Loads persisted settings from the user application directory and merges
them with environment variables.
"""

from pathlib import Path
from typing import ClassVar

import platformdirs
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_APP_NAME: str = "camply"
# Application identifier for platform directories.

_CONFIG_FILENAME: str = "config.json"
# Filename for persisted user configuration.


def get_config_dir() -> Path:
    """
    Get the directory path where camply configuration is stored.

    Returns
    -------
    Path
        Directory path for camply user configuration.
    """
    path = Path(platformdirs.user_config_dir(appname=_APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_file_path() -> Path:
    """
    Get the full file path to the JSON configuration file.

    Returns
    -------
    Path
        File path to the persisted configuration file.
    """
    return get_config_dir() / _CONFIG_FILENAME


class CamplySettings(BaseSettings):
    """
    Application settings for camply CLI operations.

    Attributes
    ----------
    pushover_user_key : str | None
        User key token for Pushover push notifications.
    pushover_app_token : str | None
        Application token for Pushover message dispatch.
    default_provider : str
        Default booking provider name.
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CAMPLY_",
        case_sensitive=False,
        extra="ignore",
    )

    pushover_user_key: str | None = Field(default=None)
    pushover_app_token: str | None = Field(default=None)
    default_provider: str = Field(default="recreation_gov")


def load_settings() -> CamplySettings:
    """
    Load persisted configuration file merged with environment variables.

    Returns
    -------
    CamplySettings
        Populated settings model.
    """
    config_file = get_config_file_path()
    file_data: dict[str, str] = {}
    if config_file.is_file():
        try:
            raw = config_file.read_text(encoding="utf-8")
            file_data = CamplySettings.model_validate_json(raw).model_dump(
                exclude_none=True
            )
        except Exception:
            file_data = {}

    return CamplySettings(**file_data)


def save_settings(settings: CamplySettings) -> Path:
    """
    Persist application settings to the user's config directory.

    Parameters
    ----------
    settings : CamplySettings
        Settings model to save to disk.

    Returns
    -------
    Path
        Path to the saved configuration file.
    """
    config_file = get_config_file_path()
    json_data = settings.model_dump_json(indent=2)
    config_file.write_text(json_data, encoding="utf-8")
    return config_file
