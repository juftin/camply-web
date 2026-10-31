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
`oci://ghcr.io/juftin/charts/camply-web`. The chart version matches the release
version and its default image is the matching `vMAJOR.MINOR.PATCH` image. The
publisher must use the existing exact-tag release workflow, publish the image
before the chart, and avoid chart publication on latest-only main builds.

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
startup blocking. Keep autoscaling, disruption budgets, and policy presets outside
this increment.
