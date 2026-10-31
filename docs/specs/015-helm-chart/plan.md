# Implementation plan

1. Audit home-ops values and installed runtime commands; preserve health probes,
   graceful frontend shutdown, metrics, persistence, session configuration,
   initial provider sync, and resource/security settings.
2. Add a dependency-free chart with optional backing services, reusable storage
   templates, Ingress/HTTPRoute/Gateway, and documented example values.
3. Use a normal revision-specific migration Job and narrowly scoped Job-read RBAC.
   Mount a projected token only in the waiting init container. Avoid hooks and sync
   waves that would block first-install database creation. Gate every API, worker,
   and beat pod on the current Job's Complete condition; disable launcher migrations.
4. Add rendered-manifest and gate behavior regressions, Task entrypoints, CI checks,
   installation/upgrade guidance, and the global checklist entry.

## Constitution check

No application dependencies or internal module boundaries change. Python scripts
use only the standard library. All verification is exposed through Task. Tests
cover startup failures and upgrade identity as well as user-facing configuration.

## OCI publication

1. Rename the chart to `camply-web` while retaining `nameOverride: camply` so
   existing Kubernetes resource names and selectors remain stable.
2. Default image tags to Chart.appVersion when not explicitly overridden. Package
   release charts with version `MAJOR.MINOR.PATCH` and appVersion `vMAJOR.MINOR.PATCH`.
3. Add a CI-only stable-version Task that packages and pushes to
   `oci://ghcr.io/juftin/charts`. Invoke it after the existing exact-release image
   publication, with a separate Helm registry login using the runtime GITHUB_TOKEN.
4. Verify real package metadata and rendered images with a recorded registry push,
   invalid publication contexts, and release-only workflow ordering on Helm 3/4.
