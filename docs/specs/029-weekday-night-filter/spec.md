# Feature Specification: Nights of the week

**Feature**: `029-weekday-night-filter`

**Created**: 2026-11-15

**Status**: Implemented and verified

**Input**: “Nights of the week should be an option in the Web UI as well as the CLI. Similar to the legacy CLI, some people want weekends, or select days of the week only. For example: ‘give me any weekend this summer at campground foo’.”

## User Scenarios & Testing

### User Story 1 - Monitor any weekend in a date range (Priority: P1)

A camper selects a campground and a broad date range, chooses weekend nights, and receives matches only for those nights. One saved scan covers every weekend in the range, without a separate scan for each weekend.

**Why this priority**: This directly serves the request to find any weekend during a season while avoiding irrelevant midweek openings.

**Independent Test**: Create a scan for a synthetic campground from June 1 through September 1, 2027, choose Friday and Saturday nights, and set a two-night minimum. Supply midweek openings, isolated Friday or Saturday openings, and complete Friday–Saturday openings. Only complete weekend stays qualify, with Sunday checkout.

**Acceptance Scenarios**:

1. **Given** a new scan with a summer date range, **when** the user chooses “Weekends,” **then** Friday and Saturday nights are selected, the date range stays unchanged, and one scan covers all eligible weekends within it.
2. **Given** weekend nights and a two-night minimum, **when** a campsite has Thursday through Sunday nights available, **then** results and alerts include only Friday and Saturday nights, presented as Friday check-in and Sunday checkout.
3. **Given** weekend nights and a one-night minimum, **when** only Saturday is available, **then** Saturday check-in and Sunday checkout qualify; the weekend shortcut does not silently require two nights.
4. **Given** weekend nights and a two-night minimum, **when** Friday is available at one campsite and Saturday at another, **then** neither campsite qualifies.
5. **Given** a valid new scan with no weekday restriction specified, **when** it is saved, **then** all seven nights remain eligible as they are today.

---

### User Story 2 - Choose and edit individual nights (Priority: P1)

A camper selects any combination of nights, sees those preferences on their scan, and can change or remove the restriction later.

**Why this priority**: Work schedules and travel plans vary; weekends alone do not cover the requested selection of specific days.

**Independent Test**: Save a Monday/Wednesday scan, reload it, edit it to Sunday/Monday with a two-night minimum, and verify the saved selection and matching results. Cancel another edit and verify the previous saved selection remains intact.

**Acceptance Scenarios**:

1. **Given** a new or existing scan form, **when** the user selects individual nights, **then** each of the seven nights has a clear selected state and can be operated with a keyboard on desktop and mobile layouts.
2. **Given** Monday and Wednesday nights and a one-night minimum, **when** Monday, Tuesday, and Wednesday are available, **then** Monday and Wednesday appear as separate one-night stays; Tuesday is excluded.
3. **Given** Sunday and Monday nights and a two-night minimum, **when** both consecutive nights are available at one site, **then** Sunday check-in and Tuesday checkout qualify across the calendar-week boundary.
4. **Given** a saved selection, **when** the user reloads the dashboard, opens scan details, or reopens editing, **then** the same nights are shown; unrestricted scans are identified as “Any night.”
5. **Given** an existing restricted scan, **when** the user chooses “Any night” and saves, **then** all seven nights become eligible. Canceling preserves the previous saved selection. A failed save preserves entered values for retry without changing saved state.
6. **Given** an existing scan, **when** only its night selection changes, **then** its identity, dates, active preference, and other filters remain intact, and other subscribers' results do not change.

---

### User Story 3 - Use the same night rules in the CLI (Priority: P1)

A terminal user continues to use the existing day and weekend options and can rely on the same eligible-night rules as web users.

**Why this priority**: The CLI already supports these selectors; the feature must preserve that behavior while bringing the Web UI to parity.

**Independent Test**: Run equivalent web and CLI searches against the same synthetic availability for unrestricted nights, weekends, individual days, and a weekend-plus-Sunday selection. Compare eligible nights and qualifying consecutive blocks while preserving each interface's stay-length presentation.

**Acceptance Scenarios**:

1. **Given** a CLI search, **when** the user supplies `--weekends`, **then** Friday and Saturday nights are eligible; `--weekends --day Sunday` makes Friday, Saturday, and Sunday eligible.
2. **Given** repeated `--day` options, **when** full English names or existing case-insensitive abbreviations are supplied, **then** their union is eligible and repeated values have no additional effect. Unknown day names produce a clear validation error.
3. **Given** equivalent date ranges, night selections, and a stay length of two, **when** an opening spans Friday, Saturday, and Sunday nights, **then** weekend-only searches in both interfaces qualify Friday–Saturday, with Sunday checkout. With all three nights selected, the web may show the maximal three-night block and the CLI retains its exact two-night sliding stays.
4. **Given** no day or weekend options, **when** the CLI searches, **then** all nights remain eligible. Existing paired date windows and their gaps retain their current behavior.

### Edge Cases

- A checkout weekday need not be selected: Friday and Saturday nights end on Sunday.
- Friday availability on successive weeks does not form a consecutive two-night stay. Disallowed nights break stays even when the site is available on them.
- A selected weekday absent from the date range, an explicitly empty selection, and a stay length that cannot fit the selected nights produce actionable validation errors before a new search starts or changed search criteria are saved. No matches from current provider availability is a valid empty result, not invalid search criteria.
- Weekend-only selection with a three-night minimum is impossible and must not be silently widened to include Sunday or shortened to two nights.
- Date boundaries remain check-in inclusive and checkout exclusive. Month/year boundaries, leap days, and daylight-saving changes do not change a booking night's weekday.
- Past-night expiration follows the existing current-UTC-day rule. A scan that becomes unable to match as time passes shows no current matches; ordinary reads and pause/resume actions remain possible.
- Existing scans and older callers that omit the new preference remain unrestricted. An unrelated edit preserves a saved restriction.
- Invalid updates leave saved data unchanged. Duplicate day values are equivalent to one selection, and order has no effect.
- Pending notifications are rechecked against current saved nights before delivery, including when an edit removes their last qualifying stay.

## Requirements

### Functional Requirements

- **FR-001 — Selection**: Web users MUST be able to choose any nonempty subset of the seven nights when creating or editing a scan. New scans MUST default to all seven nights. Controls MUST have accessible day names, expose selected states, support keyboard operation, and fit mobile layouts.
- **FR-002 — Shortcuts**: The web form MUST offer “Weekends” to select exactly Friday and Saturday nights and “Any night” to select all seven. These shortcuts MUST leave dates and stay length unchanged. Individual nights MUST remain adjustable afterward. Existing quick-date shortcuts MUST leave the night selection unchanged and remain distinguishable from recurring night selection.
- **FR-003 — Night semantics**: Selection MUST restrict each occupied night, rather than only arrival days. A night uses the weekday of the provider's booking calendar date, without conversion to the viewer's timezone. Checkout MUST remain exclusive and need not fall on a selected weekday.
- **FR-004 — Matching order**: Matching MUST first exclude nights outside the selected date windows, expired nights, and disallowed weekdays, then evaluate consecutive stay length at a single campsite. It MUST NOT bridge excluded nights, gaps between search windows, or different campsite identities. Other saved site preferences MUST still apply.
- **FR-005 — Stay lengths**: Web scans MUST retain minimum-stay behavior and show maximal qualifying consecutive blocks. CLI searches MUST retain exact-length sliding stays. Weekday selection MUST NOT change either meaning or implicitly change the requested length.
- **FR-006 — Persistence and display**: A saved scan's night selection MUST survive reloads, pause/resume, and service restarts; be restored when editing; and appear in dashboard and detail summaries as named nights or “Any night.” A saved change MUST apply to subsequent result reads and notification matching. Canceling MUST leave saved state unchanged; failed saves MUST preserve entered values for retry.
- **FR-007 — Compatibility**: Existing saved scans and creation requests omitting the preference MUST behave as “Any night.” Updates omitting the preference MUST preserve the saved selection; explicitly selecting all seven MUST clear the restriction. An explicitly empty selection MUST be rejected rather than interpreted as unrestricted. Existing same-owner duplicate-scan rules remain unchanged.
- **FR-008 — Validation**: New searches and creation or edits of date/night/stay criteria MUST reject unknown day values, empty selections, and combinations with no possible qualifying stay in the remaining date range, independent of current availability. Errors MUST explain which constraint to change and MUST NOT silently widen selections, shorten stays, or partially save changes. Expiration alone MUST NOT block reads or status changes on existing scans.
- **FR-009 — Results and alerts**: Scan details, dashboard match counts, direct alerts, and summary alerts MUST use the same saved night restriction and qualifying-stay rules. Only qualifying nights MUST appear in delivered availability. Pending alerts MUST be revalidated against current preferences before sending; an alert with no remaining qualifying stay MUST be skipped. Openings confined to excluded nights MUST NOT trigger alerts.
- **FR-010 — Subscriber isolation**: Night preferences MUST belong to the individual saved scan. Different subscribers watching the same campground and dates MUST retain independent results and alerts while sharing existing availability polling. Changing only a night preference MUST NOT change scan identity, alter another subscriber, or require a separate provider poll for each preference.
- **FR-011 — CLI compatibility**: Existing `--day` names, abbreviations, case insensitivity, repetition, and `--weekends` behavior MUST remain supported. CLI weekends MUST add Friday/Saturday to explicit days; no selectors MUST mean all nights. Equivalent web and CLI selections MUST identify the same eligible nights for the same dates and observations.
- **FR-012 — Supported operation**: Matching and delivery behavior MUST be equivalent in standalone and distributed deployments and across supported booking providers. User documentation MUST explain nights versus arrivals, Friday/Saturday weekend semantics, the interaction with stay length, and equivalent web/CLI examples for a seasonal weekend search.

### Key Entities

- **Night selection**: An unordered, duplicate-free set of allowed booking weekdays. All seven means unrestricted; an explicitly empty user selection is invalid.
- **Saved scan**: An existing user's subscription to a campground/date range, with independently saved night selection, stay length, site preferences, and active state.
- **Booking night and qualifying stay**: A calendar date at a particular campsite and a consecutive block of eligible available nights satisfying the interface's stay-length rule. Checkout is the following date after the final occupied night.
- **Shared availability target**: The existing shared campground/date-range observation, independent of subscribers' night preferences.

## Success Criteria

### Measurable Outcomes

- **SC-001**: One web scan for June 1–September 1, 2027 with weekend nights and a two-night minimum finds every supplied complete Friday–Saturday opening, with zero midweek or isolated-night matches in results, counts, or alerts.
- **SC-002**: All 127 nonempty subsets of the seven weekdays produce the expected eligible dates over a representative date range. Equivalent CLI and web selections agree on eligible nights; stay presentation follows FR-005.
- **SC-003**: All acceptance cases for save/reload, editing, canceling, failed saves, reset to “Any night,” and older unrestricted scans preserve the expected preferences and results.
- **SC-004**: Every impossible-constraint acceptance case is rejected with an actionable error before starting new search work or saving changed criteria. Valid searches with unavailable sites return zero matches without a validation error.
- **SC-005**: Two subscribers with different night selections over identical campground dates receive only their own qualifying results and alerts, with no additional shared availability checks caused solely by the different selections. Pending-alert edit cases deliver zero newly excluded nights.
- **SC-006**: A keyboard-only user can create and edit both a weekend selection and a custom selection, and the same flows remain usable in the supported mobile layout.

## Assumptions

- “Weekend” means Friday and Saturday occupied nights, consistent with the [current CLI contract](../026-cli-parity/spec.md) and [CLI guide](../../cli.md). Sunday night can be added explicitly. It is not an automatic requirement to book both nights; users choose a two-night minimum when they want a full weekend.
- “This summer” is expressed through an explicit start/end range using existing date controls. Natural-language date parsing, automatic seasonal ranges, holiday calendars, and configurable cultural weekend definitions are outside scope.
- The CLI already implements day and weekend filtering. This work adds the missing saved-web-scan capability and verifies parity; it does not introduce new CLI options or external CLI alerts.
- Existing campground discovery, date limits, authentication, site preferences, booking actions, and notification channels remain dependencies. Weekday selection does not expand their scope or promise provider bookability beyond observed availability and provider restrictions.
- Web searches continue to use one continuous date range per saved scan. Multiple disjoint web date windows, cross-campground stays, and changes to polling schedules are outside scope.
- Changing preferences revalidates current results and pending deliveries. Replaying previously suppressed availability as new alerts is outside scope; existing change-detection behavior remains in effect.
