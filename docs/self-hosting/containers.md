# Docker and Kubernetes

Distributed deployments run the API, frontend Nginx proxy, worker, and scheduler as separate services alongside PostgreSQL, Valkey, and Prometheus.

## Docker Compose

Clone the repository, create a `.env` file, and start the stack:

```bash
git clone https://github.com/juftin/camply-web.git
cd camply-web
cp docs/examples/.env.example .env
docker compose up -d --build
```

Open <http://localhost> (port `80` by default, controlled by `FRONTEND_PORT`). The scheduler triggers the initial provider sync once the API passes migrations and health checks.

Before sharing the instance, edit `.env` to set `CAMPLY_APP_URL` to your reachable frontend address, configure [authentication](configuration.md#authentication), and set up [notifications](configuration.md#notifications).

Useful lifecycle commands:

```bash
docker compose ps
docker compose logs -f
docker compose down
```

`docker compose down` keeps named Docker volumes (`db_data`, `valkey_data`, `prometheus_data`) and `.data/camply` intact. See [Maintenance](maintenance.md) for backup and upgrade steps.

## Kubernetes with Helm

The [camply Helm chart](https://github.com/juftin/camply-web/blob/main/deploy/helm/README.md) deploys the distributed stack with migration startup gates, health probes, persistent storage, optional bundled PostgreSQL/Valkey, and Ingress or Gateway API routing.

Follow the chart README for installation and values configuration, and use [Configuration](configuration.md) for auth, notification, and `CAMPLY_APP_URL` settings.
