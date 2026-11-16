<div align="center">
<a href="https://camply.rocks">
  <img src="src/frontend/public/branding/camply-horizontal.svg" width="400" alt="camply">
</a>
</div>

camply watches for openings at sold-out campgrounds and notifies you when a stay matches your dates. Use it online at **[camply.rocks](https://camply.rocks)**, from your terminal, or on your own server.

## Quick start

Run the full web app on your own machine with [uv](https://docs.astral.sh/uv/):

```bash
uvx --from "camply-web[server]" camply serve
```

Open <http://127.0.0.1:8000>, run **Sync Providers** in Admin Operations to load campgrounds, and configure Pushover or ntfy for alerts. Set up authentication before exposing a self-hosted instance to other people.

For terminal-only searches without a database or web server:

```bash
uvx --from camply-web camply providers
```

## Documentation

Read the docs at [camply.rocks/docs](https://camply.rocks/docs/) (also served at `/docs/` on every self-hosted instance):

- **User Documentation:** [Web app guide](docs/using-camply.md) and [CLI guide](docs/cli.md).
- **Self-Hosting:** [Deployment options](docs/self-hosting/index.md), [standalone setup](docs/self-hosting/standalone.md), [Docker & Kubernetes](docs/self-hosting/containers.md), and [configuration](docs/self-hosting/configuration.md).
- **Contributors:** [Technical & Architectural Documentation](docs/technical/index.md) and [Technical Reference](docs/reference.md).

Licensed under [GNU Affero General Public License v3.0](LICENSE).
