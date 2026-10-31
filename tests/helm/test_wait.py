"""Verify startup gates fail closed without requiring access to a Kubernetes cluster."""

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def gate() -> ModuleType:
    """Load the exact standard-library script mounted by the chart."""
    path = Path(__file__).resolve().parents[2] / "deploy/helm/files/wait.py"
    spec = importlib.util.spec_from_file_location("camply_chart_wait", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "status",
    [
        {},
        {"active": 1},
        {"failed": 1},
        {"succeeded": 1},
        {"conditions": [{"type": "Complete", "status": "False"}]},
    ],
)
def test_incomplete_job_blocks(gate: ModuleType, status: dict[str, object]) -> None:
    """Neither an old API response nor a retried failed attempt releases the barrier."""
    assert gate.job_complete(status) is False


def test_complete_job_releases_gate(gate: ModuleType) -> None:
    """Only the controller's Complete=True condition releases application startup."""
    assert (
        gate.job_complete({"conditions": [{"type": "Complete", "status": "True"}]})
        is True
    )


def test_failed_job_stops_startup(gate: ModuleType) -> None:
    """A terminal migration failure cannot be mistaken for a successful retry."""
    with pytest.raises(RuntimeError, match="Migration Job failed"):
        gate.job_complete({"conditions": [{"type": "Failed", "status": "True"}]})


def test_wait_timeout(gate: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    """An unavailable dependency fails closed when the bounded wait expires."""
    monkeypatch.setattr(gate.time, "monotonic", lambda: 10)
    with pytest.raises(TimeoutError):
        gate.wait_until(lambda: False, deadline=9)


def test_wait_retries_then_completes(
    gate: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resource creation and transient connection failures are retried."""
    checks: Iterator[bool] = iter([False, False, True])
    sleep = MagicMock()
    monkeypatch.setattr(gate.time, "sleep", sleep)
    monkeypatch.setattr(gate.time, "monotonic", lambda: 0)
    gate.wait_until(lambda: next(checks), deadline=10)
    assert sleep.call_count == 2


def test_job_failure_never_checks_background_services(
    gate: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A healthy old API cannot let a worker skip a failed upgrade's migration barrier."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "wait.py",
            "--namespace",
            "test",
            "--job",
            "new-migration",
            "--background",
            "--api-url",
            "http://backend/api/health",
        ],
    )
    monkeypatch.setattr(
        gate,
        "migration_ready",
        MagicMock(side_effect=RuntimeError("Migration Job failed")),
    )
    tcp = MagicMock(return_value=True)
    api = MagicMock(return_value=True)
    monkeypatch.setattr(gate, "tcp_ready", tcp)
    monkeypatch.setattr(gate, "api_ready", api)
    with pytest.raises(RuntimeError, match="Migration Job failed"):
        gate.main()
    tcp.assert_not_called()
    api.assert_not_called()


@pytest.mark.parametrize(
    "code,retry", [(404, True), (503, True), (401, False), (403, False)]
)
def test_api_errors(
    gate: ModuleType, monkeypatch: pytest.MonkeyPatch, code: int, retry: bool
) -> None:
    """Missing Jobs and transient API outages retry; permission failures stop startup."""
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "127.0.0.1")
    monkeypatch.setattr(gate.Path, "read_text", lambda _: "synthetic-token")
    monkeypatch.setattr(gate.ssl, "create_default_context", lambda **_: None)
    error = gate.urllib.error.HTTPError(
        "https://test.invalid", code, "synthetic", {}, None
    )
    monkeypatch.setattr(gate.urllib.request, "urlopen", MagicMock(side_effect=error))
    if retry:
        assert gate.migration_ready("test", "migration") is False
    else:
        with pytest.raises(RuntimeError, match="access denied"):
            gate.migration_ready("test", "migration")
