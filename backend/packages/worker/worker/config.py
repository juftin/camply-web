# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Worker Configuration via pydantic-settings
"""

from typing import ClassVar, Optional

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
    heartbeat_interval: int = 60

    # Lock timeout in seconds (prevents ghost locks)
    lock_timeout: int = 120

    # How stale a target must be before re-checking (seconds)
    target_cooldown: int = 55


worker_config = WorkerConfig()
