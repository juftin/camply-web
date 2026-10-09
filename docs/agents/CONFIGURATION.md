# CONFIGURATION: Environment Variables & Settings

This document defines all environment variables used by the `camply` monorepo. Agents and contributors should use this as a reference when setting up local or production environments.

## ⚙️ Core Configuration

All backend environment variables are prefixed with `CAMPLY_` to avoid conflicts.
They are defined in `backend/packages/backend/backend/config.py` via `pydantic-settings`.

| Variable                           | Description                                             | Default              |
| ---------------------------------- | ------------------------------------------------------- | -------------------- |
| `CAMPLY_ENVIRONMENT`               | Deployment stage (`local`, `development`, `production`) | `local`              |
| `CAMPLY_DEBUG`                     | Enable debug logs and FastAPI docs                      | `true`               |
| `CAMPLY_SENTRY_DSN`                | Sentry DSN for error tracking                           | `None` (disabled)    |
| `CAMPLY_SENTRY_TRACES_SAMPLE_RATE` | Sentry traces sample rate                               | `0.0`                |
| `CAMPLY_AUTH_MODE`                 | Authentication mode (`local` or `auth0`)                | `local`              |
| `CAMPLY_ADMIN_EMAIL`               | Admin email for local mode (auto-whitelisted)           | `admin@camply.local` |
| `CAMPLY_AUTH0_DOMAIN`              | Auth0 tenant domain (e.g., `dev-xyz.us.auth0.com`)      | `None`               |
| `CAMPLY_AUTH0_AUDIENCE`            | Auth0 API Audience/Identifier                           | `None`               |
| `CAMPLY_AUTH0_CLIENT_ID`           | Auth0 frontend Client ID                                | `None`               |

Database config uses `CAMPLY_DB_` prefix (defined in `backend/packages/db/db/config.py`):

| Variable               | Description        | Default                           |
| ---------------------- | ------------------ | --------------------------------- |
| `CAMPLY_DB_DRIVERNAME` | Database driver    | `sqlite+aiosqlite`                |
| `CAMPLY_DB_USERNAME`   | Database username  | `camply`                          |
| `CAMPLY_DB_HOST`       | Database host/path | `~/.local/share/camply/camply.db` |
| `CAMPLY_DB_DATABASE`   | Database name      | `camply`                          |

Valkey/Celery & Operations config:

| Variable            | Description                                                | Default                    |
| ------------------- | ---------------------------------------------------------- | -------------------------- |
| `CAMPLY_VALKEY_URL` | Valkey connection string for Celery & operations telemetry | `redis://localhost:6379/0` |
| `VALKEY_URL`        | Worker Valkey connection string fallback                   | `redis://localhost:6379/0` |

Prometheus & Monitoring config:

| Variable                          | Description                                               | Default                 |
| --------------------------------- | --------------------------------------------------------- | ----------------------- |
| `CAMPLY_PROMETHEUS_URL`           | Internal Prometheus URL for Admin UI trends queries       | `http://localhost:9090` |
| `PROMETHEUS_MULTIPROC_DIR`        | Directory for multi-process Prometheus metrics collection | `None`                  |
| `CAMPLY_PROMETHEUS_MULTIPROC_DIR` | Alias for `PROMETHEUS_MULTIPROC_DIR`                      | `None`                  |

---

## 🔒 Authentication (Toggleable)

`camply` supports two authentication modes, controlled by `CAMPLY_AUTH_MODE`.
See `backend/packages/backend/backend/auth.py` for implementation details.

### 1. Local-Only Mode (Private Self-Hosting — default)

Uses `CAMPLY_ADMIN_EMAIL` to auto-create an admin user on first access.
No external identity provider needed.

### 2. Auth0 Mode (Community/SaaS)

Set `CAMPLY_AUTH_MODE=auth0` to enable Auth0 JWT validation.
Requires `CAMPLY_AUTH0_DOMAIN` and `CAMPLY_AUTH0_AUDIENCE`.

---

## 🔔 Notifications

### Pushover (MVP)

| Variable             | Description                                    |
| -------------------- | ---------------------------------------------- |
| `PUSHOVER_APP_TOKEN` | The API Token for your Pushover "Application". |

### Apprise (Legacy/Future)

| Variable       | Description                                      |
| -------------- | ------------------------------------------------ |
| `APPRISE_URLS` | Comma-separated list of Apprise-compatible URLs. |

---

## 📈 Monitoring & Observability

### Native Admin UI Monitoring (Prometheus-backed)

The Admin UI provides native monitoring dashboards for usage trends, API latency/errors, worker throughput/outcomes, and provider performance, querying an internal Prometheus instance via FastAPI proxy (`GET /api/admin/trends`). Grafana is decommissioned and no longer deployed.

| Variable                | Description                | Default                 |
| ----------------------- | -------------------------- | ----------------------- |
| `CAMPLY_PROMETHEUS_URL` | Prometheus server base URL | `http://localhost:9090` |

### Sentry

| Variable                    | Description                                   |
| --------------------------- | --------------------------------------------- |
| `SENTRY_DSN`                | The DSN for error tracking (Optional).        |
| `SENTRY_TRACES_SAMPLE_RATE` | Percentage of traces to capture (0.0 to 1.0). |

---

## 🏗️ Docker & Infrastructure

These variables are primarily used in `docker-compose.yaml`.
| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | DB Username | `camply` |
| `POSTGRES_PASSWORD` | DB Password | `camply` |
| `POSTGRES_DB` | DB Name | `camply` |
| `BACKEND_VERSION` | Docker image tag for backend | `local` |
| `FRONTEND_VERSION` | Docker image tag for frontend | `local` |
