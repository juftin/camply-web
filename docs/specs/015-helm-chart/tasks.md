# Tasks

- [x] Audit deployment parity and define chart behavior.
- [x] Implement workloads, storage, routing, and migration gating.
- [x] Add configuration examples and operator documentation.
- [x] Verify render matrix and migration gate failure/success behavior.
- [x] Integrate Task/CI checks and update global checklist.

## Release publication

- [x] Rename chart to `camply-web` while preserving default resource names.
- [x] Package stable release versions with matching image defaults and add GHCR publication.
- [x] Run chart publication only after the exact release image succeeds; use runtime credentials.
- [x] Add archive/render, invalid-context, and workflow publication regressions.
- [x] Verify publication checks on Helm 3/4 and update operator documentation.

## Verification

- `task fix`, `task lint`, and `task check` passed.
- `task backend:test`: 802 passed, 23 opt-in tests skipped.
- `task frontend:test`: 339 passed.
- `task release:test`: 15 passed.
- Full `task test` passed, including 68 packaging tests and Pages configuration/bundling/HTTP verification.
- Pre-commit hooks passed.
- `task helm:test`: 41 passed, one opt-in cluster smoke skipped, on Helm 3.19.0 and 4.3.0.
- `task backend:check -- tests/helm deploy/helm/files` passed.
- Kubeconform accepted all 24 default Kubernetes resources; chart packaging passed.
- Actionlint accepted the workflow changes with its optional ShellCheck integration disabled.
- Registry pushes were recorded locally; actual GHCR publication runs from the stable release workflow.
- `task helm:smoke` was attempted, but Docker could not pull the kind node image:
  `no space left on device`. The partial test-owned cluster was removed.
  Real cluster startup and failed-upgrade verification remain unverified locally.
