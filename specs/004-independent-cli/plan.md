# Implementation Plan: Independent CLI on the Modern Engine

**Date**: 2026-10-12
**Status**: Proposed; no implementation or runtime validation completed
**Specification**: [spec.md](spec.md)
**Detailed design**: [DESIGN_CLI.md](../../docs/agents/DESIGN_CLI.md)
**Tasks**: [tasks.md](tasks.md)

## Summary

Publish a replacement standalone `camply` CLI backed by a shared library extracted from the modern backend. Keep persistence, user policies, and distributed orchestration in existing backend packages. Retire the old engine after the replacement's explicitly bounded first-release capabilities pass installed-artifact and backend regression gates.

The detailed design is the authoritative package, domain, command, monitoring, configuration, release, and migration contract. This plan records delivery dependencies and verification checkpoints rather than duplicating that document.

## Technical context

- **Language:** Python 3.12+ for new core/CLI packages; audit affected existing Python declarations.
- **Runtime:** Existing Pydantic v2, HTTPX, structlog; Click/Rich in CLI; platformdirs for local paths; Pydantic settings for CLI configuration.
- **Build/dependencies:** Hatchling and uv; unified Python workspace in `backend/` with `packages/*` members and single `uv.lock`.
- **Storage:** Existing backend PostgreSQL unchanged; standalone metadata archive/JSON cache and session-only monitoring state.
- **Testing:** pytest, existing provider VCR fixtures, mock HTTP transports, fake clocks, backend regressions, clean artifact installs.
- **Platforms:** Linux, macOS, Windows for public CLI entry points and filesystem behavior.
- **First release:** Recreation.gov, one campground/window, implemented backend filters, local discovery, watch mode, Pushover.
- **Constraints:** No legacy fallback; no backend service runtime dependency; no new DB schema; no silent API/task payload incompatibility.

## Delivery order

### Phase 0: Contracts and baseline

Record current backend checks and provider/filter expectations. Confirm publishing identity, licensing/provenance, version policy, and Python support declarations. Add regression cases for checkout exclusion, unknown statuses, and duplicate-date runs before changing those behaviors.

**Gate:** The proposed public contracts and intentional behavior corrections are captured in tests; current failures are distinguished from extraction failures.

### Phase 1: Provider extraction

Create `backend/packages/core/` with namespace `camply_core` in the existing backend workspace. Move provider transport, models, client, descriptor/registry, and metadata parsing there. Use backend adapters for database population and numeric provider lookup. Expose core-specific build/artifact tasks without requiring service setup.

**Gate:** Backend provider/metadata tests pass, registry IDs are unchanged, and an installed core artifact performs a mocked availability check without service packages/settings.

### Phase 2: Shared matching and notifications

Extract filters, consecutive stays, snapshot comparison, notification DTOs, and explicit-credential Pushover delivery into core. Adapt workers while retaining task signatures, eligibility checks, locks, transactions, and metrics. Cover separate event-loop lifecycle and cleanup.

**Gate:** Existing worker integration checks pass; shared matching tests and old serialized notification payload tests pass; no duplicate provider/delivery implementation remains.

### Phase 3: Standalone CLI in backend/packages/cli

Configure modern package metadata for `camply` in `backend/packages/cli/`, nested alongside `core`, `db`, `providers`, `worker`, and `backend` in the uv workspace. Regenerate `backend/uv.lock`. Do not resolve the legacy Pydantic v1 CLI in the modern workspace. 

Implement one-shot arguments/configuration/output first, then catalogue discovery, local watch, notifications, and interruption. Ensure tests in `backend/packages/cli/tests/` remain isolated from legacy fixtures while old source coexists.

**Gate:** Member synchronization and backend container startup pass; all first-release command scenarios pass from installed artifacts; no CLI imports of legacy or backend integration packages.

### Phase 4: Independent release pipeline

Integrate Task/pre-commit/root CI, supported-platform checks, core/CLI wheels/source distributions, and exact-artifact publication. Configure component tags and Trusted Publishers. Resolve a required core release before dependent CLI release; validate prereleases outside the checkout.

**Gate:** Release candidates build and install independently, version/tag checks pass, and application-only changes do not release CLI packages.

### Phase 5: Stable cutover and retirement

Document removed features/flags, units, credentials, Python support, restart semantics, and pinning. Update architecture/configuration/developer docs and agent pointers. Remove legacy root `cli/` runtime/tooling/tests after replacement acceptance.

**Gate:** Root checks, backend regressions, CLI/core artifact checks, and applicable API contract checks pass; the stable distribution and source tree contain only the new engine integration.

## Constitution check

| Principle | Compliance |
| --- | --- |
| Reliability and precision | Live checks, explicit availability statuses and dates, failure-safe snapshot handling, documented delivery limitations |
| Type safety | Typed Pydantic contracts/adapters, strict static analysis and lint gates |
| Modern automation | All workflows exposed through Task, uv dependency/lock management |
| Monorepo separation | CLI nested under `backend/packages/cli` alongside `core`/`db`/`worker`, shared core in `backend/packages/core`, infrastructure in backend adapters |
| Automated verification | Behavior/regression/provider integration and installed-artifact tests |

No source/runtime boundary exception is planned. The unified backend workspace shares Python resolution and development setup across `packages/*`; component distribution/release boundaries remain separate. Two published packages are justified by two real consumers and ordinary standalone installation. Extra persistence systems and provider plugin packages are deferred.

## Validation record

Design preparation involved source/documentation inspection only. Implementation tests, artifact builds, publication, and live provider checks have not been performed. During implementation, record commands and actual results in `validation.md`, then mark corresponding feature/global checklist entries complete only after their gates pass.
