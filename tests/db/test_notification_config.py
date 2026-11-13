"""Private publishing defaults and public subscription defaults resolve separately."""

import pytest
from pydantic import ValidationError

from camply.db.notification_config import NtfyConfig


def test_ntfy_environment_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CAMPLY_NTFY_SUBSCRIPTION_URL", "https://public.example.test/push/"
    )
    monkeypatch.setenv("CAMPLY_NTFY_PUBLISH_URL", "http://ntfy.internal:80/publish/")
    config = NtfyConfig()
    assert config.subscription_server(None) == "https://public.example.test/push"
    assert config.publish_server(None) == "http://ntfy.internal:80/publish"
    assert "ntfy.internal" not in repr(config)
    assert (
        config.publish_server("https://custom.example.test")
        == "https://custom.example.test"
    )
    assert (
        config.subscription_server("https://custom.example.test")
        == "https://custom.example.test"
    )
    monkeypatch.setenv("CAMPLY_NTFY_PUBLISH_URL", "")
    assert NtfyConfig().publish_server(None) == "https://public.example.test/push"
    monkeypatch.delenv("CAMPLY_NTFY_PUBLISH_URL")
    assert NtfyConfig().publish_server(None) == "https://public.example.test/push"


@pytest.mark.parametrize("field", ["publish_url", "subscription_url"])
def test_ntfy_deployment_url_validation(field: str) -> None:
    with pytest.raises(ValidationError):
        NtfyConfig(**{field: "https://user:secret@example.test"})
