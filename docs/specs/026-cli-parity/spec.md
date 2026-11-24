# Feature Specification: Legacy CLI parity

**Feature**: `026-cli-parity`
**Created**: 2026-11-08
**Status**: Initial implementation — current-provider discovery and console-only campground monitoring; D01–D13 remain deferred
**Input**: Give users of `juftin/camply` the CLI experience they know while using the current architecture and capabilities.

## Goal and compatibility baseline

Users can discover locations, search availability and watch for cancellations in their terminal using familiar Camply commands without running a web server or provisioning infrastructure. Initial CLI results are console-only; external alerts, including Pushover, are deferred. The same provider and matching capabilities serve CLI and web workflows.

The baseline is legacy [v0.34.4](https://github.com/juftin/camply/releases/tag/v0.34.4), audited on 2026-11-08. “Camply v1” identifies the legacy generation, not a literal upstream major-version tag. The [legacy audit](legacy-audit.md) is the exhaustive surface inventory: C01–C12 commands/global behavior, S01–S16 search options, every YAML key, all 19 provider names, 17 GoingToCamp deployment selectors and 10 notification channels. Its replacement column distinguishes current foundations from missing work. The [plan](plan.md) records architectural implications; [tasks](tasks.md) records pending delivery slices.

## Initial scope and deferred work

The initial delivery focuses on provider listing, recreation-area/campground discovery, and campground-based availability using currently registered camping providers. Reuse current provider and matching capabilities. Initial output is console-only: do not implement Pushover, external notification selection or CLI notification credentials. Preserve existing `serve`, serving roles/health checks and `db` commands. Use ordinary Click and readable plain terminal output.

The legacy audit is a reference inventory, not an instruction to implement every feature. The following are **TODO — deferred, do not implement in this delivery**. Their presence in the audit, future requirements or backlog does not make them prerequisites for the initial CLI release.

| TODO | Deferred feature                                             | Tracking and boundary                                                                                                                                                                                        |
| ---- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D01  | `list-campsites`                                             | C07; defer the command and public site-catalog work solely needed for it.                                                                                                                                    |
| D02  | Search by campsite ID                                        | S01/C06; defer `--campsite`, site-to-parent resolution and site-selection compatibility. Campground/area selection remains in scope.                                                                         |
| D03  | Full notification provider parity                            | C11/S11; defer all CLI external channels, including Pushover, notification selection/credentials and test-notifications. Initial output is console-only; existing web notification behavior stays unchanged. |
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

The initial default is settled: start checking immediately and continue after matches until cancellation, without the three legacy switches. D11 retains the detailed run-mode design for later brainstorming. Brainstorm flag names, implicit mode triggers, interval defaults, lifetime alert suppression and cron behavior later; these open details do not pull the deferred legacy mode matrix into initial scope. D12 and D13 are explicitly deferred, as confirmed by the user.

Release notes must distinguish supported initial behavior from these TODOs. Full legacy parity remains a long-term reference, not the release gate for this feature. Missing deferred providers/channels must not be advertised as supported or silently mapped to another provider.

## Initial command contract

This section defines the public command surface. Deferred switches/commands are rejected by normal Click parsing; they are not accepted as no-ops. Existing serving/database options keep their current behavior.

```text
camply [--provider PROVIDER] [--debug | --no-debug] [--help] [--version]
├── providers
├── recreation-areas [--search TEXT] [--state CODE]
├── campgrounds [--search TEXT] [--state CODE] [--rec-area ID]... [--campground ID]...
├── campsites [--rec-area ID]... [--campground ID]...
│             --start-date YYYY-MM-DD ... --end-date YYYY-MM-DD ...
│             [--day DAY]... [--weekends] [--nights N]
├── serve                       (existing standalone launcher and options)
│   ├── frontend
│   ├── backend
│   ├── worker
│   ├── beat
│   └── healthcheck
└── db                          (existing commands and options)
    ├── info
    ├── migrate
    ├── delete
    └── metadata
```

`providers` accepts `--debug/--no-debug`. `recreation-areas`, `campgrounds` and `campsites` accept both `--provider` and `--debug/--no-debug` after the command as well as at the root. Every command has `--help`; keep the existing root `-h` alias. No command is required for root help. New provider/debug options do not change serving/database behavior.

### Providers and option precedence

- Default provider: `RecreationDotGov`. The `CAMPLY_PROVIDER` environment variable is the fallback when neither command nor root supplies a provider. Precedence is **explicit command option → explicit root option → environment → default**, with case-insensitive matching. An invalid winning value is an error; do not fall through to another provider. An overridden environment/root provider value does not override an explicit command value.
- Initial canonical CLI names: `RecreationDotGov`, `ReserveCalifornia`, `FloridaStateParks`, `VirginiaStateParks`, `MinnesotaStateParks`, `OhioStateParks`, `ArizonaStateParks`, `MissouriStateParks`, `FairfaxCountyParks`, `OregonMetro`, `NorthernTerritory`, `WashingtonStateParks` and `ReserveAmerica`. `RecreationGovProvider` is an alias for `RecreationDotGov`; other current provider class names are aliases for their corresponding canonical CLI names. `providers` displays canonical names, readable labels and capability information from the current registry.
- `GoingToCamp` is not an alias for `WashingtonStateParks`: its historical area IDs have different meanings, and its compatibility facade is deferred. Recognized unavailable legacy names produce a diagnostic directing users to `providers`; do not map them to another inventory.
- Debug precedence is explicit command switch → explicit root switch → false, including explicit `--no-debug`. Debug never reveals credentials. Provider/debug options are single-value options; if repeated at the same position, the last wins, following Click convention. Flags not listed for a command are rejected.

### Discovery and selector behavior

| Surface            | Required inputs, repeatability and matching                                                                                                                                                                                                                                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `recreation-areas` | `--search` and `--state` are optional scalar filters. No filters browses available recreation areas. A provider without area entities returns a successful empty list with an explanation.                                                                                                                                                        |
| `campgrounds`      | Optional scalar `--search`/`--state`; repeatable `--rec-area`/`--campground`. No selectors browses campgrounds. Recreation-area IDs form a union of their child campgrounds. Explicit campground IDs take precedence over area IDs; report ignored area selectors without resolving them. Apply text/state filters to the selected candidate set. |
| `campsites`        | At least one `--rec-area` or `--campground`, plus one or more paired start/end dates. Campground IDs take precedence over area IDs; report ignored area selectors. Duplicate IDs/targets are checked once per cycle. No `--campsite` input.                                                                                                       |

IDs are exact opaque strings, scoped by provider; trim surrounding whitespace, reject blank IDs and preserve leading zeroes and compound IDs. Resolve every selected explicit ID against upstream metadata without opening a database. An unknown/disabled/nonbookable campground or invalid area produces an actionable error before availability requests; do not silently drop some IDs from a list. An existing area with no eligible campgrounds yields an explained empty result. Names/parent context and public booking URLs come from that metadata, not guesses based on ID strings.

`campgrounds --campground ID` is an exact metadata lookup, not a free-text search for that ID. It must work even if that campground is outside the first discovery page. This requires a database-independent public lookup capability alongside feature 025; campsite-ID lookup remains deferred. Text/state filters that exclude a valid explicitly resolved campground produce an empty filtered result rather than an invalid-ID error.

Trim `--search`; blank means browse. State codes must be exactly two letters and are normalized to uppercase before requests. Query relevance remains provider-defined as in feature 025; do not promise identical text matching across providers. Discovery displays up to 50 results in deterministic order and explicitly reports when more exist; completeness detection must distinguish exactly 50 from a truncated response. Availability area expansion is exhaustive and cannot reuse that display limit. Add a public enumeration/pagination capability rather than repeatedly requesting the same limited page or exceeding the validated 1–1000 search limit.

### Console-only notification boundary

The initial CLI always displays results in the terminal and sends no external notifications. No `--notifications` option or `test-notifications` command is exposed; supplying either is an unsupported-input error. Neither configuring Pushover credentials nor having an existing web account enables CLI delivery implicitly. The CLI does not read/require `PUSHOVER_APP_TOKEN`, introduce `PUSHOVER_USER_KEY`, or look up a database user. Initial CLI operation must succeed with notification credentials absent or malformed. Existing web/server Pushover delivery and environment settings remain unchanged.

This resolves the initial credential question by deferring delivery, not by inventing new CLI credential migration. Add activation, recipient settings, acceptance checks and failure policy when external notifications are explicitly brought into scope under D03.

### Dates, matching and output

- `--start-date` and `--end-date` are repeatable ISO calendar dates, required in equal nonzero counts and paired by occurrence order. Every original end must be after its start. Clamp past starts to current UTC today with a warning; reject windows with no remaining future/current booking nights before availability IO. Arrival is inclusive; checkout is exclusive. Merge overlapping eligible nights for duplicate-work suppression without creating nights in gaps.
- `--day` is repeatable and case-insensitive: full English names plus MON/TUE/TUES/WED/THU/THUR/THURS/FRI/SAT/SUN. No day/weekend options means all days. `--weekends` adds Friday/Saturday to explicitly selected days. Weekday restrictions apply to individual nights, then consecutive stays are constructed within the resulting eligible set.
- `--nights` is a positive integer, default 1. Each qualifying stay has exactly that many consecutive nights at the same site; overlapping sliding stays are allowed and deduplicated. Reject an impossible requested length based on selected windows/weekdays rather than reducing it. Do not interpret this as an equipment or party-size filter.
- Results go to stdout; diagnostics/debug logs go to stderr. Show explicit empty-result messages, provider/parent/site identity, qualifying arrival/checkout and booking URLs when available. Use deterministic ordering by provider, campground, site and arrival/checkout. No Rich-click or machine-readable format is required.
- The availability command starts a check immediately and keeps running after successful empty or matching checks until cancelled; no deferred mode flag is needed. It performs no overlapping checks for the same target and uses cancellable waits. D11 still owns detailed cadence, failure exhaustion, expiry and alert-repeat policy. Do not implement legacy mode switches to fill those open decisions.

## Representative initial workflows

IDs come from discovery. The availability invocation follows the search-forever default; detailed run-mode design remains TODO D11. See the [CLI guide](../../cli.md) for installation and supported behavior.

```bash
camply providers
camply recreation-areas --search Yosemite --state CA
camply campgrounds --rec-area 2991
camply campsites --campground 232450 --start-date 2027-07-10 --end-date 2027-07-18 --nights 3
```

Examples using YAML, individual campsite IDs, legacy run-mode flags, equipment, external notifications or persistent history belong to the deferred reference inventory, not initial setup guidance.

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

**Independent test**: Invoke the real installed `camply campsites` command from outside the checkout with a base-only wheel and synthetic provider HTTP responses. Observe the parsed request, printed stays, a second completed check after a match, and cleanup on cancellation. Internal-operation tests supplement this public-command test; they cannot replace it. Deferred legacy flags/cron contracts remain outside this test.

1. **Given** paired search windows, **when** an availability check runs, **then** only nights inside the checkout-exclusive windows are considered, with no duplicate stays from overlap.
2. **Given** area/campground selectors, **when** targets resolve, **then** duplicate targets make only one logical availability check per cycle; individual campsite selection is deferred.
3. **Given** `--weekends --day Sunday`, **when** matching runs, **then** Friday, Saturday and Sunday are eligible; stays do not bridge gaps or combine sites.
4. **Given** a four-night run and `--nights 3`, **when** stays are presented, **then** two sliding three-night stays appear. An impossible stay length is rejected rather than downgraded.
5. **Given** provider timeout/429/schema failure, **when** checking, **then** failure is distinguished from a successful empty result and shared retry/pacing behavior applies.
6. **Given** repeated provider/area/campground/day/date options, **when** the actual command parses them, **then** provider precedence, campground-over-area selection and paired windows reach the upstream request/matching layer as specified; overridden area IDs are not fetched.
7. **Given** a matching first check, **when** no mode flag is supplied, **then** the command prints the stay and performs a second check instead of exiting. On Ctrl-C/SIGTERM, it stops scheduling work and closes owned clients/tasks; no background polling remains.
8. **Given** absent or malformed notification credentials, **when** the initial CLI runs, **then** console results still work with no credential validation, external notification requests or web-user lookup. Supplying `--notifications pushover` fails as an unsupported option.
9. **Given** an exact campground beyond the first 50 discovery results or an area with more than 1000 campgrounds, **when** commands resolve the selection, **then** exact lookup succeeds and area availability enumerates every eligible target without truncation.

### Deferred user journeys

D01–D13 retain the legacy inventory's workflows for future design. YAML migration, all external notification delivery including Pushover, notification setup/testing/parity, equipment, permits, TUI, persistent cron history and the legacy mode matrix have no initial acceptance gate. Add their implementation scenarios when the corresponding TODO is brought into scope. Revisit detailed mode tests after D11 brainstorming; retain search-forever as the intended default.

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

- **FR-001 — Initial**: Restore provider listing, recreation-area/campground discovery and campground-based availability through lazy Click commands implementing the initial command contract, including provider/debug precedence, repeatability, defaults and output streams. Preserve serving/database commands and base-only help/version behavior. C07/C08/C10/C12 and Rich-click are deferred under D01/D07–D10.
- **FR-002 — Initial, limited coverage**: Resolve currently supported providers case-insensitively through canonical identities and compatible aliases. Preserve command provider → root provider → environment → default precedence. Defer missing legacy providers and GoingToCamp deployment translation to D04; never misinterpret a legacy deployment selector as a native park ID.
- **FR-003 — Initial, limited capabilities**: Provide database-independent recreation-area/campground discovery and campground/area target resolution. Exact campground metadata lookup must work outside the discovery display limit. Complete target expansion must paginate/batch beyond feature 025's per-call limit, deduplicate provider-qualified targets and expose errors/truncation. Site-ID lookup/catalogs and equipment capabilities are deferred under D01/D02/D07.
- **FR-004 — Initial, limited filters**: Support area/campground selection, paired exclusive windows, day/weekend union and exact-length sliding stays. Exclude expired nights consistently with the web engine. Reject impossible constraints; individual campsite and equipment restrictions are deferred under D02/D07.
- **FR-005 — Initial default; mode design TODO D11**: The public availability command starts immediately and continues after empty or matching checks until cancellation, without a mode flag; this is the initial search-forever default. Brainstorm the lifecycle and `--continuous` / `--search-forever` / `--search-once` semantics later. Do not require legacy one-pass defaults or implicit flag triggers.
- **FR-006 — Initial foundation; scheduling pending D11**: Use shared async retry/rate-limit clients; avoid overlapping a target's requests and distinguish failures from empty availability. CLI interval defaults, minimums and polling schedule remain open for D11 design.
- **FR-007 — TODO D03/D11/D12/D13**: All external notification delivery, lifetime alert suppression, first-batch/general caps and persisted per-channel outcomes are deferred. Legacy 5/20 limits are historical evidence, not initial policy; console-only CLI checks cannot dispatch web notification work.
- **FR-008 — TODO D13**: Defer offline flags, JSON history/import, cross-process duplicate suppression, locking and pickle migration. Initial commands do not write a CLI history file.
- **FR-009 — TODO D05**: Defer YAML aliases, schema/default compatibility, interpolation, precedence and repairs.
- **FR-010 — TODO D03/D10**: Defer `configure`, legacy `.camply` handling and all CLI notification credentials. Initial commands require no notification settings; credential migration and wizard behavior need later design.
- **FR-011 — Initial console-only; delivery TODO D03**: Display availability and provider booking links in the terminal only. Do not expose `--notifications`, send Pushover/other external alerts, read notification credentials or query web users. All CLI external delivery/credential contracts are deferred. Preserve existing web notifications unchanged.
- **FR-012 — TODO D03**: Defer `test-notifications`, Pushover activation/credential resolution and all external-channel diagnostic/failure contracts. There is no initial CLI delivery integration.
- **FR-013 — TODO D04/D06**: Defer missing campground/provider/deployment coverage, permits and legacy ticket/tour/timed-entry inventory. Preserve the audit as a future mapping reference; no new inventory adapters are required initially.
- **FR-014 — TODO D08/D09**: Defer optional TUI and Rich-click. Ordinary Click help/output is sufficient for the initial CLI.
- **FR-015 — Initial**: Show provider/parent/site names and IDs, qualifying dates, stay counts and provider booking links when available; never invent missing data. Use deterministic readable output and sanitized debug/plain logging. Rich presentation and equipment output are deferred.
- **FR-016 — Initial foundation; lifecycle pending D11**: Validate inputs, expose provider failures, and close owned clients/tasks on cancellation. Final command exit/status, expiration, retry exhaustion and stop-after-match/cron semantics must be designed with D11 rather than copied from legacy behavior.
- **FR-017 — Initial**: Local commands run from a base `camply-web` wheel without server/distributed/postgres/sentry extras, accounts, metadata import, frontend process or external database/broker. Bound requests/queues; create no application database or persistent CLI history by default.
- **FR-018 — Initial**: Reuse current async providers, typed validation and matching; do not vendor/invoke the legacy CLI. Preserve Import Linter boundaries through explicit shared-code design and regression checks, and protect standalone/distributed behavior. Avoid abstractions needed solely by deferred features.

### Key entities in initial scope

- **Search request**: Current provider, ordered date windows, area/campground selectors and day/stay restrictions. The initial lifecycle is immediate continued checking until cancellation; D11 retains detailed scheduling policies.
- **Resolved target**: Provider-qualified campground with required native parent context, independent of web subscriptions.
- **Availability stay**: Provider/site identity, arrival/checkout, attributes and booking URL derived from successful live observations. Observed site identity is needed to construct stays; accepting campsite-ID search input is deferred.
- **Capability entry**: Current provider operations and explicit unsupported/unavailable reasons. Full legacy deployment compatibility is deferred.

Persistent history, YAML models, equipment/permit/slot models and additional channel settings are future entities, not initial schema work.

## Success criteria

- **SC-001**: Every legacy inventory entry has a documented initial/deferred disposition. Initial supported behavior has contract fixtures; D01–D13 need no implementation fixture to ship this scope.
- **SC-002**: Fresh installed-base tests invoke the actual `camply` entrypoint outside the checkout for discovery and availability, without services/account/catalog. The availability process must print expected stays, make a subsequent check after a match, and remain running until test cancellation. Help/version/provider listing perform zero network calls and create zero state files. Internal checks alone do not satisfy this gate.
- **SC-003**: Public Click tests verify the complete command/option contract, including root/command/environment precedence, repeated IDs/dates/days, selector precedence, exact-ID resolution, limits, printed stays and malformed/deferred-input rejection. Scripted internal checks supplement them for target deduplication, matching and provider retries. Installed console-only tests also assert zero notification-service requests, database-user lookups or delivery dispatch with notification settings absent or malformed. Legacy run-mode, notification cap and history tests stay deferred.
- **SC-004**: Identical observations yield equivalent eligible nights across CLI/web matching, with exact-length CLI stay presentation tested separately. Duplicate windows/targets cause no duplicate logical checks per cycle.
- **SC-005**: Public-command tests verify invalid/unsupported inputs fail clearly before availability IO and cancellation closes owned resources and leaves no further scheduled requests. Installed subprocess signal tests and in-process cleanup assertions cover both process termination and resource ownership; forced process kill alone does not establish cleanup. Persistent-state recovery and detailed lifecycle timing gates await D13/D11.
- **SC-006**: Python 3.11/default 3.14 installed-artifact checks, provider HTTP contracts, Import Linter and relevant serve/db/web/worker regressions pass. Apply project quality gates to initial implementation; do not require deferred providers, extras or inventory to pass this gate.

## Assumptions and boundaries

- Initial runtime implementation requires no database migration. The legacy audit remains intact while D01–D13 defer implementation. Later work must explicitly bring a TODO into scope before designing or implementing it.
- The legacy name/release distinction and current package publication remain explicit. Users install `camply-web` to obtain the `camply` executable; parallel installation with legacy `camply` conflicts and requires an isolated environment or deliberate replacement. Legacy PyPI/image ownership and major-version cutover are separate release decisions.
- Local foreground execution is the parity target. Remote hosted CLI authentication, saved web-scan administration, shell completion and machine-readable output are potential future features, not prerequisites.
- No auto-booking, reservation guarantees, exact terminal formatting or public legacy Python API parity. Network access to upstream booking providers remains necessary; initial CLI operation makes no notification-service requests.
