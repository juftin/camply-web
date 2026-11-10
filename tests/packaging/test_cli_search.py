"""Exercise the installed console script against a real synthetic HTTP server."""

import json
import os
import signal
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from .conftest import Installation, clean_environment


@contextmanager
def upstream() -> Iterator[tuple[str, list[tuple[str, dict[str, Any]]]]]:
    """Serve native UseDirect catalogs and grids, recording actual HTTP payloads."""
    transcript: list[tuple[str, dict[str, Any]]] = []

    class Handler(BaseHTTPRequestHandler):
        """Handle only synthetic provider requests; never proxy to a live service."""

        def log_message(self, format: str, *args: Any) -> None:
            """Keep fixture access logs out of test output."""

        def do_GET(self) -> None:
            """Supply native metadata, including an exact ID beyond the display page."""
            transcript.append((self.path, {}))
            if self.path == "/fd/places":
                data: Any = [
                    {"PlaceId": 1, "Name": "Synthetic Park", "AllowWebBooking": True}
                ]
            elif self.path == "/fd/facilities":
                data = [
                    {
                        "FacilityId": value,
                        "PlaceId": 1,
                        "Name": f"Synthetic Campground {value:02}",
                        "AllowWebBooking": True,
                    }
                    for value in range(1, 61)
                ]
            elif self.path == "/search/filters":
                data = {"UnitTypesGroups": [], "NightlySleepingUnits": []}
            else:
                self.send_error(404)
                return
            self.respond(data)

        def do_POST(self) -> None:
            """Return bookable nights for exactly the requested facility and window."""
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            transcript.append((self.path, payload))
            if self.path != "/search/grid":
                self.send_error(404)
                return
            self.respond(
                {
                    "NightsActual": 2,
                    "Facility": {
                        "FacilityId": payload["FacilityId"],
                        "Units": {
                            "100.1": {
                                "UnitId": 100,
                                "Name": "Synthetic Site",
                                "UseType": 4,
                                "AllowWebBooking": True,
                                "Slices": {
                                    "a": {"Date": "2030-01-01", "IsFree": True},
                                    "b": {"Date": "2030-01-02", "IsFree": True},
                                },
                            }
                        },
                    },
                }
            )

        def respond(self, data: Any) -> None:
            """Write a complete JSON response over the normal HTTP transport."""
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", transcript
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def synthetic_environment(installation: Installation, endpoint: str) -> dict[str, str]:
    """Redirect installed provider endpoints and internal waits, leaving CLI dispatch real.

    The external sitecustomize directory contains no application source. Production
    parsing, metadata resolution, retry transport, DTO matching and rendering run
    unmodified; the seams change only the upstream destination and test cadence.
    """
    seam = installation.directory / "synthetic-upstream"
    seam.mkdir(exist_ok=True)
    (seam / "sitecustomize.py").write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "import camply.core.search as search\n"
        "import camply.providers.usedirect.provider as usedirect\n"
        "from camply.providers.usedirect.variations import ReserveCaliforniaProvider\n"
        f"ReserveCaliforniaProvider.api_url = {endpoint!r}\n"
        "usedirect._REQUEST_INTERVAL = 0\n"
        "search.POLL_INTERVAL_SECONDS = 0.02\n"
        "def audit(event, args):\n"
        "    if event == 'sqlite3.connect':\n"
        "        raise AssertionError('CLI attempted database access')\n"
        "    if event == 'socket.connect' and args[1][0] != '127.0.0.1':\n"
        "        raise AssertionError('CLI attempted an external request')\n"
        "sys.addaudithook(audit)\n"
        "assert 'site-packages' in str(Path(search.__file__))\n"
    )
    return {
        **clean_environment(),
        "PYTHONPATH": str(seam),
        "PUSHOVER_APP_TOKEN": "malformed:synthetic-secret",
        "PUSHOVER_USER_KEY": "malformed:synthetic-recipient",
        "CAMPLY_PROVIDER": "ReserveCalifornia",
    }


def executable(installation: Installation) -> str:
    """Locate the real console entrypoint from the installed environment."""
    return str(
        installation.python.with_name("camply.exe" if os.name == "nt" else "camply")
    )


def test_installed_discovery_and_preflight(
    install: Callable[[str], Installation],
) -> None:
    """Exact discovery and public validation work with no database or optional runtime."""
    installation = install("")
    with upstream() as (endpoint, transcript):
        environment = synthetic_environment(installation, endpoint)

        def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
            """Run the installed executable outside the checkout."""
            return subprocess.run(
                [executable(installation), *arguments],
                cwd=installation.directory,
                env=environment,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

        areas = run(["recreation-areas", "--search", "Synthetic", "--state", "ca"])
        assert areas.returncode == 0, areas.stderr
        assert "Synthetic Park" in areas.stdout
        campground = run(["campgrounds", "--campground", "60"])
        assert campground.returncode == 0, campground.stderr
        assert (
            "⛰  Synthetic Park, CA (#1) - 🏕  Synthetic Campground 60 (#60)"
            in campground.stdout
        )
        transcript.clear()
        invalid = run(
            [
                "campsites",
                "--campground",
                "60",
                "--start-date",
                "2030-01-03",
                "--end-date",
                "2030-01-01",
            ]
        )
        assert invalid.returncode != 0
        assert not transcript
        unavailable = run(
            [
                "campsites",
                "--campground",
                "999",
                "--start-date",
                "2030-01-01",
                "--end-date",
                "2030-01-03",
            ]
        )
        assert unavailable.returncode != 0
        assert not any(path == "/search/grid" for path, _ in transcript)
        for deferred in (
            ["test-notifications"],
            ["campsites", "--notifications", "pushover"],
        ):
            assert run(deferred).returncode != 0


@pytest.mark.skipif(os.name == "nt", reason="POSIX console signals")
@pytest.mark.parametrize(
    ("stop_signal", "notification_settings"),
    [(signal.SIGINT, False), (signal.SIGTERM, True)],
)
def test_installed_monitor_continues_after_match(
    install: Callable[[str], Installation],
    stop_signal: signal.Signals,
    notification_settings: bool,
) -> None:
    """Matching first results are followed by more live checks until signal cancellation."""
    installation = install("")
    with upstream() as (endpoint, transcript):
        environment = synthetic_environment(installation, endpoint)
        if not notification_settings:
            environment.pop("PUSHOVER_APP_TOKEN")
            environment.pop("PUSHOVER_USER_KEY")
        process = subprocess.Popen(
            [
                executable(installation),
                "campsites",
                "--campground",
                "60",
                "--start-date",
                "2030-01-01",
                "--end-date",
                "2030-01-03",
                "--nights",
                "2",
            ],
            cwd=installation.directory,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdout is not None and process.stderr is not None
        lines: list[str] = []
        reader = threading.Thread(
            target=lines.extend, args=(process.stdout,), daemon=True
        )
        reader.start()
        try:
            deadline = time.monotonic() + 20
            while (
                sum(
                    "Reservable Campsites Matching Search Preferences" in line
                    for line in lines
                )
                < 2
            ):
                if process.poll() is not None or time.monotonic() >= deadline:
                    process.terminate()
                    process.wait(timeout=5)
                    reader.join(timeout=5)
                    pytest.fail(
                        f"No second completed check: {''.join(lines)}\n{process.stderr.read()}"
                    )
                time.sleep(0.01)
            assert process.poll() is None
            process.send_signal(stop_signal)
            process.wait(timeout=5)
            reader.join(timeout=5)
            output, error = "".join(lines), process.stderr.read()
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            reader.join(timeout=5)
            process.stdout.close()
            process.stderr.close()
        assert output.count("Reservable Campsites Matching Search Preferences") >= 2
        assert "Aborted" in error
        assert "📅 Tue, January 01 🏕  1 sites" in output
        assert "https://www.reservecalifornia.com/park/1/60 (2 nights)" in output
        assert "malformed:synthetic" not in output + error
        grids = [payload for path, payload in transcript if path == "/search/grid"]
        assert len(grids) >= 2
        assert all(payload["FacilityId"] == 60 for payload in grids)
        assert all(payload["StartDate"] == "01-01-2030" for payload in grids)
        assert all(payload["EndDate"] == "01-02-2030" for payload in grids)
        count = len(transcript)
        time.sleep(0.05)
        assert len(transcript) == count


def test_installed_help_and_provider_listing_create_no_state(
    install: Callable[[str], Installation], tmp_path: Path
) -> None:
    """Read-only commands require neither network nor configuration state."""
    installation = install("")
    seam = installation.directory / "offline-guard"
    seam.mkdir(exist_ok=True)
    (seam / "sitecustomize.py").write_text(
        "import sys\n"
        "def audit(event, args):\n"
        "    if event in ('sqlite3.connect', 'socket.connect'):\n"
        "        raise AssertionError('Offline CLI attempted network or database IO')\n"
        "sys.addaudithook(audit)\n"
    )
    environment = {
        **clean_environment(),
        "HOME": str(tmp_path),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "PYTHONPATH": str(seam),
    }
    for arguments in (["--help"], ["--version"], ["providers"]):
        result = subprocess.run(
            [executable(installation), *arguments],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    assert not list(tmp_path.iterdir())
