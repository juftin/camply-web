# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Backend Application Configuration via pydantic-settings.
"""

from enum import Enum
from typing import ClassVar, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthMode(str, Enum):
    """Authentication mode — local-only or Auth0."""

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
    auth_mode: AuthMode = AuthMode.LOCAL
    auth0_domain: Optional[str] = None
    auth0_audience: Optional[str] = None
    auth0_client_id: Optional[str] = None
    admin_email: str = "admin@camply.local"

    # Sentry
    sentry_dsn: Optional[str] = None
    sentry_traces_sample_rate: float = 0.0


backend_config = BackendConfig()
