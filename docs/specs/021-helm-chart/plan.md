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

No application dependencies or internal module boundaries change. The wait script
uses the standard library; the migration wrapper uses PostgreSQL/Alembic dependencies
already installed in the image. All verification is exposed through Task. Tests
cover startup failures and upgrade identity as well as user-facing configuration.

## OCI publication

1. Rename the chart to `camply-web` while retaining `nameOverride: camply` so
   existing Kubernetes resource names and selectors remain stable.
2. Default image tags to Chart.appVersion when not explicitly overridden. Package
   release charts with version `MAJOR.MINOR.PATCH` and appVersion `vMAJOR.MINOR.PATCH`.
3. Add a CI-only Task that packages variants and publishes OCI tags to
   `oci://ghcr.io/juftin/charts` after matching images, using ORAS with the existing
   Docker login and runtime GITHUB_TOKEN for release and main publication.
4. Verify real package metadata and rendered images with recorded registry writes,
   invalid contexts, upload failures, and image-before-chart ordering on Helm 3/4.

## Operator experience implementation

1. Write regressions for invalid values, probe overrides, ServiceMonitor selectors,
   installation notes, Helm test resources, and readiness failure/liveness isolation.
2. Add a static values schema; merge native probe overrides with defaults, supporting
   explicit disablement and handler replacement. Check database readiness with a
   bounded query through the existing overridable FastAPI session dependency.
3. Add an opt-in ServiceMonitor, component labels on metrics Services, NOTES, and
   a read-only test Pod using the same application image and no API credentials.
4. Build/load a unique local image for kind smoke; extend the test with successful
   upgrade/data survival and failure diagnostics. Reuse the existing CI image build
   to execute the smoke test rather than creating another container build job.
5. Verify both Helm versions, API contract drift, backend/frontend quality gates,
   and the full test suite; update docs/checklist and the existing PR.

No new runtime dependencies or infrastructure controllers are introduced. Helm's
schema validates values; the optional ServiceMonitor requires an existing CRD.

## Review fixes

1. Reproduce rollback migration failures and missing Prometheus scrape reload with
   rendered-manifest regressions before changing templates.
2. Record successful Job identities in the target database after Alembic finishes.
   Recreated rollback Jobs reuse these checkpoints across Helm 3/4 and GitOps
   pruning; fresh databases always run migrations. Keep existing read-only RBAC.
3. Hash the rendered Prometheus configuration to restart it when worker scraping
   changes, without restarting it just because worker replica counts change.
4. Extend the source-image lifecycle smoke with a synthetic newer database
   revision, failed-upgrade recovery, and rollback that recreates the original Job
   while reusing its database checkpoint and preserving database contents. Run
   Helm 3/4 and project checks before updating the PR.

## Matching OCI chart and image tags

1. Package separate chart variants with appVersion equal to each upstream image
   tag: full release, major alias, short SHA, and latest. Preserve `1.2.3` as an
   alias of `v1.2.3` for existing consumers. On main builds publish SHA/latest only.
2. Keep Chart.version semantic: the release version, or `0.0.0-sha-<short-sha>`
   for main builds. Use ORAS with Helm config/content media types to publish
   arbitrary OCI aliases, using the existing Docker registry credentials.
3. Validate CI, stable release versions, and revisions before packaging. Upload
   charts only after image publication succeeds, and propagate upload failures.
4. Verify real archives/renders for every tag, invalid contexts, upload failures,
   image publication plans, and workflow ordering. Verify OCI installs by digest
   with Helm 3 and 4; document resolving aliases with ORAS to bypass Helm CLI
   semantic version tag filtering. No runtime dependencies or application
   architecture changes.
