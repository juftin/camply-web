"""Persist the native beat schedule and report completed scheduler-loop ticks."""

import json
import os
import tempfile
import time
from pathlib import Path

from celery.beat import PersistentScheduler


class HealthScheduler(PersistentScheduler):
    """Expose beat liveness without enqueueing tasks or depending on worker replies."""

    def tick(self) -> float:
        """Publish a heartbeat atomically after the native scheduler completes a tick."""
        delay = super().tick()
        path = Path(os.environ["CAMPLY_BEAT_HEALTH_FILE"])
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", dir=path.parent, delete=False
            ) as handle:
                temporary = Path(handle.name)
                json.dump({"pid": os.getpid(), "timestamp": time.time()}, handle)
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return float(delay)

    def close(self) -> None:
        """Sync the schedule and clear the liveness marker on clean shutdown."""
        try:
            super().close()
        finally:
            Path(os.environ["CAMPLY_BEAT_HEALTH_FILE"]).unlink(missing_ok=True)
