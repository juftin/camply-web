# Docker and Kubernetes

Run camply in containers as a single SQLite container, a hardened production distributed stack, a local development stack, or a Kubernetes cluster.

## Choose a Docker Compose flavor

Three self-contained Compose files live under `deploy/compose/` and pull published `ghcr.io/juftin/camply-web` images from GHCR without building or cloning the repository. The root `docker-compose.yaml` builds from a local checkout for development.

| Flavor                    | File                                            | Containers                                                          | Database   | Auth default | Image source     | Best for                                                      |
| ------------------------- | ----------------------------------------------- | ------------------------------------------------------------------- | ---------- | ------------ | ---------------- | ------------------------------------------------------------- |
| **Distributed (Default)** | `deploy/compose/docker-compose.yaml`            | 7 (`frontend`, `backend`, `worker`, `beat`, `db`, `valkey`, `prom`) | PostgreSQL | `none`       | Published (`v2`) | Quick-start distributed self-hosting without building locally |
| **Standalone**            | `deploy/compose/docker-compose.standalone.yaml` | 1 (`camply`)                                                        | SQLite     | `none`       | Published (`v2`) | Personal or small-group Docker hosts with minimal setup       |
| **Production**            | `deploy/compose/docker-compose.production.yaml` | 7 (`frontend`, `backend`, `worker`, `beat`, `db`, `valkey`, `prom`) | PostgreSQL | `session`    | Published (`v2`) | Hardened self-hosted production behind HTTPS                  |
| **Local Development**     | `docker-compose.yaml` (root)                    | 7 (`frontend`, `backend`, `worker`, `beat`, `db`, `valkey`, `prom`) | PostgreSQL | `none`       | Local build      | Building and developing from a cloned repository              |

See the [Compose deployment reference](https://github.com/juftin/camply-web/blob/main/deploy/compose/README.md) in the repository for a quick summary of all files.

## Distributed quick start (`deploy/compose/docker-compose.yaml`)

Use `deploy/compose/docker-compose.yaml` to run the full distributed stack (PostgreSQL, Valkey, Celery workers, Celery beat, Nginx, and Prometheus) from published GHCR images with quick-start defaults and no local build:

```bash
docker compose -f deploy/compose/docker-compose.yaml up -d
```

Open <http://localhost> (port `80` by default, controlled by `FRONTEND_PORT`). Data is stored in named Docker volumes (`db_data`, `valkey_data`, `prometheus_data`, `camply_cache`), and Prometheus configuration is embedded inline. Before exposing the instance beyond a trusted local network, switch to `deploy/compose/docker-compose.production.yaml` (or enable [authentication](configuration.md#authentication), strong credentials, and HTTPS).

## Production distributed (`deploy/compose/docker-compose.production.yaml`)

Use `deploy/compose/docker-compose.production.yaml` for a full production deployment with PostgreSQL, Valkey, Celery workers, Celery beat, Nginx, and Prometheus-backed Admin UI trend charts.

1. Download or copy `deploy/compose/docker-compose.production.yaml` and `deploy/compose/production.env.example` (renamed to `.env`) into a deployment directory:

   ```bash
   cp deploy/compose/production.env.example .env
   ```

2. Generate a signing secret and edit `.env`:

   ```bash
   openssl rand -hex 32
   ```

   Set strong values for `POSTGRES_PASSWORD`, `CAMPLY_LOGIN_USERNAME`, `CAMPLY_LOGIN_PASSWORD`, and `CAMPLY_SESSION_SECRET` (or configure `CAMPLY_AUTH_MODE=auth0`), and set `CAMPLY_APP_URL` and `CAMPLY_CORS_ORIGINS` to your public HTTPS origin (for example `https://camply.example.com`).

3. Start the stack:

   ```bash
   docker compose -f deploy/compose/docker-compose.production.yaml up -d
   ```

Key production safeguards built into `deploy/compose/docker-compose.production.yaml`:

- **No weak credential defaults:** Compose refuses to start unless `POSTGRES_PASSWORD` and `CAMPLY_APP_URL` are explicitly set, and the backend rejects startup in `session` mode without explicit credentials and a 32+ character signing secret.
- **Network isolation:** PostgreSQL, Valkey, Prometheus, and the FastAPI backend publish no host ports. Only `frontend` binds `${FRONTEND_BIND:-127.0.0.1}:${FRONTEND_PORT:-8080}:8080` for reverse-proxy TLS termination.
- **Named volumes and self-contained config:** Data is stored in named Docker volumes (`db_data`, `valkey_data`, `prometheus_data`, `camply_cache`) with no host bind-mount permission issues, and Prometheus configuration is embedded inline.
- **Operational defaults:** Every service uses `restart: unless-stopped`, JSON log rotation (`max-size: 10m`, `max-file: 3`), role-specific health checks, graceful stop signals, and optional `CAMPLY_SENTRY_DSN` reporting across backend, worker, and beat.

The scheduler runs `camply serve beat --sync-providers` after the API completes database migrations and passes health checks, automatically importing the campground catalog on first boot.

## Standalone single-container (`deploy/compose/docker-compose.standalone.yaml`)

Use `deploy/compose/docker-compose.standalone.yaml` when you want Docker lifecycle management without PostgreSQL, Valkey, Nginx, or Prometheus:

```bash
docker compose -f deploy/compose/docker-compose.standalone.yaml up -d
```

Open <http://localhost:8000> (bound to `127.0.0.1` by default via `CAMPLY_BIND`) and run **Sync Providers** in **Admin Operations**. SQLite data and provider caches persist in the `camply_data` named volume mounted at `/home/camply/.local/share/camply`.

Before exposing the container beyond localhost, create a `.env` file with [authentication](configuration.md#authentication), `CAMPLY_APP_URL`, and `CAMPLY_CORS_ORIGINS`, and place it behind an HTTPS reverse proxy. See [Standalone hosting](standalone.md) for details and `uv`-based installation.

## Local development (`docker-compose.yaml`)

The root `docker-compose.yaml` builds the shared image from a local repository checkout, uses local-only defaults (`CAMPLY_AUTH_MODE=none`, `CAMPLY_SESSION_COOKIE_SECURE=false`), and exposes backing service ports (`5432`, `6379`, `8000`, `9090`, and `FRONTEND_PORT`, defaulting to `80`) for local development and debugging:

```bash
git clone https://github.com/juftin/camply-web.git
cd camply-web
cp docs/examples/.env.example .env
docker compose up -d --build
```

Open <http://localhost>. Do not expose the root development Compose file directly to the internet without overriding credentials, auth mode, and port bindings; use `deploy/compose/docker-compose.production.yaml` instead.

## Reverse proxy and TLS termination

Both `deploy/compose/docker-compose.production.yaml` (`127.0.0.1:8080`) and `deploy/compose/docker-compose.standalone.yaml` (`127.0.0.1:8000`) bind to loopback by default so an HTTPS reverse proxy (Caddy, Nginx, Traefik, or Cloudflare Tunnel) can terminate TLS on the host:

```caddyfile
camply.example.com {
    reverse_proxy 127.0.0.1:8080
}
```

When serving behind HTTPS:

- Keep `CAMPLY_SESSION_COOKIE_SECURE=true`.
- Set `CAMPLY_APP_URL=https://camply.example.com` so summary notification links open your domain.
- Set `CAMPLY_CORS_ORIGINS='["https://camply.example.com"]'` so password login and CORS trust your public origin.
- If your reverse proxy runs in another container or host, override `FRONTEND_BIND` (or `CAMPLY_BIND` for standalone) or attach the container to your proxy's external Docker network.

## Lifecycle, backups, and upgrades

Common commands (pass `-f deploy/compose/docker-compose.production.yaml` or `-f deploy/compose/docker-compose.standalone.yaml` as appropriate):

```bash
docker compose -f deploy/compose/docker-compose.production.yaml ps
docker compose -f deploy/compose/docker-compose.production.yaml logs -f
docker compose -f deploy/compose/docker-compose.production.yaml pull
docker compose -f deploy/compose/docker-compose.production.yaml up -d
docker compose -f deploy/compose/docker-compose.production.yaml down
```

`docker compose down` keeps named Docker volumes intact. Pin a specific release tag with `CAMPLY_VERSION=v2.0.0` (or track the `v2` major alias) and see [Maintenance](maintenance.md) for database backup, restore, and migration procedures.

## Kubernetes with Helm

The [camply Helm chart](https://github.com/juftin/camply-web/blob/main/deploy/helm/README.md) deploys the distributed stack with migration startup gates, health probes, persistent storage, optional bundled PostgreSQL/Valkey, and Ingress or Gateway API routing.

Follow the chart README for installation and values configuration, and use [Configuration](configuration.md) for auth, notification, and `CAMPLY_APP_URL` settings.
