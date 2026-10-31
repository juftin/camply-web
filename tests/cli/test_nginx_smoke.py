"""Opt-in packaged Nginx proxy regression against synthetic HTTP and TLS servers."""

import http.server
import json
import os
import ssl
import subprocess
import threading
import time
from contextlib import ExitStack
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("CAMPLY_NGINX_SMOKE") != "1",
    reason="Run task backend:nginx:test with Docker and OpenSSL",
)


class Upstream(http.server.BaseHTTPRequestHandler):
    """Echo proxy routing information without contacting a real booking service."""

    def do_GET(self) -> None:
        """Return the path and forwarded Host header after a successful handshake."""
        self.send_response(200)
        self.end_headers()
        self.wfile.write(
            json.dumps({"path": self.path, "host": self.headers["Host"]}).encode()
        )

    def log_message(self, format: str, *args: object) -> None:
        """Suppress per-request noise from synthetic upstream traffic."""


def _command(args: list[str]) -> str:
    """Run a bounded local operation and expose useful failure diagnostics."""
    result = subprocess.run(
        args, capture_output=True, text=True, check=False, timeout=60
    )
    assert result.returncode == 0, f"{args}: {result.stdout}\n{result.stderr}"
    return result.stdout.strip()


@pytest.mark.parametrize("use_tls", [False, True], ids=["http", "https-requires-sni"])
def test_packaged_nginx_proxies_upstream(tmp_path: Path, use_tls: bool) -> None:
    """Serve local health and retain API routing for HTTP and SNI-required HTTPS."""
    names: list[str | None] = []

    def require_sni(
        connection: ssl.SSLSocket, name: str | None, context: ssl.SSLContext
    ) -> int | None:
        """Reject TLS negotiation unless Nginx sends the configured upstream hostname."""
        names.append(name)
        return (
            None
            if name == "host.docker.internal"
            else ssl.ALERT_DESCRIPTION_UNRECOGNIZED_NAME
        )

    with ExitStack() as stack:
        upstream = http.server.ThreadingHTTPServer(("0.0.0.0", 0), Upstream)
        stack.callback(upstream.server_close)
        if use_tls:
            _command(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-days",
                    "1",
                    "-subj",
                    "/CN=host.docker.internal",
                    "-keyout",
                    str(tmp_path / "synthetic.key"),
                    "-out",
                    str(tmp_path / "synthetic.crt"),
                ]
            )
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(
                tmp_path / "synthetic.crt", tmp_path / "synthetic.key"
            )
            context.set_servername_callback(require_sni)
            upstream.socket = context.wrap_socket(upstream.socket, server_side=True)
        thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        stack.callback(thread.join, timeout=5)
        stack.callback(upstream.shutdown)
        templates = Path(__file__).resolve().parents[2] / "src/camply/cli/nginx"
        (tmp_path / "nginx.conf").write_text(
            (templates / "nginx.conf")
            .read_text()
            .replace("${CAMPLY_NGINX_SERVER_CONFIG}", '"/review/server.conf"')
        )
        scheme = "https" if use_tls else "http"
        (tmp_path / "server.conf").write_text(
            (templates / "server.conf")
            .read_text()
            .replace("${CAMPLY_FRONTEND_DIR}", '"/review"')
            .replace(
                "${CAMPLY_BACKEND_URL}",
                json.dumps(f"{scheme}://host.docker.internal:{upstream.server_port}"),
            )
        )
        container = _command(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--user",
                "0",
                "--publish",
                "127.0.0.1::8080",
                "--add-host",
                "host.docker.internal:host-gateway",
                "--volume",
                f"{tmp_path}:/review:ro",
                "--entrypoint",
                "nginx",
                os.environ.get("CAMPLY_NGINX_SMOKE_IMAGE", "nginx:stable-alpine"),
                "-p",
                "/tmp/",
                "-c",
                "/review/nginx.conf",
                "-g",
                "daemon off;",
            ]
        )
        stack.callback(
            subprocess.run,
            ["docker", "rm", "--force", container],
            capture_output=True,
            check=False,
            timeout=30,
        )
        port = _command(["docker", "port", container, "8080"]).rsplit(":", 1)[1]
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=5
        ) as client:
            for _attempt in range(50):
                try:
                    if client.get("/healthz").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            else:
                raise AssertionError(_command(["docker", "logs", container]))
            response = client.get(
                "/api/health", headers={"Host": "frontend.example.invalid"}
            )
        assert response.status_code == 200, response.text
        assert response.json() == {
            "path": "/api/health",
            "host": "frontend.example.invalid",
        }
        assert names == (["host.docker.internal"] if use_tls else [])
