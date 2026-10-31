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

- `task fix`, `task lint`, `task check`, and pre-commit hooks passed.
- Full `task test` passed: 818 backend tests (23 opt-in skips), 68 packaging tests,
  339 frontend tests, 15 release checks, and Pages configuration/bundling/HTTP checks.
- `task helm:test`: 54 passed, one opt-in cluster smoke skipped, on Helm 3.19.0 and 4.3.0.
- `task helm:smoke`: all 55 tests passed locally on ARM64 with Helm 4.3.0 and
  kind 0.33.0 / Kubernetes 1.37.0, using an image built from this checkout.
  Verified migration ordering, both Helm connection tests, successful upgrade
  with PostgreSQL data preservation (`SELECT value FROM helm_upgrade_proof` returned
  `42`), and failed-migration startup blocking for backend, worker, and beat.
- `task backend:check -- tests/helm deploy/helm/files` and API contract checks passed.
- Kubeconform accepted all 25 default Kubernetes resources; chart packaging passed.
- Actionlint accepted the workflow changes with its optional ShellCheck integration disabled.
- Registry pushes were recorded locally; actual GHCR publication runs from the stable release workflow.

## Operator experience

- [x] Add schema, probe, monitoring, notes/test, and readiness regressions.
- [x] Implement schema validation and configurable probes.
- [x] Make API readiness depend on the database while keeping liveness independent.
- [x] Add ServiceMonitor, install notes, and a read-only Helm connection test.
- [x] Run source-image lifecycle smoke in CI with upgrade/data preservation checks.
- [x] Complete validation and update documentation and PR.

Operator verification: Helm 3/4 regressions cover schema failures, probe
replacement/disablement, monitor selection, rendered notes, and the test hook.
API readiness and liveness checks, full project checks, and the local source-image
Kubernetes lifecycle smoke passed.

## Local cluster testing

- [x] Diagnose local storage exhaustion and document smoke-test disk requirements.
- [x] Initialize the CI lifecycle job's Task/Python environment before installing Helm/kind.
- [x] Reproduce the missing CI setup with a regression, then verify the fix.
- [x] Complete the local Kubernetes lifecycle test after freeing sufficient disk space.

Follow-up validation: the source image builds and the complete local lifecycle
smoke passed (55 tests, 135 seconds). Resource and log diagnostics are retained
under `tmp/camply-helm-c756fd0e/`. The test-owned cluster was removed. The same lifecycle smoke also passed in
[CI on AMD64](https://github.com/juftin/camply-web/actions/runs/41235448171); all
checks in that run passed. Approved Docker cleanup preserved the existing
running services while removing unused data.
