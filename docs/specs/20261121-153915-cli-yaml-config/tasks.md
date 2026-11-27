---
description: "Implementation checklist for CLI YAML Configuration"
---

# Tasks for CLI YAML Configuration

**Inputs** — [Specification](spec.md), [plan](plan.md), [research](research.md), [data model](data-model.md), [CLI contract](contracts/cli.md), and [validation guide](quickstart.md).

**Tests** — Write the acceptance, contract, and regression cases before the implementation they cover. Use synthetic providers and notification responses.

**Format** — `[P]` identifies tasks that can run alongside the indicated peer after their prerequisites. Story tags map to the specification. All file paths are repository-relative.

## Phase 1 — Setup

- [x] T001 Declare PyYAML as a base dependency and a Draft 2020-12 JSON Schema validator as a development dependency in `pyproject.toml`. Refresh `uv.lock` and verify resolution on Python 3.11 and 3.14.

## Phase 2 — Foundation

- [x] T002 [P] Add loader, input-model, and shared schema fixtures in `tests/cli/test_yaml_config.py` against `docs/cli-yaml-config.schema.json`. Cover one document, duplicate keys, plain and quoted ISO dates, strict scalar types, opaque IDs, forbidden extras, redacted diagnostics, legacy flat input, and defaults including explicit empty lists, false, and search-only RV length null. Exercise JSON Schema and Pydantic on the same structural cases and test YAML-only errors separately.
- [x] T003 [P] Add a pure canonical provider lookup to `src/camply/cli/providers.py` for aliases and provider IDs without instantiating clients or consulting the environment. Reuse it from the existing flag resolver while preserving flag precedence and messages.
- [x] T004 Implement the isolated safe loader and strict Pydantic input models in `src/camply/cli/yaml_config.py`. Enforce an “ordered, non-empty list of named searches and an optional mapping of shared settings,” a “Unique non-blank name, explicit provider,” and “At least one target list and one window are populated.” Use strict strings for IDs and selectors, one inclusive `start_date` and exclusive `end_date` in ISO calendar format, positive exact nights, interval of at least five whole minutes, documented campsite types, and Pushover/ntfy channel choices. Preserve field presence for “explicit search value, shared setting, then built-in default.” Shared RV length is an “integer from 1 to 200.” An explicit null for search `rv_length` clears the filter. All other explicit nulls are invalid. Report known field paths or line and column without raw inputs and provide migration guidance for legacy flat YAML.

**Checkpoint** — Local syntax and schema validation work without starting searches.

## Phase 3 — User Story 1 — Run multiple campsite searches from one file (P1)

**Goal** — Run independent foreground watches across providers from a single config.

**Independent test** — Run the installed base CLI with three named searches across two synthetic providers, including same-provider aliases with different filters and equal IDs across providers. Check filter parity, pacing, progress while another provider stalls, and cancellation.

- [x] T005 [P] [US1] Specify CLI preflight and flag-mode regression cases in `tests/cli/test_campsite_batch.py` and `tests/cli/test_search.py`. Cover root or command flag conflicts, invalid final search, no external calls or state writes, campground precedence, occupied weekdays, unsupported inherited filters, explicit RV length clearing, and existing flag-mode behavior.
- [x] T006 [P] [US1] Add controlled async scheduling tests in `tests/cli/test_campsite_batch_scheduling.py` for independent intervals, shared provider clients for aliases, same-provider filter isolation, cross-provider stalls, target-resolution recovery, successful empty areas, and cleanup of active and waiting searches on cancellation.
- [x] T007 [US1] Prepare effective searches in `src/camply/cli/yaml_config.py` using provider lookup and the normalizer in `src/camply/core/search.py`. Enforce “End follows start” and “The effective windows and weekday selection must accommodate the requested stay length.” Reuse capability checks on resolved filters, require a parent, warn when explicit campgrounds win, and normalize campsite selectors. Construct all prepared searches before network work.
- [x] T008 [US1] Implement batch execution in `src/camply/cli/campsite_batch.py` with one provider client per canonical ID, one coroutine per search, and the existing target resolver and availability check. Cache successful target resolution, retry failed attempts after that search's wait, and reuse provider pacing. Support a one-attempt path for single-pass mode. Drain tasks before closing clients and preserve cancellation from `src/camply/cli/execution.py`.
- [x] T009 [US1] Wire `--yaml-config` into `src/camply/cli/campsites.py`, enforce conditional flag requirements with Click parameter sources, route to the batch after successful preparation, and preserve flag-only help and error behavior. Configure logging once and label terminal stays and sanitized errors with search name and canonical provider in `src/camply/cli/output.py`.
- [x] T010 [US1] Extend `tests/packaging/test_cli_search.py` to prove multi-provider file execution from outside the checkout in a base-only wheel, including result attribution, opaque ID collisions, and cleanup. Use synthetic HTTP responses.

**Checkpoint** — The installed base CLI runs multiple console watches and isolates provider failures.

## Phase 4 — User Story 2 — Get alerts for the searches that matter (P2)

**Goal** — Apply notification selection and observation history per search.

**Independent test** — Inherit ntfy, override with Pushover, and clear notifications on a third search. Observe open, unchanged, failed check, closed, and reopened across cycles and repeat single-pass runs.

- [x] T011 [P] [US2] Add notification tests in `tests/cli/test_campsite_batch_notifications.py` for channel inheritance, missing credentials, no credential reads for console-only searches, attributed deliveries with booking links, and isolated delivery failures. Under synthetic conditions check delivery within the constitution's 60-second objective.
- [x] T012 [P] [US2] Add observation and persistence tests in `tests/cli/test_campsite_batch_state.py` for failed cycles, reopened stays, separate config-relative state paths across runs, canonical path collisions, config self-reference, and unreadable or unwritable state.
- [x] T013 [US2] Extend preparation in `src/camply/cli/yaml_config.py` to resolve environment settings for effective channels and validate state paths before client startup. Enforce “State paths belong to individual searches and may not resolve to the configuration file or another search's state path.”
- [x] T014 [US2] Reuse `src/camply/cli/notifications.py` from `src/camply/cli/campsite_batch.py` with one observation history per search. Preserve the existing state format and stay identity fields. Record complete successful checks, preserve history on failed attempts, and attribute alerts and warnings without exposing credentials or state paths.
- [x] T015 [US2] Extend `tests/packaging/test_cli_search.py` with repeat file invocations against synthetic upstream and notification endpoints to verify per-search state persistence and suppressed duplicate alerts.

**Checkpoint** — Selected searches deliver attributed alerts. Provider and delivery errors preserve independent operation.

## Phase 5 — User Story 3 — Run a batch once from a script (P2)

**Goal** — Emit one ordered JSON response and an aggregate status for a single-pass batch.

**Independent test** — Run `--search-once --json` with one match, one successful empty search, and one provider failure completing out of order. Verify one result per search in file order, successful stays retained, stderr diagnostics, and exit 1. Also verify status 0 when all succeed and status 2 with empty stdout for a startup error.

- [x] T016 [P] [US3] Add `tests/cli/test_campsite_batch_json.py` for the contract in `docs/specs/20261121-153915-cli-yaml-config/contracts/cli.md`. Cover file ordering, exactly one attempt per search apart from provider retries, mixed and all-success statuses, empty versus failed results, JSON without `--search-once`, and stdout remaining empty on invalid preflight.
- [x] T017 [P] [US3] Extract reusable stay serialization from `src/camply/cli/output.py` while keeping the existing flag-mode JSON array and fields. Add file-mode rendering of one array with `name`, canonical `provider`, `status`, and `stays` per search. An `ok` outcome may have no stays. An `error` outcome has no stays and a corresponding sanitized diagnostic.
- [x] T018 [US3] Collect single-pass outcomes in order in `src/camply/cli/campsite_batch.py` and finalize streams and status codes in `src/camply/cli/campsites.py`. Wait for all attempts, preserve successes, send all diagnostics to stderr in JSON mode, and keep the exit status independent of notification and state warnings.
- [x] T019 [US3] Extend `tests/packaging/test_cli_search.py` to verify one valid JSON document, both outcome statuses, and process exit behavior using the installed console script.

**Checkpoint** — Scripts can distinguish an empty search from a failed search while retaining successful results.

## Phase 6 — Documentation and verification

- [x] T020 [P] Document file mode, a working two-provider example, inheritance and overrides, editor association with the checked-in schema, single-pass output, and flat-format migration in `docs/cli.md`. Reconcile commands and results in `docs/specs/20261121-153915-cli-yaml-config/quickstart.md`.
- [x] T021 Run the validation guide in `docs/specs/20261121-153915-cli-yaml-config/quickstart.md` with the root `Taskfile.yaml`, covering CLI, core search, installed artifacts, imports, lint, types, and docs. Verify Python 3.11 compatibility and Python 3.14 defaults.
- [x] T022 Record completed work in `docs/CHECKLIST.md` and update the CLI YAML roadmap item in `docs/PLAN.md` after acceptance passes.

## Dependencies and execution order

```text
Setup → Foundation → US1 → US2 → US3 integration → Documentation and verification
                        └──────→ US3 contract tests and serializer
```

Foundation tasks T002 and T003 can overlap after T001. T004 follows T002. Start story implementation after foundation validation passes. For US1, complete T005 and T006 before T007–T009, then verify the installed command in T010. For US2, write T011 and T012 before T013–T014, then run T015. For US3, write T016 before T017–T018. T018 integrates after T014 so it preserves notification and persistence semantics. After T018, the packaging check (T019) and documentation work (T020) can overlap. T019 also follows the earlier edits to the same packaging test file. T021 follows the story checkpoints and T020. T022 follows T021.

## Parallel execution examples

| Story | Parallel work once prerequisites are met                                                                                                              |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| US1   | Write CLI contract and regression tests (T005) alongside the scheduling tests (T006).                                                                 |
| US2   | Write delivery tests (T011) alongside persistence tests (T012).                                                                                       |
| US3   | Write batch JSON contract tests (T016) while US2 implementation proceeds. After T016, T017 can overlap T013–T014 because they edit different modules. |

## Implementation strategy

Deliver US1 first as the MVP and verify it with the synthetic installed-wheel run. Add alerts and persistent history in US2, then finish the batch output contract in US3. Verify each increment at its checkpoint and run the full acceptance guide before updating the roadmap.
