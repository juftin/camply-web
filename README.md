<div align="center">
<a href="https://camply.rocks">
  <img src="src/frontend/public/branding/camply-horizontal.svg" width="400" alt="camply">
</a>
</div>

**`camply`**, the campsite finder ⛺️, is a tool to help you book a campsite online. Finding reservations at sold out campgrounds can be tough. That's where camply comes in. It searches thousands of campgrounds across the world via the APIs of booking services like [recreation.gov](https://recreation.gov). It continuously checks for cancellations and availabilities to pop up - once a campsite becomes available, camply sends you a notification to book your spot!

Use it online at **[camply.rocks](https://camply.rocks)**, from your terminal, or on your own server.

> [!NOTE]
> This repository is where **camply v2** is being developed. Once v2 reaches a stable release, it will move back to [github.com/juftin/camply](https://github.com/juftin/camply) and the package will be renamed from `camply-web` to `camply`. As a major release, v2 introduces breaking changes to the CLI and configuration compared to v1.

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
- **Self-Hosting:** [Deployment options](docs/self-hosting/index.md), [standalone setup](docs/self-hosting/standalone.md), [Docker & Kubernetes](docs/self-hosting/containers.md), [configuration](docs/self-hosting/configuration.md), and [maintenance](docs/self-hosting/maintenance.md).
- **Contributors:** [Technical & Architectural Documentation](docs/technical/index.md) and [Technical Reference](docs/reference.md).
