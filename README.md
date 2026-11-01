<div align="center">
<a href="https://camply.juftin.dev">
  <img src="src/frontend/public/branding/camply-horizontal.svg" width="400" alt="camply">
</a>
</div>

**camply**, the campsite finder ⛺️, watches for openings at sold-out campgrounds and alerts you when a stay matches your plans. Explore campgrounds, save your dates, and follow booking links when availability appears.

**[Open camply →](https://camply.juftin.dev)**

## Run camply yourself

Install from GitHub with [uv](https://docs.astral.sh/uv/). The Git install builds the web app, so it also needs Git, Node.js 24, and pnpm (see [installation prerequisites](docs/zensical/self-hosting/standalone.md#install-from-github)).

```bash
uv tool install git+https://github.com/juftin/camply-web --with 'camply[server]' --python 3.14
camply serve
```

Open <http://127.0.0.1:8000> and use **Sync Providers** in Admin Operations to load the campground catalog. Set up Pushover to receive alerts. The default login uses a shared administrator account; [configure authentication](docs/zensical/configuration.md) before sharing your instance.

See the [standalone guide](docs/zensical/self-hosting/standalone.md) for installation and storage, or self-host with [Docker Compose](docs/zensical/self-hosting/containers.md) or [Kubernetes/Helm](deploy/helm/README.md).

## Documentation

Start with the [camply docs](https://juftin.com/camply-web/) for using the app, configuration, and self-hosting ([browse the source](docs/zensical/index.md)). Contributors can follow the [developer guide](docs/development/DEVELOPER_GUIDE.md); detailed [runtime and packaging](docs/operations/RUNNING.md) and [architecture](docs/architecture/ARCHITECTURE_DEEP_DIVE.md) references are also available.

To edit or preview the documentation, see [working on the docs](docs/zensical/development.md#working-on-the-docs).

Licensed under [PolyForm Noncommercial 1.0.0](LICENSE).
