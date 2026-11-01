"""Verify versioned OCI chart publication without registry credentials or uploads."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
HELM = shutil.which("helm")
pytestmark = pytest.mark.skipif(
    HELM is None, reason="Helm is required for chart publication tests"
)


@pytest.fixture
def publisher(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Run real chart packaging while replacing only the registry push with a recorder."""
    shutil.copy(ROOT / "Taskfile.yaml", tmp_path / "Taskfile.yaml")
    shutil.copytree(ROOT / "tasks", tmp_path / "tasks")
    shutil.copytree(ROOT / "deploy/helm", tmp_path / "deploy/helm")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    wrapper = binaries / "helm"
    wrapper.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = push ]; then\n'
        '  printf "%s\\n" "$@" > "$HELM_TEST_CALLS"\n'
        "  exit 0\n"
        "fi\n"
        'exec "$HELM_TEST_REAL" "$@"\n'
    )
    wrapper.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{binaries}{os.pathsep}{os.environ['PATH']}",
        "HELM_TEST_REAL": str(HELM),
        "HELM_TEST_CALLS": str(tmp_path / "push-args"),
        "CI": "true",
        "RELEASE_VERSION": "1.2.3",
    }
    return tmp_path, env


def test_publish_versioned_chart(publisher: tuple[Path, dict[str, str]]) -> None:
    """The published chart uses the requested name, release version, and matching image."""
    directory, env = publisher
    original = (directory / "deploy/helm/Chart.yaml").read_text()
    result = subprocess.run(
        ["task", "helm:publish"],
        cwd=directory,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    archive = directory / "dist/camply-web-1.2.3.tgz"
    assert archive.is_file()
    assert (directory / "push-args").read_text().splitlines() == [
        "push",
        "dist/camply-web-1.2.3.tgz",
        "oci://ghcr.io/juftin/charts",
    ]
    metadata = subprocess.run(
        [str(HELM), "show", "chart", str(archive)],
        capture_output=True,
        text=True,
        check=True,
    )
    chart = yaml.safe_load(metadata.stdout)
    assert chart["name"] == "camply-web"
    assert chart["version"] == "1.2.3"
    assert chart["appVersion"] == "v1.2.3"
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
            for container in pod["containers"] + pod.get("initContainers", []):
                assert container["image"] == "ghcr.io/juftin/camply-web:v1.2.3"
    assert (directory / "deploy/helm/Chart.yaml").read_text() == original


@pytest.mark.parametrize(
    "ci,version",
    [
        ("", "1.2.3"),
        ("false", "1.2.3"),
        ("true", ""),
        ("true", "latest"),
        ("true", "1.2.3-beta.1"),
        ("true", "1.2.3; touch unexpected"),
    ],
)
def test_publish_rejects_invalid_context(
    publisher: tuple[Path, dict[str, str]], ci: str, version: str
) -> None:
    """Only stable CI releases can reach the registry push command."""
    directory, env = publisher
    result = subprocess.run(
        ["task", "helm:publish"],
        cwd=directory,
        env={**env, "CI": ci, "RELEASE_VERSION": version},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert not (directory / "push-args").exists()
    assert not (directory / "unexpected").exists()


def test_workflow_publishes_chart_after_release_image() -> None:
    """Only stable release events publish a chart, after its versioned image is available."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/publish.yaml").read_text())
    assert workflow["permissions"]["packages"] == "write"
    steps = workflow["jobs"]["publish"]["steps"]
    chart = next(s for s in steps if s.get("run") == "task helm:publish")
    image = next(s for s in steps if s.get("run") == "task publish")
    assert chart["if"] == "steps.source.outputs.version != ''"
    assert chart["env"]["RELEASE_VERSION"] == "${{ steps.source.outputs.version }}"
    assert steps.index(image) < steps.index(chart)
    login = next(s for s in steps if "helm registry login" in s.get("run", ""))
    assert login["if"] == chart["if"]
    assert "--password-stdin" in login["run"]
    assert steps.index(login) < steps.index(chart)
