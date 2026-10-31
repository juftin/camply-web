"""Check chart contracts against actual Helm-rendered Kubernetes resources."""

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CHART = ROOT / "deploy/helm"
HELM = shutil.which("helm")
pytestmark = pytest.mark.skipif(HELM is None, reason="Helm is required for chart tests")


def render(*args: str) -> list[dict[str, Any]]:
    """Render the chart without contacting a cluster or reading operator secrets."""
    result = subprocess.run(
        [str(HELM), "template", "test", str(CHART), "--namespace", "camply", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return [item for item in yaml.safe_load_all(result.stdout) if item]


def resource(items: list[dict[str, Any]], kind: str, suffix: str) -> dict[str, Any]:
    """Find a release resource by kind and component suffix."""
    return next(
        item
        for item in items
        if item["kind"] == kind and item["metadata"]["name"].endswith(suffix)
    )


def test_default_stack_and_migration_barrier() -> None:
    """All database consumers wait on the exact migration Job, with limited RBAC."""
    items = render()
    job = next(item for item in items if item["kind"] == "Job")
    assert "helm.sh/hook" not in job["metadata"].get("annotations", {})
    assert "ttlSecondsAfterFinished" not in job["spec"]
    migration = job["spec"]["template"]["spec"]["containers"][0]
    assert migration["command"] == ["python", "-m", "camply.db.migration"]
    deployments = [item for item in items if item["kind"] == "Deployment"]
    assert len(deployments) == 7
    for role in ("backend", "worker", "beat"):
        pod = resource(items, "Deployment", f"-{role}")["spec"]["template"]["spec"]
        gate = pod["initContainers"][0]
        assert job["metadata"]["name"] in gate["args"]
        assert pod["automountServiceAccountToken"] is False
        assert any(m["name"] == "migration-api" for m in gate["volumeMounts"])
        assert all(
            m["name"] != "migration-api" for m in pod["containers"][0]["volumeMounts"]
        )
        env = {e["name"]: e.get("value") for e in pod["containers"][0]["env"]}
        assert env["SKIP_MIGRATIONS"] == "1"
    rule = resource(items, "Role", "-migration-wait")["rules"][0]
    assert rule["verbs"] == ["get"]
    assert rule["resourceNames"] == [job["metadata"]["name"]]
    beat = resource(items, "Deployment", "-beat")
    assert beat["spec"]["replicas"] == 1
    assert beat["spec"]["strategy"] == {"type": "Recreate"}
    assert (
        "--sync-providers" in beat["spec"]["template"]["spec"]["containers"][0]["args"]
    )


def test_migration_identity_and_rollout() -> None:
    """New images and explicit GitOps revisions replace immutable migration Jobs."""

    def job_name(items: list[dict[str, Any]]) -> str:
        """Return the current migration barrier name."""
        return next(i["metadata"]["name"] for i in items if i["kind"] == "Job")

    original = job_name(render())
    assert job_name(render()) == original
    assert job_name(render("--set", "image.tag=1.2.3")) != original
    assert job_name(render("--set", "migrations.revision=2")) != original
    # template --is-upgrade changes flags, but its synthetic Release.Revision stays 1.
    assert job_name(render("--is-upgrade")) == original


@pytest.mark.parametrize(
    "example", ["home-ops", "ingress", "gateway", "external-services"]
)
def test_example_values(example: str) -> None:
    """Published operator examples produce valid multi-document YAML."""
    assert render("-f", str(CHART / "examples" / f"{example}.yaml"))


def test_ingress_and_gateway_backends() -> None:
    """Routes resolve release-specific services, supporting TLS and parent references."""
    items = render("-f", str(CHART / "examples/gateway.yaml"))
    route = resource(items, "HTTPRoute", "-app")
    gateway = resource(items, "Gateway", "-gateway")
    assert route["spec"]["parentRefs"] == [{"name": gateway["metadata"]["name"]}]
    service_names = {i["metadata"]["name"] for i in items if i["kind"] == "Service"}
    assert all(
        r["backendRefs"][0]["name"] in service_names for r in route["spec"]["rules"]
    )
    ingress = resource(
        render("-f", str(CHART / "examples/ingress.yaml")), "Ingress", "-app"
    )
    assert ingress["spec"]["ingressClassName"] == "nginx"
    assert ingress["spec"]["tls"][0]["secretName"] == "camply-tls"


@pytest.mark.parametrize(
    "storage_class,expected", [("fast", "fast"), ("-", ""), (None, None)]
)
def test_pvc_storage_classes(storage_class: str | None, expected: str | None) -> None:
    """Default, explicit, and disabled storage classes retain distinct meanings."""
    args = (
        []
        if storage_class is None
        else ["--set-string", f"postgresql.persistence.storageClass={storage_class}"]
    )
    claim = resource(render(*args), "PersistentVolumeClaim", "-postgresql")
    assert claim["spec"].get("storageClassName") == expected
    assert claim["metadata"]["annotations"]["helm.sh/resource-policy"] == "keep"


def test_reuse_claim_and_ephemeral_storage() -> None:
    """Existing claims are mounted without recreating them; ephemeral is explicit."""
    items = render(
        "--set",
        "postgresql.persistence.existingClaim=restored-db",
        "--set",
        "valkey.persistence.enabled=false",
    )
    assert not any(
        i["kind"] == "PersistentVolumeClaim"
        and i["metadata"]["name"].endswith("-postgresql")
        for i in items
    )
    db = resource(items, "Deployment", "-postgresql")["spec"]["template"]["spec"]
    assert db["volumes"][0]["persistentVolumeClaim"]["claimName"] == "restored-db"
    broker = resource(items, "Deployment", "-valkey")["spec"]["template"]["spec"]
    assert broker["volumes"][0]["emptyDir"] == {}


def test_external_services_and_secret_injection() -> None:
    """External endpoints and secret references reach migrations and every consumer."""
    items = render("-f", str(CHART / "examples/external-services.yaml"))
    assert not any(i["kind"] == "PersistentVolumeClaim" for i in items)
    assert len([i for i in items if i["kind"] == "Deployment"]) == 4
    for kind, suffix in [
        ("Deployment", "-backend"),
        ("Deployment", "-worker"),
        ("Deployment", "-beat"),
    ]:
        container = resource(items, kind, suffix)["spec"]["template"]["spec"][
            "containers"
        ][0]
        env = {e["name"]: e for e in container["env"]}
        assert env["CAMPLY_DB_HOST"]["value"] == "postgres.example.internal"
        assert (
            env["CAMPLY_VALKEY_URL"]["valueFrom"]["secretKeyRef"]["name"]
            == "camply-broker"
        )
        assert container["envFrom"] == [{"secretRef": {"name": "camply-runtime"}}]


def test_metrics_scrape_each_replica() -> None:
    """Prometheus discovers pod endpoints instead of sampling a load-balanced Service."""
    config = resource(render(), "ConfigMap", "-prometheus")
    prometheus = yaml.safe_load(config["data"]["prometheus.yml"])
    jobs = {job["job_name"]: job for job in prometheus["scrape_configs"]}
    assert jobs["camply-backend"]["dns_sd_configs"][0]["type"] == "A"
    assert jobs["camply-worker"]["dns_sd_configs"][0]["port"] == 8001


def test_long_release_names_remain_valid() -> None:
    """Generated Service and RBAC names stay within Kubernetes DNS label limits."""
    items = render("--set", "fullnameOverride=" + "camply" * 12)
    assert all(len(item["metadata"]["name"]) <= 63 for item in items)


@pytest.mark.parametrize(
    "args",
    [
        ["--set", "postgresql.enabled=false"],
        ["--set", "route.enabled=true"],
        ["--set", "gateway.enabled=true"],
        ["--set", "frontend.enabled=false", "--set", "ingress.enabled=true"],
    ],
)
def test_incomplete_configuration_rejected(args: list[str]) -> None:
    """Invalid external-service and routing choices fail before installation."""
    result = subprocess.run(
        [str(HELM), "template", "test", str(CHART), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Error" in result.stderr


def test_reserved_environment_cannot_bypass_migrations() -> None:
    """User environment cannot enable competing launcher migrations or reroute its DB."""
    items = render(
        "--set",
        "backend.env.SKIP_MIGRATIONS=0",
        "--set",
        "backend.env.CAMPLY_DB_HOST=wrong-db",
    )
    container = resource(items, "Deployment", "-backend")["spec"]["template"]["spec"][
        "containers"
    ][0]
    env = {e["name"]: e.get("value") for e in container["env"]}
    assert env["SKIP_MIGRATIONS"] == "1"
    assert env["CAMPLY_DB_HOST"] == "test-camply-postgresql"
