# Feature Specification: CLI Full-Stack Parity

**Feature Branch**: `20261117-193928-cli-fullstack-parity`
**Created**: 2026-11-16
**Status**: Draft
**Input**: User description: "Add full-stack application feature parity to the camply CLI for capabilities currently missing from the CLI."

## Clarifications

### Session 2026-11-16

- Q: When filtering availability by specific campsites (`--campsite`), should the user still be required to specify at least one `--campground` or `--rec-area`, or should `--campsite` work standalone without a parent location? (FR-001) → A: Option A — Require at least one `--campground` or `--rec-area` alongside `--campsite`, filtering observed sites within those targets by campsite ID or name across all supported providers.
- Q: How should users supply Pushover and ntfy credentials and server settings when enabling CLI notifications or running `test-notifications`? (FR-003) → A: Select channels via `--notifications` (`pushover`, `ntfy`) and read all notification credentials and settings from environment variables (`PUSHOVER_USER_KEY`, `PUSHOVER_APP_TOKEN`, `NTFY_TOPIC`, `NTFY_SERVER_URL`, `NTFY_ACCESS_TOKEN`), without CLI flags for ntfy topic/server or database lookups.
- Q: How should `camply campgrounds` and `camply recreation-areas` switch between live database-free provider search and local catalog database search when cross-provider or amenity/radius filters are used? (FR-007) → A: Option C — Keep CLI discovery strictly live and database-free against upstream provider APIs; drop cross-provider search, discovery amenity filters, geographic radius search, and facets that require a populated local database catalog, and retain only live upstream pagination (`3b`) and canonical provider names in `camply db metadata` (`3d`).
- Q: Should we also remove persistent database-saved scan management (`FR-008`) from the CLI so that all user-facing CLI search and monitoring commands remain 100% stateless and database-free? (FR-008) → A: Option A — Remove persistent database-saved scan CRUD from this specification and track it on the project roadmap (`docs/PLAN.md`), keeping all CLI discovery, availability watching, and notifications 100% stateless and database-free.
- Q: Should `camply campsites` stay scoped to a single `--provider` per invocation (matching legacy `camply`), or should it support watching targets across multiple providers in one command? (FR-006) → A: Option A — Keep `camply campsites` scoped to a single `--provider` per invocation; drop flag-based multi-provider foreground watching from this specification and track multi-search/multi-provider YAML configuration on the project roadmap (`docs/PLAN.md`).

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Filter terminal availability searches by site type, equipment, hookups, accessibility, and specific sites (Priority: P1)

A camper using the terminal wants to watch for campsites that fit their actual setup—such as tent-only, RV, or cabin sites, electric hookups, ADA accessibility, a minimum RV or trailer length, or specific campsite IDs/names within selected campgrounds or recreation areas—so they do not get false matches for unusable sites.

**Why this priority**: Equipment, hookup, accessibility, and site-level filters directly prevent false-positive availability matches for sites a camper cannot physically occupy, bringing terminal availability watching in line with web scan filtering without requiring a server or database.

**Independent Test**: Run a foreground CLI availability search against synthetic provider availability containing mixed tent, RV, cabin, electric, non-electric, ADA-accessible, and length-limited sites. Confirm only sites satisfying every requested filter appear in output (preserving the existing classic CLI output format and exact `--nights` stay behavior), and confirm unsupported provider filters or `--campsite` without `--campground`/`--rec-area` fail validation before polling starts.

**Acceptance Scenarios**:

1. **Given** a campground with a 35-foot electric RV site, a 20-foot electric RV site, and a tent-only non-electric site, **When** a user searches in the CLI requiring RV sites with electric hookups and a minimum vehicle length of 28 feet, **Then** only stays from the 35-foot electric RV site appear in results.
2. **Given** an accessibility requirement is enabled on a CLI availability search, **When** provider results include an explicitly accessible site, a non-accessible site, and a site with unknown accessibility, **Then** only stays from the explicitly accessible site qualify.
3. **Given** a user specifies one or more `--campsite` IDs or site names alongside `--campground` or `--rec-area`, **When** availability is checked, **Then** only matching campsites within those resolved campgrounds are included; passing `--campsite` without `--campground` or `--rec-area` fails with a clear usage error.
4. **Given** a provider whose capability metadata declares that a filter (such as minimum RV length or electric hookups) is unsupported, **When** a user supplies that filter for that provider, **Then** the CLI rejects the invalid combination before starting availability requests and explains which filter is unsupported, while the provider listing command clearly shows each provider's supported filter capabilities.

---

### User Story 2 - Receive Pushover and ntfy alerts with duplicate suppression from the CLI (Priority: P1)

A camper running the CLI in the terminal (either continuously or on a recurring cron/timer schedule) wants alerts sent to Pushover or ntfy when qualifying campsites open up—without being notified repeatedly for unchanged openings on every poll cycle—and wants a way to verify notification credentials before relying on an alert.

**Why this priority**: Real-time push alerting for newly discovered cancellations is the core reason campers monitor sold-out campgrounds over extended periods, and bringing Pushover and ntfy parity to the CLI completes the standalone monitoring workflow initiated in [CLI parity](../20261110-005958-cli-parity/spec.md).

**Independent Test**: Configure Pushover or ntfy environment variables for a synthetic CLI watch, run `camply test-notifications`, then run multiple poll cycles where an opening appears on cycle 1, remains unchanged on cycle 2, disappears on cycle 3, and reopens on cycle 4 (both in a continuous process and across separate single-pass invocations using an optional state file). Confirm the test alert succeeds, cycle 1 and cycle 4 trigger external alerts, and cycle 2 suppresses duplicate delivery.

**Acceptance Scenarios**:

1. **Given** `--notifications` (`pushover` or `ntfy`, repeatable) with settings in environment variables (`PUSHOVER_USER_KEY`, `PUSHOVER_APP_TOKEN`, `NTFY_TOPIC`, `NTFY_SERVER_URL`, `NTFY_ACCESS_TOKEN`), **When** a user runs `camply test-notifications`, **Then** a test message is delivered to each selected channel without querying a database, and the command reports delivery success or actionable failure details without leaking secret tokens.
2. **Given** an availability watch configured with `--notifications pushover` or `--notifications ntfy`, **When** a qualifying stay is observed for the first time, **Then** an external notification is sent containing the campground, site/stay details, dates, and direct provider booking link, while console output continues working as usual.
3. **Given** the same qualifying stay remains open on the next poll cycle (or on the next single-pass run when local state persistence is enabled), **When** no new dates or sites have opened since the previous check, **Then** no duplicate external notification is sent; if the stay closes and later reopens, a new alert is sent.
4. **Given** `--notifications` is not passed, **When** a user runs availability commands with missing or malformed notification environment variables, **Then** console-only monitoring succeeds without reading or validating notification credentials.

---

### User Story 3 - Browse beyond 50 live discovery results and use canonical provider names across CLI commands (Priority: P2)

A camper exploring destinations from the terminal wants to browse beyond the default 50-result display cap during live upstream discovery (`camply campgrounds` and `camply recreation-areas`) with zero database setup, and wants `camply db metadata` to accept canonical provider names alongside numeric IDs.

**Why this priority**: Live upstream discovery without database setup is a core CLI design principle; adding result limit/pagination controls and consistent provider naming removes friction without introducing a local catalog dependency.

**Independent Test**: Run `camply campgrounds` and `camply recreation-areas` against a synthetic upstream provider returning more than 50 results with custom limit/pagination options and zero database present; run `camply db metadata` with a canonical provider name (`RecreationDotGov`).

**Acceptance Scenarios**:

1. **Given** more than 50 matching campgrounds or recreation areas exist in a live upstream provider response, **When** a user requests a larger bounded `--limit` (`1..500`, default `50`), **Then** additional results are displayed deterministically without requiring any database setup.
2. **Given** an operator running local database metadata population (`camply db metadata`), **When** they specify a provider by its canonical CLI name (such as `RecreationDotGov` or `ReserveCalifornia`) in addition to numeric ID or `all`, **Then** the command resolves the provider consistently with discovery and availability commands.

---

### User Story 4 - Control run cadence and emit JSON output (Priority: P2)

A camper wants to control whether foreground CLI monitoring runs once or continuously on a custom interval, and emit machine-readable JSON output for scripting—all directly from the stateless CLI.

**Why this priority**: Power users, cron jobs, and automation scripts need flexible foreground run modes (one-shot checks vs. continuous polling with custom intervals) and structured JSON output without requiring a database or web server.

**Independent Test**: Run foreground `camply campsites` in single-pass mode, with a custom interval, and with `--json` output (as well as discovery commands with `--json`) against synthetic upstream provider responses with no database present.

**Acceptance Scenarios**:

1. **Given** a user runs `camply campsites` with a single-pass mode option, **When** the availability check completes, **Then** the CLI prints results (and sends any configured notifications) and exits cleanly rather than looping indefinitely.
2. **Given** a user supplies a custom polling interval within safe provider bounds, **When** continuous foreground monitoring runs, **Then** subsequent checks wait for the configured interval (rejecting unsafe sub-minimum intervals).
3. **Given** a user passes the JSON output flag (`--json`) to `providers`, discovery (`recreation-areas`, `campgrounds`), or single-pass availability (`campsites --search-once`) commands, **When** the command executes, **Then** valid machine-readable JSON is written to stdout while diagnostics remain on stderr.

---

### Edge Cases

- **Unknown site attributes fail closed**: When a provider omits vehicle length, electric status, or ADA accessibility on a site, active filters requiring those attributes MUST exclude the site rather than guessing, while unrestricted searches MUST still include it.
- **Campsite filter requires parent target**: Supplying `--campsite` without at least one `--campground` or `--rec-area` MUST be rejected as a usage error before any network request is made; blank `--campsite` values MUST also be rejected.
- **Zero-sentinel and invalid equipment inputs**: Non-positive RV lengths (`<= 0`), lengths above practical upper bounds (`> 200` feet), or unknown campsite types MUST be rejected with actionable validation errors before network requests begin.
- **Provider capability mismatches**: Filters supported by some providers (e.g., RV length) and unsupported by others MUST be validated against the selected provider before starting checks and fail clearly rather than being silently ignored.
- **Missing notification credentials when `--notifications` is set**: Selecting `--notifications pushover` without `PUSHOVER_USER_KEY` and `PUSHOVER_APP_TOKEN`, or selecting `--notifications ntfy` without `NTFY_TOPIC`, MUST fail validation before starting availability requests; all notification credentials and settings are read from environment variables only (not CLI flags or database user rows).
- **Notification failures must not crash monitoring**: Transient Pushover or ntfy HTTP errors during a live watch MUST be reported as safe diagnostics (with secrets redacted) without terminating foreground monitoring or losing track of console output; however, explicit test-notification commands MUST exit non-zero on failure.
- **Duplicate suppression across cycle failures and restarts**: If a poll cycle fails for a campground due to a provider error, previously tracked open stays for that campground MUST NOT be purged as "closed," avoiding false re-open alerts on recovery. When an optional state file is used with single-pass runs, corrupted or unreadable state files must be reported clearly without crashing console availability checks.
- **Stateless CLI execution**: Live provider discovery (`campgrounds`, `recreation-areas`), live availability watching (`campsites`), and direct Pushover/ntfy alerts (`test-notifications`, `campsites --notifications`) MUST run directly against upstream APIs with base package dependencies only and zero database setup.
- **Machine-readable output**: Structured JSON output on stdout MUST never be interleaved with Rich banners, progress spinners, or diagnostic log lines.
- **Credential redaction**: Notification tokens (`PUSHOVER_USER_KEY`, `PUSHOVER_APP_TOKEN`, `NTFY_ACCESS_TOKEN`) MUST NEVER appear in stdout, stderr, `--debug` diagnostics, or error messages.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001 — Campsite, equipment, & site-ID filtering**: The availability command MUST accept optional filters for campsite types, electric hookups, ADA accessibility, minimum RV/trailer length in feet, and repeatable `--campsite` ID/name selectors (which require at least one `--campground` or `--rec-area` target and filter observed sites within those targets), validating inputs and provider filter capabilities before making availability requests and evaluating filters identically to the web application's matching rules while preserving the existing single-provider CLI stay-matching and console output format.
- **FR-002 — Provider filter capability & name consistency**: The provider listing command MUST display which site-attribute filters each provider supports, and database metadata commands (`camply db metadata`) MUST accept canonical provider names in addition to numeric provider IDs and `all`.
- **FR-003 — External notification channels & credential resolution**: The CLI MUST accept repeatable `--notifications` (`pushover`, `ntfy`) on `campsites` and a dedicated `test-notifications` command, resolving all notification credentials and settings exclusively from environment variables (`PUSHOVER_USER_KEY`, `PUSHOVER_APP_TOKEN`, `NTFY_TOPIC`, `NTFY_SERVER_URL` defaulting to `https://ntfy.sh`, and `NTFY_ACCESS_TOKEN`), without querying database user records.
- **FR-004 — Alert deduplication & state persistence**: When external notifications are enabled during CLI monitoring, the CLI MUST suppress repeated notifications for unchanged openings across poll cycles, support an optional local state file to preserve seen-opening deduplication across separate single-pass (`--search-once`) invocations, re-alert only on newly opened or reopened stays, and preserve console-only operation with zero credential lookups when notifications are not enabled.
- **FR-005 — Run-mode & cadence controls**: The availability command MUST support both continuous polling (preserving the current default) and a single-pass check-once mode that exits after one cycle, as well as an optional bounded polling interval flag enforcing safe minimum intervals.
- **FR-006 — Live upstream discovery pagination**: Discovery commands (`campgrounds`, `recreation-areas`) MUST remain strictly live and database-free against upstream provider APIs while supporting a bounded `--limit` (`1..500`, default `50`) option beyond the default 50-item display cap.
- **FR-007 — Structured output & stream separation**: Provider listing (`providers`), discovery (`recreation-areas`, `campgrounds`), and single-pass availability (`campsites --search-once`) commands MUST support optional machine-readable output (`--json`) on stdout while keeping logs and diagnostics on stderr, preserving clean shell-pipeline composability.
- **FR-008 — Dependency & credential safety**: Live provider discovery, foreground availability filtering, and direct Pushover/ntfy notifications MUST continue running in a base package installation without requiring optional server or distributed-worker dependencies. All notification tokens and secrets MUST be redacted from logs, debug output, and error messages.

### Key Entities

- **CLI Availability Query**: Single selected provider (`--provider`), parent target(s) (`--campground` or `--rec-area`), date windows, weekday night filters, exact stay length (`--nights`), site/equipment filters (site types, electric, ADA, minimum RV length, and optional `--campsite` IDs/names scoped within those parent targets), run mode (`continuous` vs. `single-pass` and polling interval), and notification options.
- **Notification Channel & Deduplication State**: Selected delivery channel(s) (`pushover`, `ntfy`), environment-sourced settings (`PUSHOVER_USER_KEY`, `PUSHOVER_APP_TOKEN`, `NTFY_TOPIC`, `NTFY_SERVER_URL`, `NTFY_ACCESS_TOKEN`), and seen-openings state (in-memory for continuous runs, optionally persisted to a local file for recurring single-pass runs).
- **Live Discovery Query**: Single-provider upstream text query, optional two-letter state code, entity type, and bounded `--limit` (`1..500`, default `50`) parameter requiring zero database state.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: In synthetic availability suites covering all filter dimensions (site type, electric hookup, ADA accessibility, RV length, campsite ID/name), 100% of qualifying sites in CLI output agree with the web matching engine for identical provider observations, and 0% of unverified or undersized sites pass active filters.
- **SC-002**: Unsupported provider/filter combinations, `--campsite` without a parent target, and invalid equipment inputs are rejected 100% of the time before any upstream availability HTTP request is sent.
- **SC-003**: With Pushover or ntfy enabled across multi-cycle synthetic availability runs (both continuous in-memory and single-pass with a state file), 100% of newly opened and reopened stays trigger delivery while repeated unchanged cycles produce 0 duplicate notifications, and transient provider failures produce 0 false close/reopen alerts.
- **SC-004**: Live upstream discovery commands return deterministic results beyond the default 50-item cap with zero database access, and `camply db metadata` accepts canonical provider names for all 26 providers.
- **SC-005**: Base-wheel installations without `server` or `distributed` extras pass all live discovery, filtered availability, single-pass, JSON output, and direct Pushover/ntfy notification tests with zero missing-dependency errors and zero leaked credentials in stdout/stderr logs.

## Assumptions

- **Stateless-first CLI**: All user-facing CLI discovery (`providers`, `campgrounds`, `recreation-areas`), foreground availability watching (`campsites`), and external alerting (`test-notifications`, `campsites --notifications`) operate directly against upstream provider APIs with zero database setup.
- **Backward compatibility**: All existing CLI commands, single-provider per-command scoping, classic log output formatting, exact `--nights` stay matching, and defaults from [CLI parity](../20261110-005958-cli-parity/spec.md) (`providers`, `recreation-areas`, `campgrounds`, `campsites` continuous console-only default, `serve`, `db`) remain unchanged when new options are omitted.
- **Out of scope**:
  - Database-backed CLI features: persistent saved scan CRUD (`camply scans`) and catalog-backed cross-provider/amenity/geographic discovery (tracked on the roadmap in [docs/PLAN.md](../../PLAN.md)).
  - Multi-provider/multi-search CLI orchestration via flags (tracked as a declarative YAML configuration feature on the roadmap in [docs/PLAN.md](../../PLAN.md)).
  - Enriched availability terminal output changes (site attribute/restriction columns) and web-style minimum-stay contiguous block mode on `camply campsites`.
  - Summary notification aggregation in the CLI (CLI notifications use direct per-opening alerts).
  - Destination enrichment detail inspection in the CLI.
  - Remote `camply-web` account, authentication, session, and admin CLI client operations.
  - Legacy notification channels outside Pushover and ntfy, interactive terminal UI (TUI), Rich-click help styling, and backcountry permits/tours.
