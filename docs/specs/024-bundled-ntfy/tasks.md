# Tasks

- [x] Inspect home-ops ntfy configuration and existing chart/release behavior.
- [x] Add persistent single-replica ntfy, public read-only proxy, private publishing Service, routing and schema.
- [x] Publish one semantic chart version on stable releases only.
- [x] Verify renders, storage, hostname/TLS overrides, actual proxy boundary, and local release packages.
- [x] Update chart guide, release operations, and global checklist.

Validation: `task helm:test`; live proxy checks with `CAMPLY_TEST_NGINX` using a local Nginx binary. Cluster smoke remains opt-in and needs a Docker daemon; unavailable in this workspace.
