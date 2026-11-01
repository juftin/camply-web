"""Verify OCI chart aliases and image defaults without credentials or uploads."""

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
HELM = shutil.which("helm")
ORAS = shutil.which("oras")
pytestmark = pytest.mark.skipif(
    HELM is None, reason="Helm is required for chart publication tests"
)


@pytest.fixture
def publisher(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Use real packaging and Python, recording only external registry writes."""
    shutil.copy(ROOT / "Taskfile.yaml", tmp_path / "Taskfile.yaml")
    shutil.copytree(ROOT / "tasks", tmp_path / "tasks")
    shutil.copytree(ROOT / "deploy/helm", tmp_path / "deploy/helm")
    script = ROOT / "deploy/publish_chart.py"
    if script.exists():
        shutil.copy(script, tmp_path / "deploy/publish_chart.py")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    wrapper = binaries / "helm"
    wrapper.write_text(
        '#!/bin/sh\nif [ "$1" = push ]; then exit 0; fi\nexec "$HELM_TEST_REAL" "$@"\n'
    )
    wrapper.chmod(0o755)
    # Reuse pytest's Python/dependencies rather than installing into each fixture.
    runner = binaries / "uv"
    runner.write_text('#!/bin/sh\nshift 4\nexec "$HELM_TEST_PYTHON" "$@"\n')
    runner.chmod(0o755)
    recorder = binaries / "oras"
    recorder.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "import subprocess\n"
        "from pathlib import Path\n"
        "with Path(os.environ['HELM_TEST_CALLS']).open('a') as stream:\n"
        "    stream.write(json.dumps({'cwd': os.getcwd(), 'args': sys.argv[1:]}) + '\\n')\n"
        "status = int(os.environ.get('HELM_TEST_PUSH_STATUS', '0'))\n"
        "if not status and os.environ.get('HELM_TEST_LAYOUT'):\n"
        "    args = sys.argv[1:]\n"
        "    ref = next(a for a in args if a.startswith('ghcr.io/'))\n"
        "    args[args.index(ref)] = os.environ['HELM_TEST_LAYOUT'] + ':' + ref.rsplit(':', 1)[1]\n"
        "    status = subprocess.run([os.environ['HELM_TEST_ORAS'], *args, '--oci-layout']).returncode\n"
        "sys.exit(status)\n"
    )
    recorder.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{binaries}{os.pathsep}{os.environ['PATH']}",
        "HELM_TEST_REAL": str(HELM),
        "HELM_TEST_PYTHON": sys.executable,
        "HELM_TEST_CALLS": str(tmp_path / "push-args"),
        "CI": "true",
        "RELEASE_VERSION": "1.2.3",
        "GITHUB_SHA": "0123456789abcdef0123456789abcdef01234567",
    }
    return tmp_path, env


def publish(directory: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Exercise the public Task entrypoint."""
    return subprocess.run(
        ["task", "helm:publish"],
        cwd=directory,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "release,version,expected",
    [
        ("1.2.3", "1.2.3", ["1.2.3,v1.2.3", "0123456", "v1", "latest"]),
        ("2.0.0", "2.0.0", ["2.0.0,v2.0.0", "0123456", "v2", "latest"]),
        ("", "0.0.0-sha-0123456", ["0123456", "latest"]),
    ],
)
def test_publish_matching_chart_images(
    publisher: tuple[Path, dict[str, str]],
    release: str,
    version: str,
    expected: list[str],
) -> None:
    """Each alias packages its matching image, including latest after main builds."""
    directory, env = publisher
    originals = {
        name: (directory / "deploy/helm" / name).read_text()
        for name in ("Chart.yaml", "values.yaml")
    }
    result = publish(directory, {**env, "RELEASE_VERSION": release})
    assert result.returncode == 0, result.stderr
    calls = [
        json.loads(line) for line in (directory / "push-args").read_text().splitlines()
    ]
    tags = []
    for call in calls:
        args = call["args"]
        assert args[0] == "push"
        reference = next(a for a in args if a.startswith("ghcr.io/"))
        tag = reference.removeprefix("ghcr.io/juftin/charts/camply-web:")
        tags.append(tag)
        image_tag = tag.split(",")[-1]
        config_arg = args[args.index("--config") + 1]
        config_file, config_type = config_arg.split(":")
        assert config_type == "application/vnd.cncf.helm.config.v1+json"
        chart = json.loads((Path(call["cwd"]) / config_file).read_text())
        assert chart["name"] == "camply-web"
        assert chart["version"] == version
        assert chart["appVersion"] == image_tag
        assert (
            "org.opencontainers.image.source=https://github.com/juftin/camply-web"
            in args
        )
        archive_arg = args[-1]
        archive_file, archive_type = archive_arg.split(":")
        assert archive_type == "application/vnd.cncf.helm.chart.content.v1.tar+gzip"
        archive = Path(call["cwd"]) / archive_file
        metadata = subprocess.run(
            [str(HELM), "show", "chart", str(archive)],
            capture_output=True,
            text=True,
            check=True,
        )
        assert yaml.safe_load(metadata.stdout) == chart
        manifest = subprocess.run(
            [str(HELM), "template", "test", str(archive)],
            capture_output=True,
            text=True,
            check=True,
        )
        items = [i for i in yaml.safe_load_all(manifest.stdout) if i]
        for item in items:
            if item["kind"] == "Job" or (
                item["kind"] == "Deployment"
                and item["metadata"]["name"].endswith(
                    ("-frontend", "-backend", "-worker", "-beat")
                )
            ):
                pod = item["spec"]["template"]["spec"]
            elif item["kind"] == "Pod":
                pod = item["spec"]
            else:
                continue
            for container in pod["containers"] + pod.get("initContainers", []):
                assert container["image"] == f"ghcr.io/juftin/camply-web:{image_tag}"
    assert tags == expected
    for name, original in originals.items():
        assert (directory / "deploy/helm" / name).read_text() == original


@pytest.mark.parametrize(
    "overrides",
    [
        {"CI": ""},
        {"CI": "false"},
        {"RELEASE_VERSION": "latest"},
        {"RELEASE_VERSION": "1.2.3-beta.1"},
        {"RELEASE_VERSION": "01.2.3"},
        {"RELEASE_VERSION": "1.2.3; touch unexpected"},
        {"GITHUB_SHA": ""},
        {"GITHUB_SHA": "123456"},
        {"GITHUB_SHA": "not-a-sha"},
        {"GITHUB_SHA": "0123456; touch unexpected"},
    ],
)
def test_publish_rejects_invalid_context(
    publisher: tuple[Path, dict[str, str]], overrides: dict[str, str]
) -> None:
    """Invalid CI/version/revision values fail before packaging or registry writes."""
    directory, env = publisher
    result = publish(directory, {**env, **overrides})
    assert result.returncode != 0
    assert not (directory / "push-args").exists()
    assert not (directory / "dist").exists()
    assert not (directory / "unexpected").exists()


def test_publish_stops_on_push_failure(publisher: tuple[Path, dict[str, str]]) -> None:
    """A failed upload fails the Task and cannot advance the remaining aliases."""
    directory, env = publisher
    result = publish(directory, {**env, "HELM_TEST_PUSH_STATUS": "1"})
    assert result.returncode != 0
    assert len((directory / "push-args").read_text().splitlines()) == 1


def test_workflow_publishes_chart_after_matching_images() -> None:
    """Both publication contexts push charts only after their image upload succeeds."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/publish.yaml").read_text())
    assert workflow["permissions"]["packages"] == "write"
    steps = workflow["jobs"]["publish"]["steps"]
    chart = next(s for s in steps if s.get("run") == "task helm:publish")
    assert "if" not in chart
    assert chart["env"]["RELEASE_VERSION"] == "${{ steps.source.outputs.version }}"
    assert chart["env"]["GITHUB_SHA"] == "${{ steps.revision.outputs.sha }}"
    for command in ("task publish", "task publish:latest"):
        assert steps.index(
            next(s for s in steps if s.get("run") == command)
        ) < steps.index(chart)
    tools = next(s for s in steps if "ORAS_VERSION" in s.get("env", {}))
    assert "if" not in tools
    assert steps.index(tools) < steps.index(chart)
    login = next(
        s for s in steps if s.get("uses", "").startswith("docker/login-action@")
    )
    assert steps.index(login) < steps.index(chart)


@pytest.mark.skipif(ORAS is None, reason="ORAS is required for OCI round trips")
@pytest.mark.parametrize("release", ["1.2.3", ""])
def test_oci_aliases_install_by_digest(
    publisher: tuple[Path, dict[str, str]], release: str
) -> None:
    """Real ORAS manifests install through Helm, including non-semantic aliases."""
    directory, env = publisher
    layout = directory / "oci"
    result = publish(
        directory,
        {
            **env,
            "RELEASE_VERSION": release,
            "GITHUB_SHA": "abcdef0123456789",
            "HELM_TEST_LAYOUT": str(layout),
            "HELM_TEST_ORAS": str(ORAS),
        },
    )
    assert result.returncode == 0, result.stderr

    class Registry(BaseHTTPRequestHandler):
        """Serve the actual OCI layout blobs as a read-only local registry."""

        def do_GET(self) -> None:
            """Return a manifest or layer by digest without any external registry."""
            digest = self.path.rsplit("/", 1)[-1]
            blob = layout / "blobs" / digest.replace(":", "/")
            if not blob.is_file():
                self.send_error(404)
                return
            data = blob.read_bytes()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.send_header(
                "Content-Type",
                "application/vnd.oci.image.manifest.v1+json"
                if "/manifests/" in self.path
                else "application/octet-stream",
            )
            self.end_headers()
            self.wfile.write(data)

    registry = ThreadingHTTPServer(("127.0.0.1", 0), Registry)
    thread = threading.Thread(target=registry.serve_forever, daemon=True)
    thread.start()
    try:
        index = json.loads((layout / "index.json").read_text())
        expected = (
            {"v1.2.3": "v1.2.3", "1.2.3": "v1.2.3", "v1": "v1"} if release else {}
        )
        expected.update({"abcdef0": "abcdef0", "latest": "latest"})
        aliases = {
            m["annotations"]["org.opencontainers.image.ref.name"]: m["digest"]
            for m in index["manifests"]
        }
        assert aliases.keys() == expected.keys()
        for tag, image_tag in expected.items():
            manifest = subprocess.run(
                [
                    str(HELM),
                    "template",
                    "test",
                    f"oci://127.0.0.1:{registry.server_port}/camply-web@{aliases[tag]}",
                    "--plain-http",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            assert manifest.returncode == 0, manifest.stderr
            assert f"image: ghcr.io/juftin/camply-web:{image_tag}\n" in manifest.stdout
    finally:
        registry.shutdown()
        registry.server_close()
        thread.join()
