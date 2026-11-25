# Standalone hosting

Standalone mode serves the web app, API, and background polling from one Python process backed by SQLite. It needs no Docker, PostgreSQL, or Valkey.

## Run with uv

Start camply directly with [uv](https://docs.astral.sh/uv/):

```bash
uvx --from "camply-web[server]" camply serve
```

Or install it as a persistent CLI tool:

```bash
uv tool install "camply-web[server]"
camply serve
```

If you downloaded a release wheel, install it from the folder containing the file:

```bash
uv tool install './camply_web-0.1.0-py3-none-any.whl[server]'
camply serve
```

Open <http://127.0.0.1:8000>. Run **Sync Providers** in **Admin Operations** to import the campground catalog, then create a scan from [Using the web app](../using-camply.md).

## Run with Docker Compose

Prefer a single container without PostgreSQL, Valkey, or Prometheus? Use `deploy/compose/docker-compose.standalone.yaml`, which runs `camply serve` from the published `ghcr.io/juftin/camply-web` image and persists SQLite in a named Docker volume:

```bash
docker compose -f deploy/compose/docker-compose.standalone.yaml up -d
```

The container binds `127.0.0.1:8000` by default (override with `CAMPLY_BIND` and `CAMPLY_PORT`) and persists `/home/camply/.local/share/camply` in the `camply_data` volume. Configure authentication, `CAMPLY_APP_URL`, and notifications via a `.env` file alongside the Compose file; see [Docker & Kubernetes](containers.md) for reverse-proxy TLS setup and distributed Compose options.

## Expose on your network

By default, standalone camply listens only on `127.0.0.1:8000` and signs every visitor in as a shared administrator.

Before sharing the instance, [enable authentication](configuration.md#authentication) and bind to your network interface:

```bash
camply serve --host 0.0.0.0 --port 8000
```

When serving behind an HTTPS reverse proxy, set `CAMPLY_APP_URL` to your public URL (including any path prefix) so links inside alert messages open the right address.

## Storage and limits

SQLite stores the catalog, scans, and pending alerts in your platform's user data directory (such as `~/.local/share/camply/camply.db` on Linux). Set `CAMPLY_DB_HOST` to an absolute writable path to store it elsewhere.

Run only one standalone process against a given SQLite file. For multi-worker scaling or historical worker metrics charts, use [Docker Compose or Kubernetes](containers.md). For backups and upgrades, see [Maintenance](maintenance.md).
