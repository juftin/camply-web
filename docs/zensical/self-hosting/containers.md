# Docker and Kubernetes

The distributed deployment runs the API, frontend, worker, and scheduler as separate services, with PostgreSQL, Valkey, and Prometheus. Choose [standalone](standalone.md) for a simpler personal setup.

## Docker Compose

Install Docker with Compose and [Task](https://taskfile.dev/installation/), then run from the checkout root:

```bash
git clone https://github.com/juftin/camply-web.git
cd camply-web
cp docs/examples/.env.example .env
task compose:up
```

This builds the application image locally and starts the full stack. Open <http://localhost> (port 80 by default, configurable with `FRONTEND_PORT`). The API is available on port 8000. The scheduler queues the initial provider catalog sync after the API's migrations and health check succeed.

Edit `.env` for your instance. Set `CAMPLY_APP_URL` to the address you actually use, such as `http://localhost`, so alert links open the correct frontend. Set `PUSHOVER_APP_TOKEN` and each user's key for alerts. Compose defaults to automatic administrator login; configure [authentication](../configuration.md#authentication) before exposing it to other users.

```bash
task compose:ps
task compose:logs
task compose:down
```

PostgreSQL, Valkey, and Prometheus use named Docker volumes; application data also uses `.data/camply`. `task compose:down` preserves volumes. Back up persistent data before upgrading or removing volumes.

The shared application image is `ghcr.io/juftin/camply-web`. The checkout's Compose tasks build it locally; published version tags are available for custom deployments. See the [runtime and image reference](https://github.com/juftin/camply-web/blob/main/docs/operations/RUNNING.md#develop-from-the-repository-root) for role commands, startup ordering, and shutdown behavior.

## Kubernetes with Helm

The [camply Helm chart](https://github.com/juftin/camply-web/blob/main/deploy/helm/README.md) supports the distributed stack, optional bundled backing services, persistent storage, and Ingress or Gateway API routing. It includes migration startup gates and health checks.

Follow the chart's installation guide and example values for your cluster. Use its secret references for credentials and choose persistent storage or external PostgreSQL/Valkey services. See [configuration](../configuration.md) for login, alerts, and the public application URL.
