# Feature Specification: CLI YAML Configuration

**Feature Branch**: `prolific-yak`

**Created**: 2026-11-18

**Status**: Draft

**Input**: User description "Write a spec for the CLI YAML feature"

## Clarifications

### Session 2026-11-18

- Q: How should a search disable a minimum RV length inherited from `defaults.rv_length`? → A: Set `rv_length: null` on the search to clear the filter. Omit the field to inherit the shared value.

## User Scenarios & Testing

### User Story 1 - Run multiple campsite searches from one file (Priority: P1)

A camper wants to save several trips in one file and watch them from one terminal. Each trip can use its own booking provider, locations, dates, and campsite filters.

**Why this priority** — Running multiple searches from one command is the core roadmap requirement.

**Independent test** — Run the installed base CLI with a file containing three named searches across two synthetic providers. Give two searches different filters on the same provider, and have both providers return the same campground ID. Verify that all three searches run concurrently and that each result is attributed to the correct search and provider.

**Acceptance scenarios**

1. **Given** two searches with different providers, dates, and target IDs, **when** the camper runs `camply campsites --yaml-config trips.yaml`, **then** both searches begin checking immediately and each result identifies its search and provider.
2. **Given** two searches on the same provider with different weekday, stay-length, or equipment filters, **when** a provider response contains a mix of eligible and ineligible stays, **then** each search reports only the stays that satisfy its own rules.
3. **Given** one search takes longer or encounters a provider failure, **when** another search is ready to report results or begin its next cycle, **then** it proceeds on its own schedule subject to provider rate limits. The failed search reports its name and provider and retries after its normal interval.
4. **Given** checks are running or waiting between cycles, **when** the user presses Ctrl-C, **then** the invocation stops all searches and exits.
5. **Given** `defaults.rv_length` is `28`, **when** one search omits `rv_length` and another sets `rv_length: null`, **then** the first applies the 28-foot filter and the second applies no RV length filter. The second can use a provider that lacks RV length filtering.

### User Story 2 - Get alerts for the searches that matter (Priority: P2)

A camper wants push alerts for high-priority trips while keeping exploratory searches console-only. They want changes in one search to leave another search's alert history intact.

**Why this priority** — Each trip needs its own alert settings so the user receives alerts only where requested.

**Independent test** — Configure one search for Pushover, one for ntfy, and one for console only. Observe a stay appearing, remaining open, disappearing, and reopening. Repeat with single-pass invocations and separate notification state files.

**Acceptance scenarios**

1. **Given** the searches select different notification channels, **when** each finds a qualifying stay, **then** external alerts go only to the channels selected for that search and identify the search alongside the stay and booking link. The console-only search also displays its results.
2. **Given** a successfully checked stay remains open, **when** the same search runs again, **then** it suppresses a repeat alert. After a successful check confirms the stay closed, a later opening can alert again. A failed check preserves that search's previous observations.
3. **Given** a selected channel is missing required settings, **when** the CLI reads the configuration, **then** the invocation exits before any provider or notification request and identifies the affected search and missing variable. A delivery failure after startup is reported and other searches and channels continue.
4. **Given** `defaults.notifications` selects ntfy, **when** one search omits `notifications`, another sets `[pushover]`, and a third sets `[]`, **then** the searches use ntfy, Pushover, and console-only monitoring respectively.

### User Story 3 - Run a batch once from a script (Priority: P2)

A camper wants to schedule a single round of checks and distinguish an empty result from a failed search.

**Why this priority** — Reliable exit status and attributable results let scripts act on the whole batch.

**Independent test** — Run `camply campsites --yaml-config trips.yaml --search-once --json` with one search that finds a stay, one that completes without matches, and one whose provider fails.

**Acceptance scenarios**

1. **Given** a valid config and `--search-once`, **when** the command runs, **then** it attempts one cycle per search and waits for all attempts to finish. It exits successfully if all searches complete, including searches with zero matches.
2. **Given** a provider search fails after the provider's normal retries, **when** a single-pass batch completes, **then** the command exits nonzero and preserves successful results. JSON contains an entry for every search in file order, with failed searches distinguishable from successful empty searches.
3. **Given** any search has an invalid local setting or an incompatible flag is supplied, **when** the command starts, **then** it exits nonzero with an actionable diagnostic on stderr before starting any search. JSON mode leaves stdout empty for these startup errors.

### Edge Cases

- Reject unreadable files, empty files, additional YAML documents, missing or empty search lists, unknown or repeated keys, invalid value types, and duplicate search names. Point to the applicable file location or field.
- Preserve provider-scoped IDs as written, including leading zeros in quoted IDs and punctuation in opaque IDs. Equal IDs from different providers belong to different targets.
- A valid recreation area with zero eligible campgrounds yields a successful empty result. An error resolving a target is a failed check.
- Validate all searches before polling, even when the invalid setting belongs to the last search in the file.
- If two searches match the same opening, each reports it under its own name and applies its own notification history.
- A local notification state file that cannot be read or written produces a warning. The search continues with in-memory history for that invocation.

## Requirements

### Functional Requirements

- **FR-001** — Accept an explicit local file through `camply campsites --yaml-config PATH`. File mode works with the base CLI and requires no application account, server, or database. Invocation without a file retains the current single-provider flags, defaults, output, and exit behavior.
- **FR-002** — Require a single YAML document containing a non-empty `searches` list. Each entry must have a unique, non-blank `name` and an explicit `provider` recognized by `camply providers`. Each entry supplies its own targets, windows, filters, polling interval, and notification selection according to the configuration fields below.
- **FR-003** — Reject explicit search-definition and per-search settings passed as command-line flags in file mode, including `--provider` at either command level, targets, dates, filters, interval, notification channels, and state file. Allow `--search-once`, `--json` with `--search-once`, and debug switches to control the whole invocation. Provider selection in file mode comes from each entry.
- **FR-004** — Apply the current flag-based availability rules to each search. Require a parent campground or recreation area, give explicit campgrounds precedence with a warning when both are supplied, and match exact campsite IDs or case-insensitive names within the selected parents. Interpret date windows as inclusive check-in and exclusive checkout, apply weekday selections to occupied nights, and match the exact number of consecutive nights. Reject date and weekday combinations that cannot fit the requested stay and filters unsupported by the selected provider. A stay must satisfy every active filter.
- **FR-005** — Validate the entire file and invocation before any provider or notification request or state-file write. Report errors on stderr with the file location or named search and field as applicable, and return a nonzero status. Keep credentials and raw configuration values out of diagnostics, including in debug mode.
- **FR-006** — Start searches concurrently. By default, each checks immediately and continues at its own interval after each completed attempt until cancelled. Respect existing provider request limits, avoid overlapping cycles for the same search, report provider failures under the affected search, and let other searches continue. A failed continuous check is eligible to retry at the search's next interval. Cancel active and waiting searches together on interruption.
- **FR-007** — Identify the search and provider in terminal stay results and search-specific errors. In JSON single-pass mode, write one array to stdout with one entry per search in configuration order. Each entry contains `name`, canonical `provider`, `status` (`ok` or `error`), and `stays` using the existing JSON stay fields. A failed search uses `status: error` with an empty `stays` array and explanatory diagnostics on stderr. All progress and diagnostics go to stderr in JSON mode.
- **FR-008** — In single-pass mode, attempt one cycle for every search, including normal provider retries. Preserve and report successful results if another search fails. Exit zero when all searches complete successfully and nonzero when any search fails. Notification delivery and state-file warnings follow the current CLI behavior and do not change availability exit status.
- **FR-009** — Allow each search to select Pushover, ntfy, both, or console-only monitoring. Read channel credentials and destination settings from the existing environment variables for selected channels only. Include the search name in alerts, preserve existing booking details, and keep notification failures local to the failed delivery.
- **FR-010** — Maintain separate alert histories per search. Suppress unchanged openings until a successful check confirms they closed. A failed check leaves history intact. Support optional local state files for repeat invocations, with relative paths resolved from the config file's directory. Reject two entries that resolve to the same state path and reject a state path that resolves to the config itself.
- **FR-011** — Document `--yaml-config`, a working two-provider example with shared defaults and a per-search override, accepted fields and defaults, how to use the JSON Schema with a YAML editor, single-pass JSON behavior, and how to translate a legacy single-search configuration. Recognize the legacy flat shape for an actionable migration error.
- **FR-012** — Decode YAML as data and validate the resulting document with Pydantic models. Reject duplicate mapping keys during YAML decoding. Pydantic must forbid unknown fields and reject type coercion that would accept mistyped inputs, including numeric IDs, numeric strings for integer settings, and strings for booleans. Preserve field paths in sanitized error messages.
- **FR-013** — Accept an optional top-level `defaults` mapping for reusable search settings. Resolve each setting from the search's explicit value, then the shared default, then the built-in default. Explicit lists replace inherited lists in full, including `[]`, and explicit `false` overrides inherited `true`. A search can set `rv_length: null` to clear the RV length filter. This is the only field and placement that accepts `null`. Validate the defaults block even when all searches override it, then apply provider, date, and credential checks to each search's effective settings. Report invalid shared values under `defaults.<field>` and invalid combinations under the affected search.

### JSON Schema

The Draft 2020-12 schema in `contracts/cli-yaml-config.schema.json` describes the input accepted by the Pydantic models. Keep the schema and models aligned on field names, required fields, types, defaults, and structural constraints. Verify valid and invalid fixtures against both. The CLI also validates rules that depend on multiple fields or the runtime environment, such as unique search names, date ordering, provider capabilities, notification settings, and state-file conflicts.

### Configuration Fields

All list fields take YAML sequences. Location IDs and campsite selectors are strings. Quote numeric-looking IDs to preserve their exact spelling.

`defaults` accepts `notifications`, `interval`, `days`, `weekends`, `nights`, `campsite_types`, `electric`, `accessible`, and `rv_length`. Names, providers, targets, date windows, and state files are set on individual searches. An empty `defaults` mapping is equivalent to omitting it.

In `defaults`, `rv_length` accepts a whole number from 1 to 200. In a search, `rv_length` accepts the same range or `null` to clear an inherited length.

| Field                                                   | Values and defaults                                                                                                                                                                                                     |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`, `provider`                                      | Required strings. Names must be unique. Providers use the current CLI names or aliases.                                                                                                                                 |
| `campgrounds`, `recreation_areas`                       | Lists of provider-specific IDs. At least one populated list is required.                                                                                                                                                |
| `campsites`                                             | Optional list of campsite IDs or names within the selected parent targets.                                                                                                                                              |
| `date_windows`                                          | Required non-empty list of `start_date` and `end_date` pairs in `YYYY-MM-DD` form.                                                                                                                                      |
| `days`, `weekends`, `nights`                            | Optional weekday names or abbreviations, weekend boolean, and positive exact stay length. Defaults allow all days and require one night. `weekends: true` adds Friday and Saturday to any explicitly selected weekdays. |
| `campsite_types`, `electric`, `accessible`, `rv_length` | Optional list of `TENT`, `RV`, `CABIN`, or `OTHER`, electric and accessibility booleans, and minimum compatible RV or trailer length in whole feet (1–200). Defaults apply no equipment or site-type restrictions.      |
| `interval`                                              | Whole minutes between checks. Default 10, minimum 5.                                                                                                                                                                    |
| `notifications`, `state_file`                           | Optional list of `pushover` and/or `ntfy` and an optional path for alert history. Defaults are console only and in-memory history.                                                                                      |

This example uses illustrative campground IDs. Each ID comes from discovery for the corresponding provider.

```yaml
defaults:
  notifications: [ntfy]
  interval: 10
searches:
  - name: yosemite-weekends
    provider: RecreationDotGov
    campgrounds: ["232450"]
    date_windows:
      - start_date: "2027-07-01"
        end_date: "2027-07-31"
    weekends: true
    nights: 2
  - name: california-coast
    provider: ReserveCalifornia
    campgrounds: ["1234"]
    date_windows:
      - start_date: "2027-08-06"
        end_date: "2027-08-09"
    interval: 15
    notifications: []
```

### Key Entities

- **Configuration file** — A collection of named campsite searches run in one foreground invocation.
- **Search** — One name, provider, set of targets, date windows, filters, polling interval, and alert preferences.
- **Search outcome** — A named search's qualifying stays or check failure.
- **Alert history** — Previously observed openings for one search, optionally retained in a local state file.

## Success Criteria

### Measurable Outcomes

- **SC-001** — With three configured searches across two providers, one command starts all three in the first cycle. A deliberately stalled provider does not delay the other provider's first result or next eligible check.
- **SC-002** — For equivalent single-search inputs on synthetic availability data, file mode returns the same qualifying stays and booking links as flag mode. Multi-search tests return every match under the correct search and provider, including when provider-scoped IDs collide.
- **SC-003** — Every invalid startup case in the acceptance matrix, including an invalid last search, produces a nonzero status, an actionable diagnostic, and zero external requests or state-file writes.
- **SC-004** — For each selected channel and search, the sequence open, unchanged, failed check, closed, reopened yields two alerts, one for each opening. Console-only searches produce zero external alerts. The same outcomes hold across single-pass runs using separate state files.
- **SC-005** — A mixed-result single-pass batch reports one result entry per configured search, retains successful stays, distinguishes failures from empty results, and returns a nonzero status. An all-success batch returns zero.

## Assumptions

- The [roadmap item](../../PLAN.md) and the [full-stack parity specification](../031-cli-fullstack-parity/spec.md) define the feature scope and current CLI baseline.
- The draft uses a new multi-search format with explicit provider names and invocation-wide run controls. Scope includes guidance for migrating the [legacy flat format](../026-cli-parity/legacy-audit.md#yaml-contract). Automatic discovery, legacy file import, and environment-variable interpolation are outside this release.
- Notification settings are shared through the process environment. A search selects channels rather than separate credentials or destinations. Server-managed scans, cross-process coordination of alert state, and new provider or notification integrations are outside this release.
