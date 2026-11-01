# Run camply on your machine

Standalone camply serves the web app, API, and background polling in one Python process. It stores your catalog, scans, and pending alerts in SQLite. This is the simplest setup for a personal instance.

## Run from a checkout

Install Python 3.14, [uv](https://docs.astral.sh/uv/), Node.js 24, the pnpm version pinned in `package.json`, and [Task](https://taskfile.dev/installation/). Enable pnpm with `corepack enable`; install Corepack first if your Node installation does not include it.

```bash
git clone https://github.com/juftin/camply-web.git
cd camply-web
task standalone:install
task standalone:build
task standalone:run
```

Open <http://127.0.0.1:8000>. Use **Sync Providers** in Admin Operations to import the campground catalog, then [create a scan](../using-camply.md). Configure [Pushover](../configuration.md#notifications) to receive alerts.

Docker, PostgreSQL, and Valkey are not required for this workflow. Internet access is needed for catalog imports, availability checks, and notifications.

## Run a prepared wheel

If you have a built camply wheel, install it into a Python environment with the `server` extra. Package consumers need Python 3.11 or later. For example, from the directory containing the downloaded wheel:

```bash
uv venv --python 3.14
uv pip install './camply-0.1.0-py3-none-any.whl[server]'
uv run --no-project camply serve
```

Replace the wheel filename with your actual artifact. Prepared wheels include the web app, so Node and pnpm are only needed when building from source. See [building and installing distributions](https://github.com/juftin/camply-web/blob/main/docs/operations/RUNNING.md#build-and-install-the-complete-application) for the full artifact workflow.

## Storage and backups

By default, SQLite lives in your platform's camply application-data directory, such as `~/.local/share/camply/camply.db` on Linux. Set `CAMPLY_DB_HOST` to an absolute writable file path to choose another location. Keep that file between runs.

Stop camply before copying the database for a backup, or use SQLite's online backup API. To restore, stop the app, replace the database with a consistent backup, and restart. Run only one standalone process against a database.

## Share an instance

The default authentication mode signs everyone in as a shared administrator. [Set up session or Auth0 login](../configuration.md#authentication) before making the app available to others.

To change the listener from a checkout:

```bash
task standalone:run -- --host 0.0.0.0 --port 8000
```

With an installed package, use `camply serve --host 0.0.0.0 --port 8000`. For HTTPS hosting, place the listener behind a reverse proxy and set `CAMPLY_APP_URL` to the public URL so notification links point to your instance.

Standalone supports personal and small-instance workloads. Historical monitoring charts use the [distributed deployment](containers.md). For scheduling, recovery, and health-check details, see the [runtime reference](https://github.com/juftin/camply-web/blob/main/docs/operations/CONFIGURATION.md#runtime-selection).
