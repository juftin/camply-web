"""Isolated Celery worker with synthetic tasks for the admin monitoring smoke test."""

import os
from typing import Any

from celery import Celery

import camply.worker.telemetry  # noqa: F401
from camply.worker.metrics import start_metrics_server

app = Celery("admin_smoke", broker=os.environ["CAMPLY_VALKEY_URL"])
app.conf.update(
    task_ignore_result=True, task_serializer="json", accept_content=["json"]
)


@app.task(name="admin_smoke.failure")
def failure() -> None:
    """Exercise the real failure and post-run signal sequence."""
    raise ValueError("Synthetic smoke failure")


@app.task(bind=True, name="admin_smoke.retry")
def retry_once(self: Any) -> dict[str, str]:
    """Exercise two attempts under the same Celery task ID."""
    if self.request.retries == 0:
        raise self.retry(countdown=0, max_retries=1)
    return {"status": "success"}


if __name__ == "__main__":
    start_metrics_server(port=int(os.environ["CAMPLY_SMOKE_METRICS_PORT"]))
    app.worker_main(
        [
            "worker",
            "--pool=solo",
            "--concurrency=1",
            "--hostname=admin-smoke",
            "--loglevel=warning",
        ]
    )
