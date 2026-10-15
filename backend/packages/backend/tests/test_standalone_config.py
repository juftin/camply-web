"""Runtime selection must be explicit and independent of authentication."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.config import BackendConfig, RuntimeMode


def test_runtime_defaults_to_distributed() -> None:
    """Keep existing deployments on their current execution mode."""
    assert BackendConfig().runtime_mode == "distributed"


def test_standalone_does_not_select_authentication(tmp_path: Path) -> None:
    """Choosing a host runtime must preserve owner-selected authentication."""
    config = BackendConfig(runtime_mode=RuntimeMode.STANDALONE, frontend_dir=tmp_path)
    assert config.auto_login
    assert config.frontend_dir == tmp_path


@pytest.mark.parametrize(
    "settings",
    [{"runtime_mode": "other"}, {"heartbeat_interval": 0}, {"target_cooldown": 0}],
)
def test_invalid_runtime_settings_are_rejected(settings: dict[str, object]) -> None:
    """Reject invalid runtime names and timing that would spin the scheduler."""
    with pytest.raises(ValidationError):
        BackendConfig.model_validate(settings)
