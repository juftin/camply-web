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
