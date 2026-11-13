<div align="center">
<a href="https://camply.rocks">
  <img src="src/frontend/public/branding/camply-horizontal.svg" width="400" alt="camply">
</a>
</div>

**camply**, the campsite finder ⛺️, watches for openings at sold-out campgrounds and alerts you when a stay matches your plans. Explore campgrounds, save your dates, and follow booking links when availability appears.

**[Open camply →](https://camply.rocks)**

## Run camply yourself

Run camply directly with [uv](https://docs.astral.sh/uv/):

```bash
uvx --from "camply-web[server]" camply serve
```

Open <http://127.0.0.1:8000> and use **Sync Providers** in Admin Operations to load the campground catalog. Set up Pushover to receive alerts. The default login uses a shared administrator account; [configure authentication](docs/configuration.md) before sharing your instance.

See the [standalone guide](docs/self-hosting/standalone.md) for installation and storage, or self-host with [Docker Compose](docs/self-hosting/containers.md) or [Kubernetes/Helm](deploy/helm/README.md).

For terminal-only discovery and availability monitoring, run
`uvx --from camply-web camply providers` and follow the [command-line guide](docs/cli.md).
This workflow needs no web account, database or server extras; results appear in
your terminal.

## Docs

Start with the [camply docs](https://camply.rocks/docs/) for using the app, configuration, and self-hosting ([browse the source](docs/index.md)). Every installation includes docs at `/docs/`, linked from the app footer. Contributors can follow the [contributing guide](docs/CONTRIBUTING.md) and [developer guide](docs/development/DEVELOPER_GUIDE.md); detailed [runtime and packaging](docs/operations/RUNNING.md) and [architecture](docs/architecture/ARCHITECTURE_DEEP_DIVE.md) references are also available.

To edit or preview the docs, see [working on the docs](docs/development.md#working-on-the-docs).

Licensed under [GNU Affero General Public License v3.0](LICENSE).
