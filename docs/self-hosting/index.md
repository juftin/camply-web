# Self-hosting camply

Run your own camply instance on a single machine, a Docker host, or a Kubernetes cluster.

## Choose a deployment option

| Option                               | Backing services                         | Best for                                             | Guide                                                     |
| ------------------------------------ | ---------------------------------------- | ---------------------------------------------------- | --------------------------------------------------------- |
| **Standalone (`uv` or 1 container)** | None (built-in SQLite)                   | Personal or small-group instances on one machine     | [Standalone](standalone.md)                               |
| **Docker Compose (Distributed)**     | PostgreSQL, Valkey, Prometheus           | Hardened multi-container hosts and monitoring charts | [Docker & Kubernetes](containers.md)                      |
| **Kubernetes (Helm)**                | PostgreSQL, Valkey (bundled or external) | Cluster deployments with Ingress or Gateway API      | [Docker & Kubernetes](containers.md#kubernetes-with-helm) |

## After your first start

1. **Secure login before sharing:** Standalone and local Compose instances default to automatic admin login (`CAMPLY_AUTH_MODE=none`), while production Compose defaults to password sessions (`CAMPLY_AUTH_MODE=session`). Configure session or Auth0 login in [Configuration](configuration.md#authentication) before exposing your instance to others.
2. **Load campgrounds:** Open **Admin Operations** in the web app and run **Sync Providers** (distributed Docker Compose runs this automatically on first boot).
3. **Configure notifications:** Set a Pushover application token or ntfy defaults in [Configuration](configuration.md#notifications) so users can receive alerts.
4. **Plan backups and upgrades:** See [Maintenance](maintenance.md) for database backups, schema migrations, and health checks.
