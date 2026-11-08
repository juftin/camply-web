# Feature Specification: Legacy CLI parity

**Feature**: `026-cli-parity`
**Created**: 2026-11-08
**Status**: Draft — specification and source audit only; CLI parity is not implemented
**Input**: Give users of `juftin/camply` the CLI experience they know while using the current architecture and capabilities.

## Goal and compatibility baseline

Users can discover locations, search availability, watch for cancellations, and receive alerts using familiar Camply commands without running a web server or provisioning infrastructure. The same provider and matching capabilities serve CLI and web workflows.

The baseline is legacy [v0.34.4](https://github.com/juftin/camply/releases/tag/v0.34.4), audited on 2026-11-08. “Camply v1” identifies the legacy generation, not a literal upstream major-version tag. The [legacy audit](legacy-audit.md) is the exhaustive surface inventory: C01–C12 commands/global behavior, S01–S16 search options, every YAML key, all 19 provider names, 17 GoingToCamp deployment selectors and 10 notification channels. Its replacement column distinguishes current foundations from missing work. The [plan](plan.md) records architectural implications; [tasks](tasks.md) records pending delivery slices.

## Scope and release claims

The first delivery supports discovery and local availability on currently registered camping providers, followed by monitoring/state/notifications. Broader legacy provider coverage is a separate delivery gate, not an excuse to hide missing features. `providers` must identify unavailable legacy providers and explain blockers. Each release must publish a compatibility matrix identifying implemented, intentionally changed, blocked and pending behavior.

“Full CLI parity” requires every baseline entry either passing its acceptance contract or having an explicitly documented intentional difference from this specification. A missing adapter or channel is a gap, not an intentional difference. Broader GoingToCamp, Yellowstone, Alabama/Maricopa and Recreation.gov tours/timed entry remain required parity work even if shipped later. Existing `serve`, serving roles/health checks, and `db` subcommands remain supported.

## Representative compatibility workflows

These are target syntax examples, not commands implemented by this change. IDs come from discovery and dates must still be in the future when run.

```bash
# Discover a park, then campgrounds, then individual sites.
camply recreation-areas --search Yosemite --state CA
camply campgrounds --rec-area 2991
camply list-campsites --campground 232450

# One pass: three-night stays starting anywhere in the window.
camply campsites --campground 232450 --start-date 2027-07-10 --end-date 2027-07-18 --nights 3

# Monitor and notify; continue after matches, with persisted duplicate suppression.
camply campsites --campground 232450 --start-date 2027-07-10 --end-date 2027-07-18 --notifications pushover --search-forever --offline-search

# A cron invocation using a saved search with search_once: true.
camply campsites --yaml-config /path/to/search.yaml

# Keep familiar provider and channel diagnostics.
camply providers
camply test-notifications --notifications pushover --notifications email
```

For a cron YAML file, set `search_once: true` and `offline_search: true`; omit `continuous` so the one-cycle override applies. For flag-only cron commands, use `--search-once --notifications NAME --offline-search`. Saving history still performs live upstream checks each invocation.

## User Scenarios & Testing

### User Story 1 — Discover and run an existing search (P1)

A CLI user pastes a familiar discovery command, obtains IDs, and searches one or more sites/windows from a fresh base installation.

**Why**: This restores the core useful CLI workflow before any background services or accounts are needed.

**Independent test**: In an installed base wheel outside the checkout, use synthetic upstreams to discover and search a registered provider with no database, server extra, or populated catalog.

1. **Given** Recreation.gov results, **when** the user runs `camply recreation-areas --search Yosemite --state CA`, **then** names and usable provider-native IDs appear.
2. **Given** multiple area, campground and site selectors, **when** Recreation.gov runs, **then** site selectors take precedence, matching legacy selection, and duplicate targets make only one logical availability check per cycle.
3. **Given** two paired windows, **when** the user searches, **then** only nights inside those checkout-exclusive windows are considered, with no duplicated stays from overlap.
4. **Given** an unknown or unavailable provider, **when** selected, **then** an actionable error occurs before network requests or file writes; no other provider is substituted.
5. **Given** a supported campground, **when** `list-campsites` runs, **then** it lists actual catalog site names/IDs without requiring availability on arbitrary dates.

### User Story 2 — Watch for cancellations or schedule cron (P1)

A user runs until the first match, runs indefinitely, or schedules one notification-capable cycle in cron.

**Why**: Cancellation monitoring is the legacy CLI's primary recurring use.

**Independent test**: A fake clock and scripted empty/match/unchanged/disappear/reappear responses verify requests, delivery counts, termination, persisted state and shutdown.

1. **Given** empty availability followed by a match, **when** `--continuous` runs, **then** the first check is immediate and subsequent checks respect the effective interval; the process exits after the match and delivery outcome is recorded.
2. **Given** `--search-forever`, **when** the same stay disappears and returns, **then** it does not notify twice during that run/history lifetime.
3. **Given** persisted JSON history, **when** separate `--search-once --offline-search` processes see the same stay, **then** only the first notifies, while each still checks upstream.
4. **Given** Ctrl-C/SIGTERM while waiting or fetching, **when** stopping, **then** requests/tasks close, state writes remain valid, and no process continues polling.
5. **Given** all selected nights expire, **when** another cycle is due, **then** monitoring stops with a clear explanation rather than looping forever.

### User Story 3 — Reuse configuration and alerts (P1)

A user supplies an old YAML file and notification environment or `.camply` configuration without rewriting the search.

**Why**: Saved searches and notification setup represent users' existing investment.

**Independent test**: Load sanitized legacy YAML/configuration fixtures with deterministic environment values and fake notification transports; verify normalized requests and channel payloads.

1. **Given** YAML with no `continuous` key, **when** read using either YAML option spelling, **then** it defaults to continuous; an equivalent flag-only invocation defaults to one pass.
2. **Given** YAML plus explicit search flags, **when** invoked, **then** file fields govern and ignored explicit flags are identified. File provider, including its default, governs over root provider.
3. **Given** 12 immediately available stays and external notifications, **when** the first cycle runs, **then** five notify by default; with `--notify-first-try`, all 12 notify. A batch of 25 with the flag sends at most 20 and reports suppression.
4. **Given** multiple selected channels, **when** one fails, **then** other channels are attempted, outcomes are reported separately and failure is visible to cron.
5. **Given** an existing `.camply`, **when** configuration changes are declined, **then** the file is unchanged; confirmed writes preserve unrelated keys and hide secrets.

### User Story 4 — Preserve advanced provider workflows (P2)

A user searches a particular equipment category, a Yellowstone facility, another GoingToCamp deployment, or a Recreation.gov ticket/time slot.

**Why**: Camping-only syntax compatibility leaves established users behind without this coverage.

**Independent test**: Contract fixtures for every legacy provider name and each deployment mapping, with source-family integration tests and date/quantity/equipment boundary cases.

1. **Given** `GoingToCamp --rec-area 3`, **when** discovery/search runs, **then** it uses Washington's deployment and translates native park targets; native park ID 3 is not inferred from the legacy selector.
2. **Given** equipment restrictions, **when** no site meets them or capability is unsupported, **then** the CLI reports no match or unsupported respectively; neither silently broadens the search.
3. **Given** a daily ticket provider and `--equipment 1300 4`, **when** searching, **then** results require four available tickets in the 13:00 slot, not an RV length of four.
4. **Given** optional TUI support, **when** the user fills the search form, **then** previewed command and execution use the same validation and search behavior as the CLI.

### Edge cases

- Unequal/missing date pairs; reversed/equal endpoints; leap days; month/year crossings; past start; expired end; overlap; UTC day rollover during a run.
- `--weekends --day Sunday` includes Fri/Sat/Sun; nonadjacent allowed nights cannot form a consecutive stay. Stays never combine different site identities.
- A four-night run with `--nights 3` yields two distinct sliding three-night stays. An impossible five-night request is rejected, not downgraded.
- Opaque IDs, including contract-scoped IDs and `YLYB:RV`, are never globally coerced to integers. Equal IDs in different providers/entity types remain distinct.
- Site-only resolution where supported; required parent omitted where not; empty or enormous area expansion; disabled/unbookable catalog entries; discovery truncation must be explicit, never silently lose scan targets.
- Missing TUI/notification extra; unsupported channel/equipment; malformed webhook headers; missing environment interpolation; YAML unknown fields; conflicting modes.
- Absent, corrupt, unwritable, mismatched or concurrently used state file; interruption during save; legacy JSON with unknown provider identity; pickle suffix.
- Provider timeout/429/schema failure versus successful empty result; partial multi-target success; external acceptance followed by process failure; bounded cancellation while backoff is active.

## Requirements

### Functional requirements

- **FR-001**: Restore C01–C12 command names, documented options/aliases and provider/debug selection; preserve current serving/database commands. Root help/version/providers must work without network, database initialization or optional runtime imports.
- **FR-002**: Resolve providers case-insensitively through canonical identities plus legacy aliases; expose capability and availability information for all 19 names and all current providers. Preserve flag precedence: command provider, root provider, environment, default, except YAML's documented authority.
- **FR-003**: Provide database-independent discovery, exact-ID lookup, site-to-parent resolution, site catalogs and equipment catalogs where supported. Complete area expansion must paginate/batch beyond feature 025's per-call result limit; deduplicate provider-qualified targets and make truncation/errors explicit.
- **FR-004**: Support S01–S05 and S13–S14: provider selection rules, paired exclusive windows, day/weekend union, exact-length sliding stays, equipment OR constraints/length and scoped category selection. Exclude expired nights consistently with the web engine. Reject impossible or unsupported constraints before availability requests.
- **FR-005**: Implement all four modes: plain one-pass, poll-until-match, forever, and notification-enabled one-cycle. Preserve implicit continuous triggers from S07–S12. Validate contradictory modes consistently, including YAML repairs documented in the audit.
- **FR-006**: Default CLI interval to 10 minutes, clamp below 5 with a diagnostic, and honor stricter provider limits. Use shared async retry/rate-limit clients; never overlap a target's requests or treat transport/schema failures as empty availability. Report effective pacing and bounded retry exhaustion.
- **FR-007**: Preserve lifetime/history duplicate suppression for CLI separately from current web re-opening alerts. Identity includes provider, campground, site/resource, arrival, checkout and applicable slot; delivery status additionally includes channel. Notify only eligible new stays. First-batch and general limits are 5/20 as audited.
- **FR-008**: Preserve safe JSON saved-search history, path-implies-state behavior and the default path. Import baseline JSON with explicit/validated provider context, preserve enough fields for duplicate matching, write atomically and reject concurrent writers. Reject pickle with actionable guidance to export JSON using the old release. State is historical, never proof of live availability.
- **FR-009**: Support every audited YAML key/default and both file option spellings; handle scalar/list values and environment interpolation. Add optional `equipment_id`; reject unknown fields and unresolved environment references. Provide field-specific errors without echoing secrets. Document ignored explicit flags and run-mode repairs.
- **FR-010**: Read legacy `.camply` notification fields with process environment taking precedence. Configuration writes require explicit overwrite consent, mask secrets, preserve unrelated fields and use atomic/restricted writes. Provide explicit migration rules for current Pushover settings and obsolete RIDB configuration; do not copy embedded legacy credentials.
- **FR-011**: Support all ten audited notification names through shared adapters or verified equivalent mappings, including SMTP, SMS recipient fan-out and legacy webhook serialization. Always retain console results; isolate channel failures and validate configuration before searching. CLI links must lead directly to provider booking pages without requiring web accounts or a running server.
- **FR-012**: `test-notifications` must exercise each explicitly selected channel once with sample data, show individual outcomes and exit nonzero on failure. Terminal monitoring failures may send one sanitized diagnostic through capable selected channels; diagnostic failure cannot mask the originating error.
- **FR-013**: Recognize all legacy providers and deployment IDs; implement missing inventory using verified current upstream contracts. Ticket quantities/time slots and Yellowstone facility-level inventory must retain their meanings. Do not coerce non-camping inventory into false nightly campsite semantics.
- **FR-014**: Offer the optional TUI with command preview and shared validation/execution; ordinary installs and CLI behavior remain independent of it.
- **FR-015**: Show human-readable provider/parent/site names and IDs, qualifying dates, nights/counts and booking links; show price/capacity/equipment when available, never invent missing data. Deterministic ordering governs output and notification caps. Debug output remains sanitized; plain logging supports redirected/cron use.
- **FR-016**: Define process outcomes: 0 for a successful completed cycle (including no matches), 2 for invalid input/unsupported capability, 1 for exhausted provider, storage or delivery failure, 130 for Ctrl-C and 143 for SIGTERM. During forever mode report transient failures and continue with bounded backoff; terminate nonzero after configured exhaustion. Flush pending delivery/state before normal completion and report unsent work rather than silently succeeding. No exactly-once external-delivery guarantee.
- **FR-017**: Local commands must run from a base `camply-web` wheel without server, distributed, postgres or sentry extras, accounts, metadata import, frontend process or external database/broker. Optional notification/TUI packages may be extras with preflight guidance. Requests and queues must remain bounded; default state-free commands create no application database.
- **FR-018**: Reuse current async providers, typed validation, matching and notification policies; do not vendor or invoke the legacy CLI. Preserve Import Linter boundaries through an explicit shared-core design and regression checks. Existing distributed/standalone behavior must remain stable.

### Key entities

- **Search request**: Provider, ordered date windows, native selectors, weekdays, stay/equipment/slot restrictions, mode and interval; normalized once from flags or YAML.
- **Resolved target**: Provider-qualified campground/resource and optional site selection with required native parent context; independent of a web user/subscription.
- **Availability stay**: Provider/resource identity, arrival/checkout or timed slot, capacity, attributes and usable booking URL; derived only from successful live observations.
- **History record**: Versioned provider-qualified seen identity with per-channel delivery outcome, timestamps and compatibility-import context; separate from live results.
- **Capability entry**: Provider/legacy deployment mappings, supported inventory/discovery/equipment operations and an explicit unavailable reason.

## Success criteria

- **SC-001**: All C01–C12 and S01–S16 entries have contract fixtures and a published disposition; every claimed supported behavior passes its fixture. All 19 legacy provider aliases, 17 deployment mappings and 10 channel names have coverage.
- **SC-002**: Fresh installed-base tests complete discover → select IDs → one-pass search with no services/account/catalog. Help/version/provider listing perform zero network calls and create zero state files.
- **SC-003**: Scripted mode tests produce exact expected request counts, interval bounds, sliding stays, notification cap counts and termination outcomes, including restart/history cases.
- **SC-004**: Same raw provider observations yield equivalent eligible nights across CLI/web matching; CLI's exact-stay formatting and lifetime notification policy are verified intentional differences. Duplicate windows/targets produce no duplicate logical checks per cycle.
- **SC-005**: Invalid/unsupported requests fail before upstream availability IO; interrupted state saves leave a valid old or new file. Shutdown completes within five seconds under mocked blocking transports and sleeps.
- **SC-006**: Python 3.11 and default 3.14 installed-artifact checks, provider HTTP contracts, Import Linter and relevant existing web/worker regression suites pass. Full task quality gates pass before implementation PRs merge.

## Assumptions and boundaries

- This is a specification change, with no runtime behavior or migration implemented. Later provider verification can change endpoint choices, but not silently erase baseline coverage.
- The legacy name/release distinction and current package publication remain explicit. Users install `camply-web` to obtain the `camply` executable; parallel installation with legacy `camply` conflicts and requires an isolated environment or deliberate replacement. Legacy PyPI/image ownership and major-version cutover are separate release decisions.
- Local foreground execution is the parity target. Remote hosted CLI authentication, saved web-scan administration, shell completion and machine-readable output are potential future features, not prerequisites.
- No auto-booking, reservation guarantees, exact terminal formatting or public legacy Python API parity. Network access to upstream booking and selected notification services remains necessary.
