# Run camply on your machine

Standalone camply serves the web app, API, and background polling in one Python process. It stores your catalog, scans, and pending alerts in SQLite. This is the simplest setup for a personal instance.

## Quick start with uvx

Run camply directly with [uv](https://docs.astral.sh/uv/):

```bash
uvx --from "camply-web[server]" camply serve
```

Open <http://127.0.0.1:8000>. Use **Sync Providers** in Admin Operations to import the campground catalog, then [create a scan](../using-camply.md). Configure [Pushover](../configuration.md#notifications) to receive alerts.

The `server` extra installs the dependencies needed to serve the app.

Docker, PostgreSQL, and Valkey are not required for this workflow. Internet access is needed for catalog imports, availability checks, and notifications.

## Install as a tool

To install camply into a persistent tool environment:

```bash
uv tool install "camply-web[server]"
camply serve
```

uv exposes the `camply` command on your PATH. If your shell cannot find it, run `uv tool update-shell` and restart your shell.

## Run a prepared wheel

If you have a prepared camply-web wheel, install it with uv from the directory containing the downloaded file:

```bash
uv tool install './camply_web-0.1.0-py3-none-any.whl[server]'
camply serve
```

Replace the wheel filename with your actual artifact. Prepared wheels include the web app, so Node and pnpm are only needed when building from source. See [building and installing distributions](https://github.com/juftin/camply-web/blob/main/docs/operations/RUNNING.md#build-and-install-the-complete-application) for the full artifact workflow.

## Storage and backups

By default, SQLite lives in your platform's camply application-data directory, such as `~/.local/share/camply/camply.db` on Linux. Set `CAMPLY_DB_HOST` to an absolute writable file path to choose another location. Keep that file between runs.

Stop camply before copying the database for a backup, or use SQLite's online backup API. To restore, stop the app, replace the database with a consistent backup, and restart. Run only one standalone process against a database.

## Share an instance

The default authentication mode signs everyone in as a shared administrator. [Set up session or Auth0 login](../configuration.md#authentication) before making the app available to others.

To change the listener:

```bash
camply serve --host 0.0.0.0 --port 8000
```

For HTTPS hosting, place the listener behind a reverse proxy and set `CAMPLY_APP_URL` to the public URL so notification links point to your instance.

Standalone supports personal and small-instance workloads. Historical monitoring charts use the [distributed deployment](containers.md). For scheduling, recovery, and health-check details, see the [runtime reference](https://github.com/juftin/camply-web/blob/main/docs/operations/CONFIGURATION.md#runtime-selection).
