# Feature Specification: Legacy CLI parity

**Feature**: `026-cli-parity`
**Created**: 2026-11-08
**Status**: Draft — specification and source audit only; CLI parity is not implemented
**Input**: Give users of `juftin/camply` the CLI experience they know while using the current architecture and capabilities.

## Goal and compatibility baseline

Users can discover locations, search availability, watch for cancellations, and receive alerts using familiar Camply commands without running a web server or provisioning infrastructure. The same provider and matching capabilities serve CLI and web workflows.

The baseline is legacy [v0.34.4](https://github.com/juftin/camply/releases/tag/v0.34.4), audited on 2026-11-08. “Camply v1” identifies the legacy generation, not a literal upstream major-version tag. The [legacy audit](legacy-audit.md) is the exhaustive surface inventory: C01–C12 commands/global behavior, S01–S16 search options, every YAML key, all 19 provider names, 17 GoingToCamp deployment selectors and 10 notification channels. Its replacement column distinguishes current foundations from missing work. The [plan](plan.md) records architectural implications; [tasks](tasks.md) records pending delivery slices.

## Initial scope and deferred work

The initial delivery focuses on provider listing, recreation-area/campground discovery, and campground-based availability using currently registered camping providers. Reuse current provider, matching and Pushover capabilities where needed. Preserve existing `serve`, serving roles/health checks and `db` commands. Use ordinary Click and readable plain terminal output.

The legacy audit is a reference inventory, not an instruction to implement every feature. The following are **TODO — deferred, do not implement in this delivery**. Their presence in the audit, future requirements or backlog does not make them prerequisites for the initial CLI release.

| TODO | Deferred feature                                             | Tracking and boundary                                                                                                                                                                                        |
| ---- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D01  | `list-campsites`                                             | C07; defer the command and public site-catalog work solely needed for it.                                                                                                                                    |
| D02  | Search by campsite ID                                        | S01/C06; defer `--campsite`, site-to-parent resolution and site-selection compatibility. Campground/area selection remains in scope.                                                                         |
| D03  | Full notification provider parity                            | C11/S11; defer additional legacy channels, multi-channel compatibility and their test-notification contracts. Existing Pushover capability can be reused without restoring every old channel.                |
| D04  | Full campground parity                                       | Legacy provider/deployment coverage; defer missing campground providers/catalogs, Yellowstone, Alabama/Maricopa and the broader GoingToCamp deployment facade. Use currently registered providers initially. |
| D05  | YAML files                                                   | S15; defer both file aliases, schema/import, environment expansion and legacy file precedence.                                                                                                               |
| D06  | Permits                                                      | Track future permit support and related non-camping inventory design. Legacy ticket/tour/timed-entry variants are also deferred here; the audit does not establish general legacy permit support.            |
| D07  | Equipment filtering                                          | C08/S13–S14; defer equipment lookup, categories, lengths, slot/quantity overloads and new provider capabilities solely needed for those workflows.                                                           |
| D08  | TUI                                                          | C12; defer optional extra, command preview and terminal forms.                                                                                                                                               |
| D09  | Rich-click                                                   | C01/C03 presentation; defer Rich-formatted command/help integration. Keep existing Click.                                                                                                                    |
| D10  | `configure` command                                          | C10; defer the wizard and legacy `.camply` import/write compatibility. Existing environment configuration remains available.                                                                                 |
| D11  | `--continuous` / `--search-forever` / `--search-once` design | S06–S10; **intended default: search forever**. Brainstorm modes, flags, stopping behavior and cron use later. Do not implement the legacy mode matrix or preserve its one-pass default as a requirement.     |
| D12  | `--notify-first-try`                                         | S12; defer the flag and compatibility with legacy first-batch/general notification caps.                                                                                                                     |
| D13  | `--offline-search`                                           | S16; defer this flag, `--offline-search-path`, JSON/pickle migration, persistent history and cross-process duplicate suppression.                                                                            |

D11 records a product direction, not a finished run-mode contract. Record search-forever as the default direction for the availability command without restoring the three legacy switches. Brainstorm flag names, implicit mode triggers, interval defaults, lifetime alert suppression and cron behavior later; these open details do not pull the deferred legacy mode matrix into initial scope. D12 and D13 are explicitly deferred, as confirmed by the user.

Release notes must distinguish supported initial behavior from these TODOs. Full legacy parity remains a long-term reference, not the release gate for this feature. Missing deferred providers/channels must not be advertised as supported or silently mapped to another provider.

## Representative initial workflows

These are proposed syntax examples, not commands implemented by this change. IDs come from discovery. The availability invocation follows the intended search-forever default; detailed run-mode design remains TODO D11.

```bash
camply providers
camply recreation-areas --search Yosemite --state CA
camply campgrounds --rec-area 2991
camply campsites --campground 232450 --start-date 2027-07-10 --end-date 2027-07-18 --nights 3
```

Examples using YAML, individual campsite IDs, legacy run-mode flags, equipment, additional channels or persistent history belong to the deferred reference inventory, not initial setup guidance.

## User Scenarios & Testing

### User Story 1 — Discover locations on current providers (P1)

A CLI user discovers recreation areas and campgrounds and obtains usable provider-native IDs without opening the web app.

**Why**: This restores a useful CLI workflow using existing direct provider search.

**Independent test**: From an installed base wheel outside the checkout, use synthetic upstreams with no database, server extra or populated catalog.

1. **Given** Recreation.gov results, **when** `camply recreation-areas --search Yosemite --state CA` runs, **then** names and usable provider-native IDs appear.
2. **Given** a recreation-area ID, **when** campground discovery runs, **then** results preserve native provider/parent identities and booking links.
3. **Given** an unknown or unavailable provider, **when** selected, **then** an actionable error occurs before availability requests or file writes; no other provider is substituted.
4. **Given** root help/version/provider listing, **when** invoked, **then** no network, database initialization or optional runtime dependency is needed.

### User Story 2 — Search campground availability (P1)

A user searches currently supported campgrounds or areas for qualifying stays using the familiar date/day/night selectors.

**Why**: Reuse current availability capabilities while keeping deferred parity work out of the initial delivery.

**Independent test**: Exercise a single internal availability check against scripted provider observations. Verify the intended default continues searching after a matching check; detailed legacy flag/cron contracts wait for D11. An internal check does not imply a public one-pass mode.

1. **Given** paired search windows, **when** an availability check runs, **then** only nights inside the checkout-exclusive windows are considered, with no duplicate stays from overlap.
2. **Given** area/campground selectors, **when** targets resolve, **then** duplicate targets make only one logical availability check per cycle; individual campsite selection is deferred.
3. **Given** `--weekends --day Sunday`, **when** matching runs, **then** Friday, Saturday and Sunday are eligible; stays do not bridge gaps or combine sites.
4. **Given** a four-night run and `--nights 3`, **when** stays are presented, **then** two sliding three-night stays appear. An impossible stay length is rejected rather than downgraded.
5. **Given** provider timeout/429/schema failure, **when** checking, **then** failure is distinguished from a successful empty result and shared retry/pacing behavior applies.

### Deferred user journeys

D01–D13 retain the legacy inventory's workflows for future design. YAML migration, notification setup/testing/parity, equipment, permits, TUI, persistent cron history and the legacy mode matrix have no initial acceptance gate. Add their implementation scenarios when the corresponding TODO is brought into scope. Revisit detailed mode tests after D11 brainstorming; retain search-forever as the intended default.

### Initial edge cases

- Unequal/missing date pairs; reversed/equal endpoints; leap days; month/year crossings; past start; expired end; overlapping windows and UTC rollover.
- Nonadjacent allowed nights cannot form a consecutive stay; stays cannot combine different site identities.
- Preserve opaque provider-scoped IDs without integer coercion, including current ReserveAmerica contract-scoped IDs. Equal IDs from different providers/entity types remain distinct.
- Empty or enormous area expansion; disabled/unbookable catalog entries; explicit discovery truncation and complete availability target enumeration.
- Unsupported/deferred inputs fail clearly if supplied; do not accept them and silently ignore constraints.
- Provider failure versus empty availability; partial target success; cancellation and owned-client cleanup. Exact command termination behavior awaits D11.

## Requirements

### Functional requirements

Requirement IDs are retained for traceability. **Deferred** entries are TODO references, not implementation requirements or initial release gates.

- **FR-001 — Initial**: Restore provider listing, recreation-area/campground discovery and campground-based availability through lazy Click commands with provider/debug selection. Preserve serving/database commands and base-only help/version behavior. C07/C08/C10/C12 and Rich-click are deferred under D01/D07–D10.
- **FR-002 — Initial, limited coverage**: Resolve currently supported providers case-insensitively through canonical identities and compatible aliases. Preserve command provider → root provider → environment → default precedence. Defer missing legacy providers and GoingToCamp deployment translation to D04; never misinterpret a legacy deployment selector as a native park ID.
- **FR-003 — Initial, limited capabilities**: Provide database-independent recreation-area/campground discovery and campground/area target resolution. Complete target expansion must paginate/batch beyond feature 025's per-call limit, deduplicate provider-qualified targets and expose errors/truncation. Site-ID lookup/catalogs and equipment capabilities are deferred under D01/D02/D07.
- **FR-004 — Initial, limited filters**: Support area/campground selection, paired exclusive windows, day/weekend union and exact-length sliding stays. Exclude expired nights consistently with the web engine. Reject impossible constraints; individual campsite and equipment restrictions are deferred under D02/D07.
- **FR-005 — Default direction; mode design TODO D11**: Intended default is search forever. Brainstorm the lifecycle and `--continuous` / `--search-forever` / `--search-once` semantics later. Do not require legacy one-pass defaults or implicit flag triggers.
- **FR-006 — Initial foundation; scheduling pending D11**: Use shared async retry/rate-limit clients; avoid overlapping a target's requests and distinguish failures from empty availability. CLI interval defaults, minimums and polling schedule remain open for D11 design.
- **FR-007 — TODO D11/D12/D13**: Lifetime notification suppression, first-batch/general caps and persisted per-channel outcomes are deferred. Legacy 5/20 limits are historical evidence, not selected initial policy. Reuse existing notification behavior without promising those compatibility semantics.
- **FR-008 — TODO D13**: Defer offline flags, JSON history/import, cross-process duplicate suppression, locking and pickle migration. Initial commands do not write a CLI history file.
- **FR-009 — TODO D05**: Defer YAML aliases, schema/default compatibility, interpolation, precedence and repairs.
- **FR-010 — TODO D10**: Defer `configure` and legacy `.camply` handling. Initial notification reuse uses current environment settings; legacy credential migration and wizard behavior need later design.
- **FR-011 — Initial reuse; parity TODO D03**: Existing Pushover capability may be shared with local CLI execution; console output and provider booking links remain useful without a web account/server. Full legacy channel support, fan-out and payload parity are deferred. Do not advertise absent channels as supported.
- **FR-012 — TODO D03**: Defer full legacy `test-notifications` and multi-channel diagnostic/failure contracts. Any initial delivery integration must expose actual failures using existing capability semantics.
- **FR-013 — TODO D04/D06**: Defer missing campground/provider/deployment coverage, permits and legacy ticket/tour/timed-entry inventory. Preserve the audit as a future mapping reference; no new inventory adapters are required initially.
- **FR-014 — TODO D08/D09**: Defer optional TUI and Rich-click. Ordinary Click help/output is sufficient for the initial CLI.
- **FR-015 — Initial**: Show provider/parent/site names and IDs, qualifying dates, stay counts and provider booking links when available; never invent missing data. Use deterministic readable output and sanitized debug/plain logging. Rich presentation and equipment output are deferred.
- **FR-016 — Initial foundation; lifecycle pending D11**: Validate inputs, expose provider/delivery failures, and close owned clients/tasks on cancellation. Final command exit/status, expiration, retry exhaustion and stop-after-match/cron semantics must be designed with D11 rather than copied from legacy behavior.
- **FR-017 — Initial**: Local commands run from a base `camply-web` wheel without server/distributed/postgres/sentry extras, accounts, metadata import, frontend process or external database/broker. Bound requests/queues; create no application database or persistent CLI history by default.
- **FR-018 — Initial**: Reuse current async providers, typed validation, matching and existing notification capabilities; do not vendor/invoke the legacy CLI. Preserve Import Linter boundaries through explicit shared-code design and regression checks, and protect standalone/distributed behavior. Avoid abstractions needed solely by deferred features.

### Key entities in initial scope

- **Search request**: Current provider, ordered date windows, area/campground selectors and day/stay restrictions. Command lifecycle will be added after D11.
- **Resolved target**: Provider-qualified campground with required native parent context, independent of web subscriptions.
- **Availability stay**: Provider/site identity, arrival/checkout, attributes and booking URL derived from successful live observations. Observed site identity is needed to construct stays; accepting campsite-ID search input is deferred.
- **Capability entry**: Current provider operations and explicit unsupported/unavailable reasons. Full legacy deployment compatibility is deferred.

Persistent history, YAML models, equipment/permit/slot models and additional channel settings are future entities, not initial schema work.

## Success criteria

- **SC-001**: Every legacy inventory entry has a documented initial/deferred disposition. Initial supported behavior has contract fixtures; D01–D13 need no implementation fixture to ship this scope.
- **SC-002**: Fresh installed-base tests complete discovery and internal availability checks without services/account/catalog. Help/version/provider listing perform zero network calls and create zero state files. Verify search-forever as the intended default without requiring legacy mode switches; detailed mode acceptance follows D11.
- **SC-003**: Scripted availability checks verify target deduplication, date/weekday matching, exact-length stays and provider retry/pacing. Legacy run-mode, notification cap, restart/history tests are deferred.
- **SC-004**: Identical observations yield equivalent eligible nights across CLI/web matching, with exact-length CLI stay presentation tested separately. Duplicate windows/targets cause no duplicate logical checks per cycle.
- **SC-005**: Invalid/unsupported inputs fail clearly before availability IO; cancellation closes owned resources. Persistent-state recovery and precise lifecycle timing gates await D13/D11.
- **SC-006**: Python 3.11/default 3.14 installed-artifact checks, provider HTTP contracts, Import Linter and relevant serve/db/web/worker regressions pass. Apply project quality gates to initial implementation; do not require deferred providers, extras or inventory to pass this gate.

## Assumptions and boundaries

- This is a specification change, with no runtime behavior or migration implemented. The legacy audit remains intact while D01–D13 defer implementation. Later work must explicitly bring a TODO into scope before designing or implementing it.
- The legacy name/release distinction and current package publication remain explicit. Users install `camply-web` to obtain the `camply` executable; parallel installation with legacy `camply` conflicts and requires an isolated environment or deliberate replacement. Legacy PyPI/image ownership and major-version cutover are separate release decisions.
- Local foreground execution is the parity target. Remote hosted CLI authentication, saved web-scan administration, shell completion and machine-readable output are potential future features, not prerequisites.
- No auto-booking, reservation guarantees, exact terminal formatting or public legacy Python API parity. Network access to upstream booking and selected notification services remains necessary.
