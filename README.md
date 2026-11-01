<div align="center">
<a href="https://camply.juftin.dev">
  <img src="src/frontend/public/branding/camply-horizontal.svg" width="400" alt="camply">
</a>
</div>

**camply**, the campsite finder ⛺️, watches for openings at sold-out campgrounds and alerts you when a stay matches your plans. Explore campgrounds, save your dates, and follow booking links when availability appears.

**[Open camply →](https://camply.juftin.dev)**

## Run camply yourself

Run the web app, API, and background checks on your machine with Python and SQLite. From a checkout, with [Python 3.14, uv, Node.js 24, pnpm, and Task installed](docs/development/DEVELOPER_GUIDE.md#-prerequisites):

```bash
git clone https://github.com/juftin/camply-web.git
cd camply-web
task standalone:install
task standalone:build
task standalone:run
```

Open <http://127.0.0.1:8000> and use **Sync Providers** in Admin Operations to load the campground catalog. Set up Pushover to receive alerts. The default login uses a shared administrator account; [configure authentication](docs/zensical/configuration.md) before sharing your instance.

See the [standalone guide](docs/zensical/self-hosting/standalone.md) for installation and storage, or self-host with [Docker Compose](docs/zensical/self-hosting/containers.md) or [Kubernetes/Helm](deploy/helm/README.md).

## Documentation

Start with the [camply docs](https://juftin.com/camply-web/) for using the app, configuration, and self-hosting ([browse the source](docs/zensical/index.md)). Contributors can follow the [developer guide](docs/development/DEVELOPER_GUIDE.md); detailed [runtime and packaging](docs/operations/RUNNING.md) and [architecture](docs/architecture/ARCHITECTURE_DEEP_DIVE.md) references are also available.

Preview the Zensical documentation locally at <http://127.0.0.1:8001>:

```bash
task docs:serve
```

`task docs:build` generates the static site in `build/docs`. Both commands need only uv and Task; see [working on the docs](docs/zensical/development.md#working-on-the-docs).

Licensed under [PolyForm Noncommercial 1.0.0](LICENSE).
