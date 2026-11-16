# Maintenance

Follow these procedures to back up data, upgrade versions, inspect database state, and check instance health.

## Backups and restores

### Standalone (SQLite)

Never copy a live SQLite database file while camply is writing to its WAL journal. Either stop camply before copying the file, or use SQLite's online backup command:

```bash
sqlite3 ~/.local/share/camply/camply.db ".backup /path/to/camply-backup.db"
```

To restore, stop camply, replace the database file at `CAMPLY_DB_HOST` (or the default path), remove any stale `-wal` and `-shm` files from the old database, and start camply again.

### Docker Compose (PostgreSQL)

Dump the database from the running `db` container:

```bash
docker compose exec -T db pg_dump -U camply camply > camply-backup.sql
```

To restore into a fresh database, stop the `backend`, `celery-worker`, and `celery-beat` services first so nothing writes while loading the dump.

## Upgrades and migrations

- **Standalone:** Upgrade `camply-web` via `uv tool upgrade camply-web` (or install the new wheel) and run `camply serve`. Standalone automatically runs pending Alembic migrations on startup.
- **Docker Compose:** Pull or rebuild images with `docker compose up -d --build`. The `backend` service applies pending migrations before serving traffic or allowing workers to start.
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
