"""Block new processes until their migration Job and runtime dependencies are ready."""

import argparse
import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path
from typing import Any


def job_complete(status: dict[str, Any]) -> bool:
    """Accept only completion; failed attempts alone may still be retried by the Job."""
    conditions = status.get("conditions", [])
    if any(c.get("type") == "Failed" and c.get("status") == "True" for c in conditions):
        raise RuntimeError("Migration Job failed; inspect its logs before retrying")
    return any(
        c.get("type") == "Complete" and c.get("status") == "True" for c in conditions
    )


def migration_ready(namespace: str, job: str) -> bool:
    """Read exactly one namespaced Job using a token mounted only in this init container."""
    credentials = Path("/var/run/camply-migration")
    host = os.environ["KUBERNETES_SERVICE_HOST"]
    if ":" in host:
        host = f"[{host}]"
    port = os.environ.get("KUBERNETES_SERVICE_PORT_HTTPS", "443")
    url = f"https://{host}:{port}/apis/batch/v1/namespaces/{namespace}/jobs/{job}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {credentials.joinpath('token').read_text().strip()}"
        },
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=5,
            context=ssl.create_default_context(cafile=str(credentials / "ca.crt")),
        ) as response:
            return job_complete(json.load(response).get("status", {}))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError(
                "Migration Job access denied; check migration-wait RBAC"
            ) from None
        return False
    except (OSError, ValueError):
        return False


def tcp_ready(host: str, port: int) -> bool:
    """Bound connection attempts while waiting for a database or broker listener."""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def api_ready(url: str) -> bool:
    """Require a successful post-migration API health response."""
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == HTTPStatus.OK
    except OSError:
        return False


def wait_until(check: Callable[[], bool], *, deadline: float) -> None:
    """Retry unavailable dependencies, failing closed when the startup deadline expires."""
    while not check():
        if time.monotonic() >= deadline:
            raise TimeoutError("Startup dependency wait timed out")
        time.sleep(2)


def main() -> None:
    """Wait for PostgreSQL alone, or for a release Job followed by background dependencies."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", action="store_true")
    parser.add_argument("--namespace")
    parser.add_argument("--job")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--api-url")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    deadline = time.monotonic() + args.timeout
    if args.database:
        wait_until(
            lambda: tcp_ready(
                os.environ["CAMPLY_DB_HOST"], int(os.environ["CAMPLY_DB_PORT"])
            ),
            deadline=deadline,
        )
        return
    wait_until(lambda: migration_ready(args.namespace, args.job), deadline=deadline)
    if args.background:
        broker = urllib.parse.urlsplit(os.environ["CAMPLY_VALKEY_URL"])
        if not broker.hostname:
            raise ValueError("CAMPLY_VALKEY_URL must include a broker hostname")
        wait_until(
            lambda: tcp_ready(str(broker.hostname), broker.port or 6379),
            deadline=deadline,
        )
        wait_until(lambda: api_ready(args.api_url), deadline=deadline)


if __name__ == "__main__":
    main()
