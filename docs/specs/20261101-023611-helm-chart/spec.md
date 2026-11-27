# Camply Helm chart

Provide a self-contained Helm chart at `deploy/helm` matching the distributed
home-ops deployment: frontend, API, worker, singleton beat with initial provider
sync, PostgreSQL, durable Valkey, and Prometheus with API/worker scraping.

Operators can use controller-independent Ingress or Gateway API HTTPRoute,
optionally create a Gateway, configure TLS/annotations, select storage classes,
reuse PVCs, and replace bundled backing services with external services. Runtime
configuration and secrets support Kubernetes env/valueFrom and envFrom without
embedding credentials in chart defaults.

A migration Job must finish successfully before new API, worker, and beat
containers start, on both installation and upgrade, including Argo CD rendering.
Failures must keep new application processes stopped. Existing processes during
rolling upgrades are not stopped; migrations must remain backwards compatible.

Stable application releases must publish the chart as `camply-web` to
`oci://ghcr.io/juftin/charts/camply-web`. Release charts expose `vMAJOR`,
`vMAJOR.MINOR.PATCH`, the seven-character Git SHA, and `latest` OCI tags; each
defaults to the identically tagged upstream image. Preserve the unprefixed semantic release tag for compatibility. Successful
main builds without a release publish SHA and latest charts after those images.
The publisher uses the checked-out source revision and valid semantic chart
metadata; it never edits source chart metadata. Explicit image overrides remain
supported.

## Operator experience

Validate chart values with JSON Schema, including known-key typo detection and
external-service/routing requirements. Keep environment variables, annotations,
and native Kubernetes extension objects open to user configuration.

Expose per-role startup/readiness/liveness probe overrides, with API liveness
using `/api/ping` and readiness using a bounded database check at `/api/health`.
Retain standalone runner health checks and existing public health response shapes.

Offer an opt-in Prometheus Operator ServiceMonitor using existing metrics Services,
without installing CRDs or another Prometheus. Print install and troubleshooting
instructions through NOTES, and provide a read-only `helm test` connection check.

Run the kind lifecycle test in CI against a source-built image. Verify migration
ordering, a successful upgrade with preserved database data, and failed-upgrade
startup blocking, and rollback against a newer backward-compatible schema without
rerunning older migrations. Record successful migration checkpoints in the target
database so rollback survives Job pruning under Helm 3/4 and GitOps. Restart bundled Prometheus whenever its
rendered scrape configuration changes. Keep autoscaling, disruption budgets, and
policy presets outside this increment.
