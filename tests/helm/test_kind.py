"""Exercise first-install migration ordering and failed upgrades in a disposable cluster."""

import json
import os
import shutil
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    os.environ.get("CAMPLY_HELM_SMOKE") != "1", reason="Opt in with task helm:smoke"
)


@pytest.fixture
def cluster(tmp_path: Path) -> Iterator[dict[str, str]]:
    """Create a test-owned kind cluster without touching the operator's kubeconfig."""
    for executable in ("kind", "kubectl", "helm", "docker"):
        assert shutil.which(executable), f"{executable} is required"
    name = f"camply-helm-{uuid.uuid4().hex[:8]}"
    env = {**os.environ, "KUBECONFIG": str(tmp_path / "kubeconfig")}
    image = os.environ.get("CAMPLY_HELM_TEST_IMAGE", f"camply-helm-smoke:{name}")
    env["CAMPLY_HELM_TEST_IMAGE"] = image
    built_here = "CAMPLY_HELM_TEST_IMAGE" not in os.environ
    try:
        if built_here:
            run(
                env,
                "docker",
                "build",
                "--target",
                "camply",
                "--tag",
                image,
                str(ROOT),
                timeout=600,
            )
        subprocess.run(
            [
                "kind",
                "create",
                "cluster",
                "--name",
                name,
                "--kubeconfig",
                env["KUBECONFIG"],
                "--wait",
                "120s",
            ],
            env=env,
            check=True,
            timeout=240,
        )
        run(env, "kind", "load", "docker-image", image, "--name", name)
        yield env
    finally:
        report = ROOT / "tmp" / name
        report.mkdir(parents=True, exist_ok=True)
        for args, filename in [
            (("kubectl", "get", "pods,jobs,pvc,events", "-o", "wide"), "resources.txt"),
            (
                (
                    "kubectl",
                    "logs",
                    "-l",
                    "app.kubernetes.io/instance=smoke",
                    "--all-containers=true",
                    "--prefix=true",
                    "--tail=100",
                    "--max-log-requests=20",
                ),
                "logs.txt",
            ),
        ]:
            try:
                result = subprocess.run(
                    args,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
                (report / filename).write_text(result.stdout + result.stderr)
            except subprocess.TimeoutExpired:
                (report / filename).write_text("Diagnostic collection timed out")
        subprocess.run(
            ["kind", "delete", "cluster", "--name", name],
            env=env,
            check=False,
            timeout=120,
        )
        if built_here:
            subprocess.run(
                ["docker", "image", "rm", image], env=env, check=False, timeout=30
            )


def run(
    env: dict[str, str], *args: str, timeout: int = 240, data: str | None = None
) -> str:
    """Run a command using only the test cluster's kubeconfig and synthetic credentials."""
    result = subprocess.run(
        args,
        env=env,
        input=data,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    assert result.returncode == 0, f"{args}:\n{result.stdout}\n{result.stderr}"
    return result.stdout


def test_migration_startup_and_failed_upgrade(cluster: dict[str, str]) -> None:
    """A fresh schema precedes consumers; a failed upgrade starts no new consumers."""
    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "camply-db"},
        "stringData": {"POSTGRES_PASSWORD": "synthetic-helm-test-password"},
    }
    run(cluster, "kubectl", "apply", "-f", "-", data=json.dumps(secret))
    repository, tag = cluster["CAMPLY_HELM_TEST_IMAGE"].rsplit(":", 1)
    options = [
        "smoke",
        str(ROOT / "deploy/helm"),
        "--set-string",
        f"image.repository={repository}",
        "--set-string",
        f"image.tag={tag}",
        "--set",
        "image.pullPolicy=Never",
        "--set",
        "prometheus.enabled=false",
        "--set",
        "beat.args={camply,serve,beat}",
        "--set",
        "migrations.activeDeadlineSeconds=300",
        "--set",
        "migrations.backoffLimit=0",
    ]
    run(
        cluster,
        "helm",
        "install",
        *options,
        "--wait",
        "--wait-for-jobs",
        "--timeout",
        "8m",
        timeout=540,
    )
    jobs = json.loads(run(cluster, "kubectl", "get", "jobs", "-o", "json"))["items"]
    completed = next(
        c["lastTransitionTime"]
        for c in jobs[0]["status"]["conditions"]
        if c["type"] == "Complete"
    )
    pods: list[dict[str, Any]] = json.loads(
        run(cluster, "kubectl", "get", "pods", "-o", "json")
    )["items"]
    for role in ("backend", "worker", "beat"):
        pod = next(
            p
            for p in pods
            if p["metadata"]["labels"].get("app.kubernetes.io/component") == role
        )
        assert (
            pod["status"]["containerStatuses"][0]["state"]["running"]["startedAt"]
            >= completed
        )
    run(cluster, "helm", "test", "smoke", "--logs", "--timeout", "90s")
    run(
        cluster,
        "kubectl",
        "exec",
        "deployment/smoke-camply-postgresql",
        "--",
        "psql",
        "-U",
        "camply",
        "-d",
        "camply",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        "CREATE TABLE helm_upgrade_proof (value integer); INSERT INTO helm_upgrade_proof VALUES (42);",
    )
    old_job = jobs[0]["metadata"]["name"]
    run(
        cluster,
        "helm",
        "upgrade",
        *options,
        "--set",
        "migrations.revision=successful-upgrade",
        "--wait",
        "--wait-for-jobs",
        "--timeout",
        "5m",
        timeout=360,
    )
    upgraded = json.loads(run(cluster, "kubectl", "get", "jobs", "-o", "json"))["items"]
    assert any(
        j["metadata"]["name"] != old_job and j.get("status", {}).get("succeeded") == 1
        for j in upgraded
    )
    proof = run(
        cluster,
        "kubectl",
        "exec",
        "deployment/smoke-camply-postgresql",
        "--",
        "psql",
        "-U",
        "camply",
        "-d",
        "camply",
        "-Atc",
        "SELECT value FROM helm_upgrade_proof",
    )
    assert proof.strip() == "42"
    run(cluster, "helm", "test", "smoke", "--logs", "--timeout", "90s")
    run(
        cluster,
        "helm",
        "upgrade",
        *options,
        "--set",
        "database.name=missing_database",
        "--set",
        "migrations.revision=failed-upgrade",
    )
    backend = json.loads(
        run(cluster, "kubectl", "get", "deployment/smoke-camply-backend", "-o", "json")
    )
    job = backend["spec"]["template"]["metadata"]["annotations"]["camply/migration-job"]
    run(
        cluster,
        "kubectl",
        "wait",
        f"job/{job}",
        "--for=condition=Failed",
        "--timeout=180s",
    )
    pods = json.loads(run(cluster, "kubectl", "get", "pods", "-o", "json"))["items"]
    for role in ("backend", "worker", "beat"):
        new = [
            p
            for p in pods
            if p["metadata"].get("annotations", {}).get("camply/migration-job") == job
            and p["metadata"]["labels"].get("app.kubernetes.io/component") == role
        ]
        assert new, f"No upgrade pod found for {role}"
        for pod in new:
            assert all(
                "running" not in s["state"] and "terminated" not in s["state"]
                for s in pod["status"].get("containerStatuses", [])
            )
