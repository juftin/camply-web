"""
Backend Application Configuration via pydantic-settings.
"""

from enum import Enum
from typing import ClassVar, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthMode(str, Enum):
    """Owner-selected authentication: automatic login, sessions, or Auth0."""

    NONE = "none"
    SESSION = "session"
    AUTH0 = "auth0"


class BackendConfig(BaseSettings):
    """Configuration for the FastAPI backend application."""

    _MIN_SESSION_SECRET_LENGTH: ClassVar[int] = 32
    """Minimum configured signing-secret length for shared-account sessions."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CAMPLY_",
        case_sensitive=False,
    )

    # Deployment environment
    environment: str = "local"
    debug: bool = True

    # Authentication
    auth_mode: AuthMode = AuthMode.NONE
    invite_only: bool = False
    """Require an invitation before users can manage scans."""
    auth0_domain: Optional[str] = None
    auth0_audience: Optional[str] = None
    auth0_client_id: Optional[str] = None
    admin_email: str = "admin@camply.local"
    login_username: Optional[str] = None
    """Shared account username for in-app session login."""
    login_password: Optional[str] = Field(default=None, repr=False)
    """Shared account password, supplied through environment configuration."""
    session_secret: Optional[str] = Field(default=None, repr=False)
    """Signing secret for session cookies; at least 32 characters."""
    session_max_age: int = Field(default=43200, ge=1)
    """Absolute cookie-session lifetime in seconds (12 hours by default)."""
    session_cookie_secure: bool = True
    """Require HTTPS for session cookies; disable explicitly for local HTTP."""
    allowed_origins: list[str] = ["http://localhost:5173", "https://camply.juftin.dev"]
    """Frontend origins allowed for CORS and in-app login requests."""

    # Sentry
    sentry_dsn: Optional[str] = None
    sentry_traces_sample_rate: float = 0.0

    # Prometheus multiprocess
    prometheus_multiproc_dir: Optional[str] = None

    @property
    def auto_login(self) -> bool:
        """Use the shared admin identity when automatic login is selected."""
        return self.auth_mode == AuthMode.NONE

    @property
    def signup_enabled(self) -> bool:
        """Offer account registration only when Auth0 handles login."""
        return self.auth_mode == AuthMode.AUTH0

    @model_validator(mode="after")
    def validate_auth_config(self) -> "BackendConfig":
        """Reject incomplete configuration for the selected authentication mode."""
        if not self.auto_login and self.auth_mode == AuthMode.AUTH0:
            if not all((self.auth0_domain, self.auth0_audience, self.auth0_client_id)):
                raise ValueError("Auth0 requires domain, audience, and client ID")
        if self.auth_mode == AuthMode.SESSION:
            if not self.login_username or not self.login_password:
                raise ValueError("Session login requires username and password")
            if (
                not self.session_secret
                or len(self.session_secret) < self._MIN_SESSION_SECRET_LENGTH
            ):
                raise ValueError(
                    "Session login requires a signing secret of at least 32 characters"
                )
        return self


backend_config = BackendConfig()
