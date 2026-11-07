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
    assert migration["command"] == ["python", "/startup/migrate.py"]
    assert migration["args"] == ["--job", job["metadata"]["name"]]
    assert {"name": "startup", "mountPath": "/startup", "readOnly": True} in (
        migration["volumeMounts"]
    )
    assert "migrate.py" in resource(items, "ConfigMap", "-startup")["data"]
    deployments = [item for item in items if item["kind"] == "Deployment"]
    assert len(deployments) == 8
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


def test_migration_checkpoints_need_no_retained_jobs_or_api_writes() -> None:
    """Database-backed checkpoints allow ordinary Job pruning and read-only RBAC."""
    job = next(item for item in render() if item["kind"] == "Job")
    assert "helm.sh/resource-policy" not in job["metadata"].get("annotations", {})
    assert job["spec"]["template"]["spec"]["automountServiceAccountToken"] is False


@pytest.mark.parametrize(
    "example", ["home-ops", "ingress", "gateway", "external-services"]
)
def test_example_values(example: str) -> None:
    """Published operator examples produce valid multi-document YAML."""
    assert render("-f", str(CHART / "examples" / f"{example}.yaml"))


@pytest.mark.parametrize("example", ["gateway", "home-ops"])
def test_gateway_backend_references_include_api_defaults(example: str) -> None:
    """Explicit API defaults prevent GitOps drift for both Service backends."""
    route = resource(
        render("-f", str(CHART / "examples" / f"{example}.yaml")), "HTTPRoute", "-app"
    )
    for rule in route["spec"]["rules"]:
        for backend in rule["backendRefs"]:
            assert backend["group"] == ""
            assert backend["kind"] == "Service"
            assert backend["weight"] == 1


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


def test_prometheus_rolls_out_when_worker_scraping_changes() -> None:
    """Enabling workers reloads scrape configuration; scaling DNS targets needs no reload."""
    disabled = render("--set", "worker.enabled=false")
    enabled = render("--set", "worker.enabled=true")
    scaled = render("--set", "worker.replicas=2")
    assert (
        resource(disabled, "ConfigMap", "-prometheus")["data"]
        != resource(enabled, "ConfigMap", "-prometheus")["data"]
    )
    pods = [
        resource(items, "Deployment", "-prometheus")["spec"]["template"]
        for items in (disabled, enabled, scaled)
    ]
    assert (
        pods[0]["metadata"]["annotations"]["checksum/config"]
        != pods[1]["metadata"]["annotations"]["checksum/config"]
    )
    assert pods[1] == pods[2]


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
    assert hook["metadata"]["annotations"]["helm.sh/hook-delete-policy"] == (
        "before-hook-creation"
    )
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
    """The required CI pipeline verifies the locally built image and Helm lifecycle DAG."""
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yaml").read_text())
    tasks = [
        item.get("task")
        for job in ci["jobs"].values()
        for item in job.get("strategy", {}).get("matrix", {}).get("include", [])
    ]
    assert "build" in tasks
    assert "helm:smoke" in tasks
    assert "smoke" in ci["jobs"]
    assert "build" in ci["jobs"]["smoke"].get("needs", [])


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


def test_ntfy_persistence_and_private_publishing() -> None:
    """One persistent writer exposes separate full-API and public read services."""
    items = render()
    deployment = resource(items, "Deployment", "-ntfy")
    assert deployment["spec"]["replicas"] == 1
    assert deployment["spec"]["strategy"] == {"type": "Recreate"}
    pod = deployment["spec"]["template"]["spec"]
    assert pod["automountServiceAccountToken"] is False
    assert pod["securityContext"]["runAsNonRoot"] is True
    ntfy, proxy = pod["containers"]
    assert ntfy["image"] == "docker.io/binwiederhier/ntfy:v2.37.1"
    assert ntfy["args"] == ["serve"]
    env = {e["name"]: e["value"] for e in ntfy["env"]}
    assert env["NTFY_CACHE_FILE"] == "/var/lib/ntfy/cache.db"
    assert env["NTFY_AUTH_DEFAULT_ACCESS"] == "read-write"
    assert ntfy["readinessProbe"]["httpGet"]["path"] == "/v1/health"
    assert proxy["securityContext"]["readOnlyRootFilesystem"] is True
    assert pod["volumes"][0]["persistentVolumeClaim"]["claimName"] == "test-camply-ntfy"
    claim = resource(items, "PersistentVolumeClaim", "-ntfy")
    assert claim["metadata"]["annotations"]["helm.sh/resource-policy"] == "keep"
    internal = resource(items, "Service", "-ntfy")
    public = resource(items, "Service", "-ntfy-public")
    assert internal["spec"]["type"] == public["spec"]["type"] == "ClusterIP"
    assert internal["spec"]["ports"][0]["targetPort"] == "http"
    assert public["spec"]["ports"][0]["targetPort"] == "subscriptions"


@pytest.mark.parametrize("network", ["ingress", "route"])
def test_ntfy_derives_public_hostname(network: str) -> None:
    """Both public routing APIs target only the read-only proxy, never publishing."""
    field = "hosts" if network == "ingress" else "hostnames"
    args = [
        "--set",
        f"{network}.enabled=true",
        "--set",
        f"{network}.{field}={{example.com,other.example.com}}",
    ]
    if network == "route":
        args += ["--set", "route.parentRefs[0].name=external"]
    items = render(*args)
    kind = "Ingress" if network == "ingress" else "HTTPRoute"
    route = resource(items, kind, "-ntfy")["spec"]
    if network == "ingress":
        assert [r["host"] for r in route["rules"]] == [
            "ntfy.example.com",
            "ntfy.other.example.com",
        ]
        backend = route["rules"][0]["http"]["paths"][0]["backend"]["service"]
    else:
        assert route["hostnames"] == ["ntfy.example.com", "ntfy.other.example.com"]
        assert route["parentRefs"] == [{"name": "external"}]
        backend = route["rules"][0]["backendRefs"][0]
    assert backend["name"] == "test-camply-ntfy-public"
    pod = resource(items, "Deployment", "-ntfy")["spec"]["template"]["spec"]
    env = {e["name"]: e["value"] for e in pod["containers"][0]["env"]}
    assert env["NTFY_BASE_URL"] == "https://ntfy.example.com"


def test_ntfy_overrides_storage_and_disable() -> None:
    """Custom URL and claims work; disabling removes every ntfy resource."""
    items = render(
        "--set",
        "ntfy.baseUrl=http://notify.local",
        "--set",
        "ntfy.persistence.existingClaim=restored",
    )
    pod = resource(items, "Deployment", "-ntfy")["spec"]["template"]["spec"]
    assert pod["volumes"][0]["persistentVolumeClaim"]["claimName"] == "restored"
    assert not any(
        i["kind"] == "PersistentVolumeClaim" and i["metadata"]["name"].endswith("-ntfy")
        for i in items
    )
    assert {e["name"]: e["value"] for e in pod["containers"][0]["env"]}[
        "NTFY_BASE_URL"
    ] == "http://notify.local"
    items = render("--set", "ntfy.persistence.enabled=false")
    assert (
        resource(items, "Deployment", "-ntfy")["spec"]["template"]["spec"]["volumes"][
            0
        ]["emptyDir"]
        == {}
    )
    items = render(
        "--set", "ntfy.enabled=false", "-f", str(CHART / "examples/gateway.yaml")
    )
    assert not any("-ntfy" in i["metadata"]["name"] for i in items)


def test_ntfy_custom_hostname_and_separate_tls() -> None:
    """Public hostname overrides and certificates remain separate from Camply auth."""
    items = render(
        "--set",
        "ingress.enabled=true",
        "--set",
        "ntfy.hostnames={notify.example.net}",
        "--set",
        "ntfy.ingress.tls[0].secretName=notify-tls",
        "--set",
        "ntfy.ingress.tls[0].hosts={notify.example.net}",
        "--set",
        "ingress.annotations.auth=camply-only",
    )
    route = resource(items, "Ingress", "-ntfy")
    assert route["spec"]["rules"][0]["host"] == "notify.example.net"
    assert route["spec"]["tls"] == [
        {"secretName": "notify-tls", "hosts": ["notify.example.net"]}
    ]
    assert "auth" not in route["metadata"]["annotations"]
