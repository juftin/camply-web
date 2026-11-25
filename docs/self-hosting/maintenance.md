# Maintenance

Follow these procedures to back up data, upgrade versions, inspect database state, and check instance health.

## Backups and restores

### Standalone (SQLite)

Never copy a live SQLite database file while camply is writing to its WAL journal. Either stop camply before copying the file, or use SQLite's online backup command:

```bash
sqlite3 ~/.local/share/camply/camply.db ".backup /path/to/camply-backup.db"
```

To restore, stop camply, replace the database file at `CAMPLY_DB_HOST` (or the default path), remove any stale `-wal` and `-shm` files from the old database, and start camply again.

When running the standalone Docker Compose stack (`deploy/compose/docker-compose.standalone.yaml`), stop the container before copying `/home/camply/.local/share/camply/camply.db` out of the `camply_data` volume:

```bash
docker compose -f deploy/compose/docker-compose.standalone.yaml stop camply
docker run --rm -v camply-standalone_camply_data:/data:ro -v "$PWD:/backup" alpine \
  cp /data/camply.db /backup/camply-backup.db
docker compose -f deploy/compose/docker-compose.standalone.yaml start camply
```

### Docker Compose (PostgreSQL)

Dump the database from the running `db` container (pass `-f deploy/compose/docker-compose.production.yaml` or `-f deploy/compose/docker-compose.yaml` for the GHCR stacks, or omit `-f` for the root development file):

```bash
docker compose -f deploy/compose/docker-compose.production.yaml exec -T db pg_dump -U camply camply > camply-backup.sql
```

To restore into a fresh database, stop the `backend`, `celery-worker`, and `celery-beat` services first so nothing writes while loading the dump.

## Upgrades and migrations

- **Standalone (`uv`):** Upgrade `camply-web` via `uv tool upgrade camply-web` (or install the new wheel) and run `camply serve`. Standalone automatically runs pending Alembic migrations on startup.
- **Docker Compose (published images):** Pull the updated image and recreate containers with `docker compose -f deploy/compose/docker-compose.production.yaml pull && docker compose -f deploy/compose/docker-compose.production.yaml up -d` (or substitute `docker-compose.yaml` / `docker-compose.standalone.yaml` under `deploy/compose/`).
- **Docker Compose (local checkout):** Rebuild and restart with `docker compose up -d --build` (or `task compose:up`). In distributed stacks, `backend` applies pending migrations before serving traffic or allowing workers to start.
- **Manual database tools:** Inspect or migrate your configured database directly with the CLI:

```bash
camply db info
camply db migrate
```

## Health checks and common issues

- **Health endpoints:** `/api/ping` confirms the API process is alive; `/api/health` verifies database connectivity (and standalone background loops) and returns HTTP `503` when unhealthy.
- **Role checks in containers:** Run `camply serve healthcheck <role>` (where `<role>` is `backend`, `worker`, or `beat`).
- **Empty catalog after install:** Open **Admin Operations** and click **Sync Providers**, or run `camply db metadata --provider-id all` to populate catalog metadata from the CLI.
- **Session login fails over HTTP:** Confirm `CAMPLY_SESSION_COOKIE_SECURE=false` and that `CAMPLY_CORS_ORIGINS` includes the exact scheme, host, and port in your browser address bar.
- **Notification links open `localhost`:** Set `CAMPLY_APP_URL` on both the API and worker to your reachable public URL.
