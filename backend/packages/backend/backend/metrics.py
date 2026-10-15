"""Keep instrumentation optional without importing Prometheus in standalone mode."""

import importlib
from typing import Any

from backend.config import RuntimeMode, backend_config


class NullMetric:
    """Accept existing instrumentation calls when monitoring is intentionally disabled."""

    def inc(self, amount: float = 1) -> None:
        """Ignore a counter update in a runtime without metric collection."""

    def observe(self, value: float) -> None:
        """Ignore a timing sample in a runtime without metric collection."""

    def labels(self, **labels: str) -> "NullMetric":
        """Keep label call sites usable without constructing a registry."""
        return self


def __getattr__(name: str) -> Any:
    """Resolve real instruments only for distributed deployments."""
    if name.startswith("__"):
        raise AttributeError(name)
    if backend_config.runtime_mode == RuntimeMode.STANDALONE:
        if name.isupper():
            return NullMetric()
        raise AttributeError(name)
    return getattr(importlib.import_module("backend._prometheus"), name)
