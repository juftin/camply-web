# Implementation plan

Reference: https://github.com/juftin/home-ops/blob/main/kubernetes/workloads/apps/ntfy/values.yaml

Use native templates and existing persistence/scheduling helpers. A small Nginx sidecar enforces the upstream read endpoint allowlist for both networking APIs; expose a separate ClusterIP publishing Service. No controller-specific policy or secrets required. Derive public hostnames from the enabled Camply networking configuration. Operators provide certificates for the extra hostname. No notification application integration is implied (Camply currently has no ntfy adapter).

Constitution: infrastructure-only change, no Python package boundary or database changes. Verify real Helm renders, persistence modes, routing and denied write endpoints, plus release packaging and local OCI round trips. Update operational docs and checklist.
