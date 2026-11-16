# Self-hosting camply

Run your own camply instance on a single machine, a Docker host, or a Kubernetes cluster.

## Choose a deployment option

| Option                | Backing services                         | Best for                                               | Guide                                                     |
| --------------------- | ---------------------------------------- | ------------------------------------------------------ | --------------------------------------------------------- |
| **Standalone**        | None (built-in SQLite)                   | Personal or small-group instances on one machine       | [Standalone](standalone.md)                               |
| **Docker Compose**    | PostgreSQL, Valkey, Prometheus           | Multi-container hosts and historical monitoring charts | [Docker & Kubernetes](containers.md)                      |
| **Kubernetes (Helm)** | PostgreSQL, Valkey (bundled or external) | Cluster deployments with Ingress or Gateway API        | [Docker & Kubernetes](containers.md#kubernetes-with-helm) |

## After your first start

1. **Secure login before sharing:** New instances default to automatic admin login (`CAMPLY_AUTH_MODE=none`). Set up session or Auth0 login in [Configuration](configuration.md#authentication) before exposing your instance to others.
2. **Load campgrounds:** Open **Admin Operations** in the web app and run **Sync Providers** (Docker Compose runs this automatically on first boot).
3. **Configure notifications:** Set a Pushover application token or ntfy defaults in [Configuration](configuration.md#notifications) so users can receive alerts.
