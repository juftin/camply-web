"""Exercise ntfy's public endpoint boundary, including GET write aliases."""

import os
import re
import shutil
import subprocess
import threading
import time
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "deploy/helm/files/ntfy-nginx.conf"
CASES = [
    ("GET", "/", True),
    ("GET", "/camply", True),
    ("GET", "/camply/json?poll=1&since=all", True),
    ("GET", "/one,two/sse", True),
    ("GET", "/camply/ws", True),
    ("GET", "/camply/auth", True),
    ("GET", "/config.js", True),
    ("GET", "/static/app.js", True),
    ("GET", "/v1/health", True),
    ("HEAD", "/file/abc.txt", True),
    ("GET", "/file/abc.txt", True),
    ("POST", "/camply", False),
    ("PUT", "/camply", False),
    ("POST", "/", False),
    ("DELETE", "/camply", False),
    ("GET", "/camply/publish?message=bad", False),
    ("GET", "/camply/send?message=bad", False),
    ("GET", "/camply/trigger?message=bad", False),
    ("GET", "/camply/clear", False),
    ("GET", "/camply/abc/delete", False),
    ("GET", "/v1/account/token", False),
    ("POST", "/v1/account", False),
    ("POST", "/file/abc.txt", False),
    ("GET", "/camply/json/../publish", False),
    ("GET", "/camply/%70ublish", False),
]


@pytest.mark.parametrize("method,path,allowed", CASES)
def test_public_allowlist(method: str, path: str, allowed: bool) -> None:
    """Validate the shipped proxy map against upstream read and write endpoints."""
    config = CONFIG.read_text()
    patterns = re.findall(r'"~([^"]+)" 1;', config)
    assert len(patterns) == 3
    key = f"{method}:{path.split('?', 1)[0]}"
    assert any(re.search(p.replace("\\\\", "\\"), key) for p in patterns) == allowed
    assert "default 0;" in config
    assert "if ($ntfy_read_allowed = 0) { return 404; }" in config
    assert "proxy_buffering off;" in config
    assert "proxy_set_header Upgrade $http_upgrade;" in config


@pytest.fixture(scope="module")
def proxy(tmp_path_factory: pytest.TempPathFactory) -> Iterator[int]:
    """Run the actual proxy against a local fake ntfy, without Docker or a cluster."""
    tmp_path = tmp_path_factory.mktemp("ntfy-proxy")
    nginx = os.environ.get("CAMPLY_TEST_NGINX") or shutil.which("nginx")
    if not nginx:
        pytest.skip("Set CAMPLY_TEST_NGINX to run live public boundary checks")

    class Upstream(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()

        do_HEAD = do_GET

        def log_message(self, format: str, *args: object) -> None:
            pass

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    # Reserve an ephemeral port while preparing the config.
    reservation = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    port = reservation.server_port
    reservation.server_close()
    config = CONFIG.read_text().replace("/tmp/", f"{tmp_path}/")
    config = config.replace("/dev/stdout", str(tmp_path / "access.log")).replace(
        "/dev/stderr", str(tmp_path / "error.log")
    )
    config = config.replace("listen 8081;", f"listen {port};").replace(
        "127.0.0.1:8080", f"127.0.0.1:{upstream.server_port}"
    )
    path = tmp_path / "nginx.conf"
    path.write_text(config)
    result = subprocess.run(
        [nginx, "-t", "-c", str(path)], check=False, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    thread.start()
    process = subprocess.Popen([nginx, "-c", str(path), "-g", "daemon off;"])
    try:
        for _ in range(100):
            try:
                connection = HTTPConnection("127.0.0.1", port, timeout=1)
                connection.request("GET", "/v1/health")
                assert connection.getresponse().status == 200
                connection.close()
                break
            except OSError:
                time.sleep(0.02)
        else:
            pytest.fail("nginx did not start")
        yield port
    finally:
        process.terminate()
        process.wait(timeout=5)
        upstream.shutdown()
        upstream.server_close()
        thread.join()


@pytest.mark.parametrize("method,path,allowed", CASES)
def test_live_public_boundary(
    proxy: int, method: str, path: str, allowed: bool
) -> None:
    """Nginx must deny writes after URI decoding/normalization and pass valid reads."""
    connection = HTTPConnection("127.0.0.1", proxy, timeout=3)
    try:
        connection.request(method, path)
        assert connection.getresponse().status == (200 if allowed else 404)
    finally:
        connection.close()
