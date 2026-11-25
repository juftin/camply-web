# Docker Compose Deployment Flavors

Every Compose file in `deploy/compose/` is self-contained and pulls the published `ghcr.io/juftin/camply-web` image with no repository checkout or local Docker build required. For building from a local checkout during development, use the root `docker-compose.yaml`.

| Flavor                    | File                                            | Containers                                                          | Database   | Auth default | Image source     | Best for                                                      |
| ------------------------- | ----------------------------------------------- | ------------------------------------------------------------------- | ---------- | ------------ | ---------------- | ------------------------------------------------------------- |
| **Distributed (Default)** | `deploy/compose/docker-compose.yaml`            | 7 (`frontend`, `backend`, `worker`, `beat`, `db`, `valkey`, `prom`) | PostgreSQL | `none`       | Published (`v2`) | Quick-start distributed self-hosting without building locally |
| **Standalone**            | `deploy/compose/docker-compose.standalone.yaml` | 1 (`camply`)                                                        | SQLite     | `none`       | Published (`v2`) | Personal or small-group Docker hosts with minimal setup       |
| **Production**            | `deploy/compose/docker-compose.production.yaml` | 7 (`frontend`, `backend`, `worker`, `beat`, `db`, `valkey`, `prom`) | PostgreSQL | `session`    | Published (`v2`) | Hardened self-hosted production behind HTTPS                  |
| **Local Development**     | `docker-compose.yaml` (root)                    | 7 (`frontend`, `backend`, `worker`, `beat`, `db`, `valkey`, `prom`) | PostgreSQL | `none`       | Local build      | Building and developing from a cloned repository              |

## Distributed quick start (default)

Run the full distributed stack using published GHCR images and quick-start defaults (no build or repo clone required):

```bash
docker compose -f deploy/compose/docker-compose.yaml up -d
```

Open `http://localhost` (port `80` by default, controlled by `FRONTEND_PORT`). Before exposing this stack on the public internet, switch to `docker-compose.production.yaml` (or enable authentication, strong secrets, and TLS).

## Standalone single-container

Start camply with built-in SQLite persisted in the `camply_data` named volume:

```bash
docker compose -f deploy/compose/docker-compose.standalone.yaml up -d
```

Open `http://localhost:8000` (bound to `127.0.0.1` by default) and run **Admin Operations → Sync Providers** to import the campground catalog.

Before exposing the container beyond localhost, create a `.env` file with `CAMPLY_AUTH_MODE=session` (or `auth0`), explicit credentials, `CAMPLY_APP_URL`, and `CAMPLY_CORS_ORIGINS`, and terminate TLS with a reverse proxy.

## Production distributed

1. Copy the production environment template and replace placeholder secrets:

   ```bash
   cp deploy/compose/production.env.example .env
   openssl rand -hex 32   # use for CAMPLY_SESSION_SECRET
   ```

2. Start the stack:

   ```bash
   docker compose -f deploy/compose/docker-compose.production.yaml up -d
   ```

Only `frontend` publishes a host port (`127.0.0.1:8080` by default); PostgreSQL, Valkey, Prometheus, and the FastAPI backend remain internal to the Compose network. Point your HTTPS reverse proxy (Caddy, Nginx, Traefik, or Cloudflare Tunnel) at `http://127.0.0.1:8080`.

## Local development (builds from source)

From a cloned repository, use the root `docker-compose.yaml` (which builds from the local checkout and exposes backing service ports for local tools):

```bash
cp docs/examples/.env.example .env
docker compose up -d --build
```

Or run `task compose:up` from the repository root.

For full documentation covering authentication, reverse-proxy TLS termination, backups, and upgrades, see the [Docker & Kubernetes self-hosting guide](../../docs/self-hosting/containers.md).
