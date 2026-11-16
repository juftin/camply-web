# Technical and Architectural Documentation

This section covers how camply is built, how to set up a local development environment, and how the subsystems fit together.

## Contributing and local setup

- [Contributing](../CONTRIBUTING.md) — Pull requests, worktrees, and commit conventions.
- [Developer Guide](../development/DEVELOPER_GUIDE.md) — Local environment, Task workflows, tests, and editing docs.
- [Style Guide](../development/STYLE_GUIDE.md) — Backend, frontend, testing, and documentation standards.

## System architecture

- [Polling Engine](../architecture/ARCHITECTURE_DEEP_DIVE.md) — Package boundaries and the de-duplicated availability poller.
- [Data Model](../architecture/DESIGN_DATA.md) — Multi-tenant schema, availability snapshots, and outbox tables.
- [Providers](../architecture/DESIGN_PROVIDERS.md) — Provider abstractions, catalog sync, and enrichment.
- [Notifications](../architecture/DESIGN_NOTIFICATIONS.md) — Outbox coalescing and Pushover/ntfy delivery.
- [API & Security](../architecture/DESIGN_API.md) — FastAPI endpoints, authentication modes, and standalone serving.
- [Frontend](../architecture/DESIGN_FRONTEND.md) — React application, MapLibre explore view, and docs bundling.

Looking for environment-variable tables, packaging contracts, or feature specs? See [Technical Reference](../reference.md).
