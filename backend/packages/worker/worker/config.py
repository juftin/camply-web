"""
Worker Configuration via pydantic-settings
"""

from typing import ClassVar, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerConfig(BaseSettings):
    """
    Configuration for the Celery worker and notification services.
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CAMPLY_",
        case_sensitive=False,
    )

    # Valkey / Redis broker URL
    valkey_url: str = "redis://localhost:6379/0"

    # Sentry
    sentry_dsn: Optional[str] = None
    sentry_traces_sample_rate: float = 0.0

    # Deployment
    environment: str = "local"

    # Heartbeat interval for target discovery (seconds)
    heartbeat_interval: int = Field(
        default=300,
        validation_alias=AliasChoices(
            "camply_heartbeat_interval",
            "camply_search_interval",
            "heartbeat_interval",
            "search_interval",
        ),
        description="Heartbeat interval for target discovery in seconds (defaults to 300s = 5m).",
    )
    """Heartbeat interval in seconds for target discovery and availability searching."""

    # Lock timeout in seconds (prevents ghost locks)
    lock_timeout: int = 120

    # How stale a target must be before re-checking (seconds)
    target_cooldown: int = Field(
        default=55,
        validation_alias=AliasChoices(
            "camply_target_cooldown",
            "target_cooldown",
        ),
        description="How stale a target must be before re-checking in seconds.",
    )
    """Minimum seconds elapsed before a previously checked target is re-scanned."""

    # Prometheus metrics HTTP server port (0 = disabled)
    metrics_port: int = 8001

    @property
    def search_interval(self) -> int:
        """
        Alias for heartbeat_interval representing campsite search polling cadence.

        Returns
        -------
        int
            Search polling interval in seconds.
        """
        return self.heartbeat_interval


worker_config = WorkerConfig()
