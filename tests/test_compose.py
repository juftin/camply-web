"""Validate Docker Compose deployment flavors and configuration invariants."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROOT_COMPOSE = ROOT / "docker-compose.yaml"
DISTRIBUTED_COMPOSE = ROOT / "deploy/compose/docker-compose.yaml"
STANDALONE_COMPOSE = ROOT / "deploy/compose/docker-compose.standalone.yaml"
PRODUCTION_COMPOSE = ROOT / "deploy/compose/docker-compose.production.yaml"
PRODUCTION_ENV_EXAMPLE = ROOT / "deploy/compose/production.env.example"
PROMETHEUS_CONFIG = ROOT / "deploy/monitoring/prometheus/prometheus.yml"

DEPLOY_COMPOSE_FILES = [DISTRIBUTED_COMPOSE, STANDALONE_COMPOSE, PRODUCTION_COMPOSE]
ALL_COMPOSE_FILES = [ROOT_COMPOSE, *DEPLOY_COMPOSE_FILES]


def _load_yaml(path: Path) -> dict[str, Any]:
    """Parse a YAML file and ensure its root object is a mapping."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} must parse as a YAML mapping"
    return data


def _env_map(service: dict[str, Any]) -> dict[str, str]:
    """Return a service's environment mapping with stringified values."""
    env = service.get("environment", {})
    assert isinstance(env, dict), "Expected environment mapping"
    return {str(key): str(value) for key, value in env.items()}


def _volume_specs(service: dict[str, Any]) -> list[str]:
    """Return string volume mounts declared on a service."""
    volumes = service.get("volumes", [])
    assert isinstance(volumes, list)
    return [str(entry) for entry in volumes]


@pytest.mark.parametrize(
    "path",
    ALL_COMPOSE_FILES,
    ids=lambda p: str(p.relative_to(ROOT)),
)
def test_compose_files_parse_and_follow_compose_spec(path: Path) -> None:
    """Every Compose flavor parses cleanly and declares services and volumes."""
    data = _load_yaml(path)
    assert isinstance(data.get("name"), str) and data["name"]
    services = data.get("services")
    assert isinstance(services, dict) and services
    volumes = data.get("volumes")
    assert isinstance(volumes, dict) and volumes
    for service_name, service in services.items():
        assert isinstance(service, dict), f"{service_name} must be a mapping"
        assert "image" in service, f"{service_name} must specify an image"
        assert "healthcheck" in service, f"{service_name} must specify a healthcheck"
        assert service.get("restart") == "unless-stopped", (
            f"{service_name} in {path.name} should set restart: unless-stopped"
        )


@pytest.mark.parametrize(
    "path",
    DEPLOY_COMPOSE_FILES,
    ids=lambda p: p.name,
)
def test_deploy_compose_files_pull_ghcr_without_building(path: Path) -> None:
    """Every Compose file under deploy/compose/ pulls published GHCR images with no build section."""
    data = _load_yaml(path)
    services = data["services"]
    defined_volumes = set(data["volumes"])
    for name, service in services.items():
        assert "build" not in service, f"{path.name}:{name} must pull, not build"
        for spec in _volume_specs(service):
            source = spec.split(":", 1)[0]
            assert not source.startswith(".") and not source.startswith("/"), (
                f"{path.name}:{name} must use named volumes only, got {spec}"
            )
            assert source in defined_volumes, f"undeclared volume {source} on {name}"
        if name in ("camply", "backend", "celery-worker", "celery-beat", "frontend"):
            assert service["image"] == "ghcr.io/juftin/camply-web:${CAMPLY_VERSION:-v2}"


def test_root_compose_preserves_dev_distributed_contract() -> None:
    """Root docker-compose.yaml stays the local-build distributed stack with Sentry on backend."""
    data = _load_yaml(ROOT_COMPOSE)
    services = data["services"]
    assert set(services) == {
        "valkey",
        "backend",
        "db",
        "celery-worker",
        "celery-beat",
        "prometheus",
        "frontend",
    }

    for name in ("backend", "celery-worker", "celery-beat", "frontend"):
        service = services[name]
        assert service["image"] == "ghcr.io/juftin/camply-web:${CAMPLY_VERSION:-local}"
        assert service["build"]["context"] == "."
        assert service["build"]["dockerfile"] == "Dockerfile"
        assert service["build"]["target"] == "camply"
        build_args = service["build"]["args"]
        assert build_args["VITE_MAP_STYLE_URL"] == "${VITE_MAP_STYLE_URL:-}"
        assert build_args["VITE_MAP_TILE_URL"] == "${VITE_MAP_TILE_URL:-}"
        assert (
            build_args["VITE_MAP_ATTRIBUTION_TEXT"] == "${VITE_MAP_ATTRIBUTION_TEXT:-}"
        )
        assert build_args["VITE_MAP_ATTRIBUTION_URL"] == "${VITE_MAP_ATTRIBUTION_URL:-}"
        assert (
            build_args["VITE_MAP_MAX_NATIVE_ZOOM"] == "${VITE_MAP_MAX_NATIVE_ZOOM:-19}"
        )

    for name in ("backend", "celery-worker", "celery-beat"):
        env = _env_map(services[name])
        assert env["CAMPLY_SENTRY_DSN"] == "${CAMPLY_SENTRY_DSN:-}"
        assert (
            env["CAMPLY_SENTRY_TRACES_SAMPLE_RATE"]
            == "${CAMPLY_SENTRY_TRACES_SAMPLE_RATE:-0.0}"
        )

    backend_env = _env_map(services["backend"])
    assert backend_env["CAMPLY_ENVIRONMENT"] == "${CAMPLY_ENVIRONMENT:-local}"
    assert backend_env["CAMPLY_AUTH_MODE"] == "${CAMPLY_AUTH_MODE:-none}"
    assert backend_env["CAMPLY_SESSION_COOKIE_SECURE"] == (
        "${CAMPLY_SESSION_COOKIE_SECURE:-false}"
    )


def test_deploy_default_compose_is_ghcr_distributed_quick_start() -> None:
    """deploy/compose/docker-compose.yaml runs the 7-service distributed stack from GHCR."""
    data = _load_yaml(DISTRIBUTED_COMPOSE)
    services = data["services"]
    assert set(services) == {
        "db",
        "valkey",
        "backend",
        "celery-worker",
        "celery-beat",
        "prometheus",
        "frontend",
    }

    backend_env = _env_map(services["backend"])
    assert backend_env["CAMPLY_ENVIRONMENT"] == "${CAMPLY_ENVIRONMENT:-local}"
    assert backend_env["CAMPLY_AUTH_MODE"] == "${CAMPLY_AUTH_MODE:-none}"
    assert backend_env["CAMPLY_SESSION_COOKIE_SECURE"] == (
        "${CAMPLY_SESSION_COOKIE_SECURE:-false}"
    )
    assert services["frontend"]["ports"] == ["${FRONTEND_PORT:-80}:8080"]

    for name in ("backend", "celery-worker", "celery-beat"):
        env = _env_map(services[name])
        assert env["CAMPLY_SENTRY_DSN"] == "${CAMPLY_SENTRY_DSN:-}"
        assert (
            env["CAMPLY_SENTRY_TRACES_SAMPLE_RATE"]
            == "${CAMPLY_SENTRY_TRACES_SAMPLE_RATE:-0.0}"
        )


def test_standalone_compose_is_single_container_sqlite() -> None:
    """Standalone Compose runs only one camply service with named-volume SQLite persistence."""
    data = _load_yaml(STANDALONE_COMPOSE)
    services = data["services"]
    assert list(services) == ["camply"]

    camply = services["camply"]
    assert "build" not in camply
    assert camply["image"] == "ghcr.io/juftin/camply-web:${CAMPLY_VERSION:-v2}"
    assert camply["command"] == [
        "camply",
        "serve",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    assert camply["stop_signal"] == "SIGTERM"
    assert camply["stop_grace_period"] == "1m"
    assert camply["restart"] == "unless-stopped"
    assert camply["healthcheck"]["test"] == ["CMD", "camply", "serve", "healthcheck"]
    assert camply["ports"] == ["${CAMPLY_BIND:-127.0.0.1}:${CAMPLY_PORT:-8000}:8000"]

    volumes = _volume_specs(camply)
    assert volumes == ["camply_data:/home/camply/.local/share/camply"]
    assert "camply_data" in data["volumes"]

    env = _env_map(camply)
    assert env["CAMPLY_ENVIRONMENT"] == "${CAMPLY_ENVIRONMENT:-production}"
    assert env["CAMPLY_DEBUG"] == "${CAMPLY_DEBUG:-false}"
    assert env["CAMPLY_AUTH_MODE"] == "${CAMPLY_AUTH_MODE:-none}"
    assert env["CAMPLY_APP_URL"] == "${CAMPLY_APP_URL:-http://localhost:8000}"
    assert env["CAMPLY_SENTRY_DSN"] == "${CAMPLY_SENTRY_DSN:-}"
    assert (
        env["CAMPLY_SENTRY_TRACES_SAMPLE_RATE"]
        == "${CAMPLY_SENTRY_TRACES_SAMPLE_RATE:-0.0}"
    )
    assert "CAMPLY_VALKEY_URL" not in env
    assert "CAMPLY_DB_HOST" not in env

    logging = camply.get("logging", {})
    assert logging.get("driver") == "json-file"
    assert logging.get("options", {}).get("max-size")
    assert logging.get("options", {}).get("max-file")


def test_production_compose_is_hardened_and_self_contained() -> None:
    """Production Compose enforces secrets, network isolation, named volumes, and inline config."""
    data = _load_yaml(PRODUCTION_COMPOSE)
    services = data["services"]
    expected_services = {
        "db",
        "valkey",
        "backend",
        "celery-worker",
        "celery-beat",
        "prometheus",
        "frontend",
    }
    assert set(services) == expected_services

    # No build blocks; every service has restart policy and JSON log rotation.
    for name, service in services.items():
        assert "build" not in service, f"production {name} must pull published image"
        assert service["restart"] == "unless-stopped"
        logging = service.get("logging", {})
        assert logging.get("driver") == "json-file", f"{name} missing json-file logging"
        assert logging.get("options", {}).get("max-size")
        assert logging.get("options", {}).get("max-file")

    # Application services use published v2 image and graceful stop settings.
    for name in ("backend", "celery-worker", "celery-beat", "frontend"):
        service = services[name]
        assert service["image"] == "ghcr.io/juftin/camply-web:${CAMPLY_VERSION:-v2}"
        assert service["stop_grace_period"] == "1m"
    assert services["frontend"]["stop_signal"] == "SIGQUIT"
    for name in ("backend", "celery-worker", "celery-beat"):
        assert services[name]["stop_signal"] == "SIGTERM"

    # Network isolation: only frontend publishes a host port.
    for internal_service in (
        "db",
        "valkey",
        "prometheus",
        "backend",
        "celery-worker",
        "celery-beat",
    ):
        assert "ports" not in services[internal_service], (
            f"production {internal_service} must not publish host ports"
        )
    assert services["frontend"]["ports"] == [
        "${FRONTEND_BIND:-127.0.0.1}:${FRONTEND_PORT:-8080}:8080"
    ]

    # Named volumes only (no host bind mounts).
    defined_volumes = set(data["volumes"])
    assert {
        "db_data",
        "valkey_data",
        "prometheus_data",
        "camply_cache",
    } <= defined_volumes
    for name, service in services.items():
        for spec in _volume_specs(service):
            source = spec.split(":", 1)[0]
            assert not source.startswith(".") and not source.startswith("/"), (
                f"production {name} must use named volumes only, got {spec}"
            )
            assert source in defined_volumes, f"undeclared volume {source} on {name}"

    # Hardened environment and required secrets (no weak defaults).
    db_env = _env_map(services["db"])
    assert ":?" in db_env["POSTGRES_PASSWORD"]

    backend_env = _env_map(services["backend"])
    assert backend_env["CAMPLY_ENVIRONMENT"] == "${CAMPLY_ENVIRONMENT:-production}"
    assert backend_env["CAMPLY_DEBUG"] == "${CAMPLY_DEBUG:-false}"
    assert backend_env["CAMPLY_AUTH_MODE"] == "${CAMPLY_AUTH_MODE:-session}"
    assert (
        backend_env["CAMPLY_SESSION_COOKIE_SECURE"]
        == "${CAMPLY_SESSION_COOKIE_SECURE:-true}"
    )
    assert ":?" in backend_env["CAMPLY_DB_PASSWORD"]
    for secret_key in (
        "CAMPLY_LOGIN_USERNAME",
        "CAMPLY_LOGIN_PASSWORD",
        "CAMPLY_SESSION_SECRET",
    ):
        value = backend_env[secret_key]
        assert value == f"${{{secret_key}:-}}", (
            f"production {secret_key} must not supply a hardcoded default"
        )

    worker_env = _env_map(services["celery-worker"])
    assert worker_env["CAMPLY_ENVIRONMENT"] == "${CAMPLY_ENVIRONMENT:-production}"
    assert ":?" in worker_env["CAMPLY_DB_PASSWORD"]
    assert ":?" in worker_env["CAMPLY_APP_URL"]
    assert worker_env["CAMPLY_INVITE_ONLY"] == "${CAMPLY_INVITE_ONLY:-false}"

    beat_env = _env_map(services["celery-beat"])
    assert beat_env["CAMPLY_ENVIRONMENT"] == "${CAMPLY_ENVIRONMENT:-production}"
    assert ":?" in beat_env["CAMPLY_DB_PASSWORD"]

    for name in ("backend", "celery-worker", "celery-beat"):
        env = _env_map(services[name])
        assert env["CAMPLY_SENTRY_DSN"] == "${CAMPLY_SENTRY_DSN:-}"
        assert (
            env["CAMPLY_SENTRY_TRACES_SAMPLE_RATE"]
            == "${CAMPLY_SENTRY_TRACES_SAMPLE_RATE:-0.0}"
        )


@pytest.mark.parametrize(
    "path",
    [DISTRIBUTED_COMPOSE, PRODUCTION_COMPOSE],
    ids=lambda p: p.name,
)
def test_inline_prometheus_config_matches_source_file(path: Path) -> None:
    """Embedded Prometheus config in deploy/compose/ distributed stacks matches prometheus.yml."""
    data = _load_yaml(path)
    configs = data.get("configs", {})
    assert "prometheus_config" in configs
    inline_content = configs["prometheus_config"]["content"]
    source_content = PROMETHEUS_CONFIG.read_text(encoding="utf-8")
    assert inline_content.strip() == source_content.strip()

    # Inline config itself must also be valid YAML with expected scrape jobs.
    parsed_prom = yaml.safe_load(inline_content)
    jobs = {job["job_name"] for job in parsed_prom["scrape_configs"]}
    assert jobs == {"camply-backend", "camply-worker", "prometheus"}

    # Prometheus service mounts the inline config and omits removed v2 flags.
    prom = data["services"]["prometheus"]
    assert prom["configs"] == [
        {
            "source": "prometheus_config",
            "target": "/etc/prometheus/prometheus.yml",
            "mode": 0o444,
        }
    ]
    command_args = " ".join(prom["command"])
    assert "--web.console.libraries" not in command_args
    assert "--web.console.templates" not in command_args


def test_production_env_example_covers_required_variables() -> None:
    """production.env.example defines every required variable referenced by docker-compose.production.yaml."""
    compose_text = PRODUCTION_COMPOSE.read_text(encoding="utf-8")
    required_vars = set(re.findall(r"\$\{([A-Z0-9_]+):\?", compose_text))
    assert required_vars == {"POSTGRES_PASSWORD", "CAMPLY_APP_URL"}

    env_text = PRODUCTION_ENV_EXAMPLE.read_text(encoding="utf-8")
    defined_keys = set(re.findall(r"^([A-Z0-9_]+)=", env_text, flags=re.MULTILINE))
    assert required_vars <= defined_keys
    assert {
        "CAMPLY_VERSION",
        "CAMPLY_CORS_ORIGINS",
        "FRONTEND_BIND",
        "FRONTEND_PORT",
        "CAMPLY_AUTH_MODE",
        "CAMPLY_LOGIN_USERNAME",
        "CAMPLY_LOGIN_PASSWORD",
        "CAMPLY_SESSION_SECRET",
        "CAMPLY_SESSION_COOKIE_SECURE",
    } <= defined_keys


def test_compose_defaults_parse_against_runtime_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default env values in docker-compose.standalone.yaml and docker-compose.production.yaml validate with Pydantic configs."""
    from camply.db.notification_config import NtfyConfig
    from camply.server.config import BackendConfig
    from camply.worker.config import WorkerConfig

    def _resolve_default(expr: str) -> str:
        match = re.fullmatch(r"\$\{[A-Z0-9_]+:-(.*)\}", expr)
        return match.group(1) if match else expr

    # Standalone defaults must instantiate cleanly out of the box.
    standalone_env = _env_map(_load_yaml(STANDALONE_COMPOSE)["services"]["camply"])
    for key, raw in standalone_env.items():
        monkeypatch.setenv(key, _resolve_default(raw))
    assert BackendConfig().auth_mode.value == "none"
    assert str(WorkerConfig().app_url).rstrip("/") == "http://localhost:8000"
    assert NtfyConfig().subscription_url == "https://ntfy.sh"
    assert NtfyConfig().publish_url is None

    # Production defaults with explicit required secrets + session credentials validate cleanly.
    prod_services = _load_yaml(PRODUCTION_COMPOSE)["services"]
    prod_backend_env = _env_map(prod_services["backend"])
    prod_worker_env = _env_map(prod_services["celery-worker"])
    for key, raw in {**prod_backend_env, **prod_worker_env}.items():
        if ":?" in raw:
            continue
        monkeypatch.setenv(key, _resolve_default(raw))
    monkeypatch.setenv("CAMPLY_APP_URL", "https://camply.example.com")
    monkeypatch.setenv("CAMPLY_LOGIN_USERNAME", "admin")
    monkeypatch.setenv("CAMPLY_LOGIN_PASSWORD", "synthetic-strong-password")
    monkeypatch.setenv("CAMPLY_SESSION_SECRET", "a" * 64)

    backend_cfg = BackendConfig()
    assert backend_cfg.environment == "production"
    assert backend_cfg.debug is False
    assert backend_cfg.auth_mode.value == "session"
    assert backend_cfg.session_cookie_secure is True

    worker_cfg = WorkerConfig()
    assert worker_cfg.environment == "production"
    assert str(worker_cfg.app_url).rstrip("/") == "https://camply.example.com"
