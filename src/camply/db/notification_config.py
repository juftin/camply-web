"""Shared ntfy deployment defaults used independently by API and worker runtimes."""

from typing import ClassVar
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def validate_ntfy_url(value: str) -> str:
    """Normalize HTTP(S) server bases without credentials, queries or fragments."""
    value = value.strip().rstrip("/")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or any(char.isspace() or not char.isprintable() for char in value)
    ):
        raise ValueError(
            "Use an HTTP(S) server URL without credentials, query or fragment"
        )
    _ = parsed.port
    return value


class NtfyConfig(BaseSettings):
    """Public subscription default and optional private publishing override."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CAMPLY_NTFY_"
    )
    subscription_url: str = "https://ntfy.sh"
    publish_url: str | None = Field(default=None, repr=False)

    @field_validator("publish_url", mode="before")
    @classmethod
    def empty_publish_url(cls, value: str | None) -> str | None:
        """An empty deployment override uses the public subscription server."""
        return value or None

    @field_validator("subscription_url", "publish_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        """Validate deployment URLs using the same rules as custom servers."""
        return validate_ntfy_url(value) if value is not None else None

    def publish_server(self, custom_server: str | None) -> str:
        """Use custom servers for both directions, otherwise apply deployment defaults."""
        return custom_server or self.publish_url or self.subscription_url

    def subscription_server(self, custom_server: str | None) -> str:
        """Expose only a public subscription server to users."""
        return custom_server or self.subscription_url


ntfy_config = NtfyConfig()
