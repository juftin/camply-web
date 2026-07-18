"""
Backend Application Configuration via pydantic-settings.
"""

from enum import Enum
from typing import ClassVar, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthMode(str, Enum):
    """Authentication mode — basic, local, or Auth0."""

    BASIC = "basic"
    LOCAL = "local"
    AUTH0 = "auth0"


class BackendConfig(BaseSettings):
    """Configuration for the FastAPI backend application."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CAMPLY_",
        case_sensitive=False,
    )

    # Deployment environment
    environment: str = "local"
    debug: bool = True

    # Authentication
    auth_mode: AuthMode = AuthMode.BASIC
    basic_auth_username: str = "admin"
    basic_auth_password: str = "camply"
    auth0_domain: Optional[str] = None
    auth0_audience: Optional[str] = None
    auth0_client_id: Optional[str] = None
    admin_email: str = "admin@camply.local"

    # Sentry
    sentry_dsn: Optional[str] = None
    sentry_traces_sample_rate: float = 0.0

    # Prometheus multiprocess
    prometheus_multiproc_dir: Optional[str] = None


backend_config = BackendConfig()
