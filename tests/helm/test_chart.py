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


@pytest.mark.parametrize(
    "setting",
    [
        "backned.replicas=2",
        "backend.replicas=-1",
        "backend.service=null",
        "database.port=70000",
        "backend.probes.readiness.timeoutSeconds=0",
        "ingress.enabld=true",
        "postgresql.persistence.accessModes={WrongMode}",
    ],
)
def test_schema_rejects_operator_mistakes(setting: str) -> None:
    """Schema errors identify invalid values before Kubernetes sees a manifest."""
    result = subprocess.run(
        [str(HELM), "template", "test", str(CHART), "--set", setting],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "schema" in result.stderr.lower()


def test_probes_separate_readiness_and_allow_overrides() -> None:
    """Dependency failures affect readiness, and native handler overrides replace defaults."""
    items = render()
    app = resource(items, "Deployment", "-backend")["spec"]["template"]["spec"][
        "containers"
    ][0]
    assert app["livenessProbe"]["httpGet"]["path"] == "/api/ping"
    assert app["readinessProbe"]["httpGet"]["path"] == "/api/health"
    items = render(
        "--set",
        "backend.probes.startup=false",
        "--set",
        "backend.probes.readiness.timeoutSeconds=4",
        "--set",
        "backend.probes.liveness.exec.command={custom-check}",
    )
    app = resource(items, "Deployment", "-backend")["spec"]["template"]["spec"][
        "containers"
    ][0]
    assert "startupProbe" not in app
    assert app["readinessProbe"]["timeoutSeconds"] == 4
    assert app["livenessProbe"]["exec"]["command"] == ["custom-check"]
    assert "httpGet" not in app["livenessProbe"]


def test_service_monitor_selects_metrics_services() -> None:
    """Existing Prometheus installations discover both API and worker endpoints."""
    items = render(
        "--set",
        "serviceMonitor.enabled=true",
        "--set",
        "serviceMonitor.labels.release=monitoring",
        "--set",
        "prometheus.enabled=false",
    )
    monitor = resource(items, "ServiceMonitor", "-metrics")
    assert monitor["metadata"]["labels"]["release"] == "monitoring"
    assert monitor["spec"]["namespaceSelector"] == {"matchNames": ["camply"]}
    assert monitor["spec"]["endpoints"][0]["port"] == "metrics"
    selector = monitor["spec"]["selector"]["matchLabels"]
    selected = [
        i
        for i in items
        if i["kind"] == "Service"
        and all(i["metadata"]["labels"].get(k) == v for k, v in selector.items())
    ]
    assert {i["metadata"]["name"] for i in selected} == {
        "test-camply-backend-metrics",
        "test-camply-worker-metrics",
    }
    assert not any(
        i["kind"] == "Deployment" and i["metadata"]["name"].endswith("-prometheus")
        for i in items
    )


def test_install_notes_and_helm_connection_test() -> None:
    """Helm users receive troubleshooting instructions and can test the installed release."""
    notes = (CHART / "templates/NOTES.txt").read_text()
    assert "helm test" in notes
    assert "logs" in notes
    assert "CAMPLY_AUTH_MODE" in notes
    hook = resource(render(), "Pod", "-connection-test")
    assert hook["metadata"]["annotations"]["helm.sh/hook"] == "test"
    assert hook["spec"]["automountServiceAccountToken"] is False
    assert "/api/health" in " ".join(hook["spec"]["containers"][0]["args"])
    assert not any(i["kind"] == "Pod" for i in render("--set", "tests.enabled=false"))


def test_schema_allows_native_extensions_and_rejects_conflicting_handlers(
    tmp_path: Path,
) -> None:
    """Validation permits user metadata/env/native objects but rejects impossible probes."""
    values = tmp_path / "values.yaml"
    values.write_text(
        yaml.safe_dump(
            {
                "env": {
                    "CUSTOM_BOOLEAN": True,
                    "CUSTOM_NUMBER": 2,
                    "CUSTOM_SECRET": {
                        "valueFrom": {
                            "secretKeyRef": {"name": "synthetic", "key": "value"}
                        }
                    },
                },
                "podAnnotations": {"custom.example/annotation": "value"},
                "extraObjects": [
                    {
                        "apiVersion": "v1",
                        "kind": "ConfigMap",
                        "metadata": {"name": "synthetic"},
                        "data": {"custom": "value"},
                    }
                ],
            }
        )
    )
    assert render("-f", str(values))
    result = subprocess.run(
        [
            str(HELM),
            "template",
            "test",
            str(CHART),
            "--set",
            "backend.probes.liveness.exec.command={check}",
            "--set",
            "backend.probes.liveness.httpGet.path=/ping",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0


def test_ci_lifecycle_uses_the_source_image() -> None:
    """The required Docker check verifies the locally built PR image in Kubernetes."""
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yaml").read_text())
    steps = ci["jobs"]["backend-docker"]["steps"]
    build = next(
        s for s in steps if s.get("uses", "").startswith("docker/bake-action@")
    )
    smoke = next(s for s in steps if s.get("run") == "task helm:smoke")
    setup = next(s for s in steps if s.get("uses") == "./.github/actions/setup-backend")
    tools = next(s for s in steps if "KIND_VERSION" in s.get("env", {}))
    assert build["with"]["load"] is True
    assert build["with"]["push"] is False
    assert smoke["env"]["CAMPLY_HELM_TEST_IMAGE"].endswith(
        build["env"]["CAMPLY_VERSION"]
    )
    assert steps.index(build) < steps.index(smoke)
    assert steps.index(setup) < steps.index(tools) < steps.index(smoke)


def test_notes_render_release_specific_commands(tmp_path: Path) -> None:
    """Render the same notes offline on Helm 3/4 without install-time discovery."""
    preview = tmp_path / "chart"
    shutil.copytree(CHART, preview)
    (preview / "notes-preview.txt").write_text(
        (CHART / "templates/NOTES.txt").read_text()
    )
    (preview / "templates/notes-preview.yaml").write_text(
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: notes-preview\ndata:\n"
        '  notes: {{ tpl (.Files.Get "notes-preview.txt") . | quote }}\n'
    )
    result = subprocess.run(
        [
            str(HELM),
            "template",
            "operator-notes",
            str(preview),
            "--namespace",
            "camply",
            "--set",
            "fullnameOverride=operator-notes",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    items = [item for item in yaml.safe_load_all(result.stdout) if item]
    notes = resource(items, "ConfigMap", "notes-preview")["data"]["notes"]
    assert "helm test operator-notes -n camply --logs" in notes
    assert "svc/operator-notes-frontend 8080:8080" in notes
    assert "logs job/operator-notes-migrate-" in notes
