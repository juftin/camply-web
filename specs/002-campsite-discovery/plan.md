# UI/UX plan: find a campground, start a useful alert

Status: proposed; planning/research session only. No application code changed.

The recommended direction is **a calm, outdoors-oriented companion for finding a
place to camp**. The primary journey is Explore → Choose campground → Choose stay
→ Enable notifications → Watch → Book with the provider. Visual design should
support that journey and convey anticipation without obscuring the utility.

This plan extends the existing frontend blueprint rather than replacing the
poller architecture. Read [the specification](spec.md) for acceptance criteria and
[the research](research.md) for source evidence and capability limitations.

The [first-release brief](implementation.md) defines concrete work packages;
[design review](design-review.md) records candidate visual tokens and additional
feature opportunities. Use the [clickable wireframe](wireframes.html) to review
the proposed core journey before implementing it.

## 1. Design principles and tradeoffs

1. **One clear next action.** Search dominates the home page; setting an alert
   dominates campground details; booking dominates a matching-opening view.
2. **Let people explore first.** Ask for authentication when saving personal work,
   and preserve the work through sign-in. Keep external setup out of discovery.
3. **Start simple; reveal detail.** Dates and minimum nights are core. Specialized
   site/equipment requirements are optional and dependent on provider capabilities.
4. **Make state understandable.** Saved, monitoring, checked, notification-ready,
   and available mean different things. Show their differences in plain language.
5. **Make uncertainty visible.** Unknown metadata, a missing delivery test, and an
   old observation should be explicit; do not imply guarantees or success rates.
6. **Delight through ease.** Beautiful places, friendly wording, useful defaults,
   preserved context, and a small success moment matter more than animation volume.
7. **A list must stand on its own.** Maps enrich discovery, but the experience works
   on a phone, with low bandwidth, or without map configuration.

A full-page alert builder is recommended for the main journey: it has room for
notification setup, survives navigation, and handles the phone keyboard better
than a long nested dialog. Retain a lightweight dialog only for editing existing
filters if testing supports it. Avoid maintaining separate search/form behavior
for dashboard and campground entry points.

## 2. Information architecture

| Destination           | User-facing purpose                                     | Proposed route and migration                                                                           |
| --------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Home                  | Start finding a place; understand the service.          | Keep `/`; one search entry plus suggestions.                                                           |
| Explore               | Browse and refine search; eventually map/list.          | New `/explore`; preserve query in URL; add complete results API before claiming comprehensive filters. |
| Park                  | Compare campground options.                             | Keep `/rec-area/:providerId/:recreationAreaId`; use friendlier display language.                       |
| Campground            | Understand the place; start an alert or visit provider. | Keep `/campground/:providerId/:campgroundId`.                                                          |
| Alert builder         | Choose dates, requirements, and notification setup.     | New `/alerts/new` with validated campground reference; draft kept separately from URL.                 |
| My alerts             | See and manage monitoring.                              | Keep `/dashboard` initially; rename label; consider `/alerts` alias without breaking links.            |
| Alert detail          | View matching observations and take action.             | Keep current detail route initially; future alias must preserve notification deep links.               |
| Notification settings | Configure supported delivery channels.                  | Keep `/profile`; consolidate duplicated dashboard setup.                                               |
| Coverage and help     | Understand supported booking systems and setup.         | Keep `/providers`, `/how-it-works`, `/faq`; call Providers “Where we search.”                          |

Desktop navigation: Explore, My alerts when signed in, How it works; account/theme
controls on the right. Move project philosophy/contribution links to the footer.
Mobile: compact header plus persistent access to Explore/My alerts/Account when
that navigation exists. Do not hide critical navigation solely because scrolling
moves down. Implement a skip link, route-change focus handling, and current-page
indication. Show Basic sign-in versus Auth0 signup actions appropriately.

## 3. Screen proposals

### 3.1 Home: make the first minute inviting

Suggested hierarchy:

```text
camply                 Explore   How it works       Sign in

More time outside.
Less time refreshing.
Find a campground. We'll watch for an opening.

Where would you love to camp?
[ Search a park or campground                         ]
Try a favorite:  [Yosemite] [Joshua Tree] [Rocky Mountain]

Pick a place → Choose your stay → Get a notification

A few places to start
[Destination image + name] [Destination] [Destination]

Free and open source · Book through official reservation sites
```

- Put search in the first mobile viewport, before large decorative imagery.
- Use one outdoors image or local illustration; desktop can pair it with text,
  while mobile uses a shallow crop. No background-video dependency.
- Destination suggestions populate/focus actual search. Curated cards must resolve
  to supported metadata; do not call them trending without measured popularity.
- A returning visitor can see “Continue your alert” when a valid draft exists and
  “View my alerts” after authentication, without replacing discovery.
- State current beta status compactly and access limitations before final save.
  Remove unsupported channel, provider, user-count, and speed claims.
- Reserve scenic cards for discovery; avoid generic SaaS benefit/stat-card overload.
- Keep helpful explanations inline: “We notify you about openings. You book directly
  with the campground's reservation service.”

### 3.2 Search: predictable, useful, accessible

Autocomplete is for fast name lookup; a results page is for exploration. Start with
consistent autocomplete everywhere, then add complete browse/search infrastructure.

- Label the field “Park or campground”; keep placeholder as an example, not the label.
- Results show name, park/location when known, and “Park” versus “Campground.” Provider
  text is secondary. Parks lead to campground choices; campgrounds lead to details.
- Grouping by entity type can improve scanning; keyboard order must match visual order.
- Enter on a highlighted result opens it. In initial autocomplete-only mode, Enter
  without a selection opens the first current result. Once `/explore` exists, Enter
  without selection submits the query; document/test that intentional change.
- Arrow keys move the active option; Escape closes every state and keeps field focus;
  Tab continues normal focus; clear returns focus. Screen readers hear result counts.
- Suppress selectable old-query results while debouncing/loading. Cancel obsolete
  requests where supported. Keep input focus and avoid a moving dropdown height.
- Empty state: “No matches. Try a park name or a shorter search.” Network state:
  “We couldn't load places. Try again.” Preserve query on retry.
- Add session-only recent searches with clear-history control after the base flow.
  Persistent recent history requires a separate privacy decision.
- Search URLs should survive back/forward/share. Geographic/date/equipment refinements
  belong on complete server results, not a partial autocomplete list.
- Spelling suggestions, aliases, and name ranking are a backend search increment;
  use deterministic examples and avoid fuzzy matches presented as certainty.

### 3.3 Explore and park pages: choose with confidence

First iteration uses the existing park campground list:

- Page heading, location, short overview, official source, and visible campground count.
- Name filter plus applicable Reservable/Monitoring-supported controls. Explain that
  reservable means provider metadata, not open inventory on the camper's dates.
- Stable alphabetical default; local filtering is valid on this complete park list.
- Each card has a semantic details link, optional supported status, short location,
  and an alert action only after eligibility is known. Avoid interactive controls
  nested inside a card-wide link.
- Distinguish no campgrounds from no filter matches; offer clear filters in the latter.
- Keep description short with expand/collapse. Raw provider HTML is sanitized.
- Use absent metadata placeholders sparingly: omit decorative gaps, explain unknown
  requirements where they affect suitability.

Later full Explore layout:

```text
[Destination / area] [Date intent, optional] [Filters]      List | Map

23 campgrounds · filters applied                  Sort: Name
[Campground card]                 [map with same result set]
[Campground card]                 [selected marker/card]
```

On mobile, show the list first; open map as an alternate view with a selected-card
tray. Provide an explicit “Search this area” action after map movement, avoiding
silent result churn. Location permission is requested only after “Near me.” Rejection
returns to manual search. Map and list share IDs/filters/selection and have equivalent
navigation; loading, configuration failure, and missing coordinates keep the list usable.
Map clusters, geographic queries, and total counts require backend work. Campflare's
public map/home suggest the direction; detailed map interactions remain our proposal.

### 3.4 Campground details: support the decision and next step

Above the fold: park breadcrumb, campground name/location, concise description,
source link, and primary “Set an alert.” Secondary action: “View reservation site.”

- Show what is known about reservation/monitoring support, not an “Active” badge
  that could mean either metadata configuration or live monitoring.
- Mobile primary action can be sticky above safe-area/bottom navigation; ensure it
  does not obscure content or focused fields at zoom.
- Detail groups: overview/location, supported camping information, official rules
  link, and nearby alternatives within the same park. Amenities/equipment suitability
  appear only when reliable metadata exists.
- Match photos to the specific campground or explicitly identify them as regional
  imagery; retain licensing/attribution and a no-image fallback.
- Do not add ratings, prices, review counts, or “available now” badges from guesses.
- On an unsupported/unreservable location, explain the limitation and offer other
  campground choices or the official site instead of enabling a doomed save.
- Existing campground endpoint rejects unreservable metadata; resolve whether to
  expose browse-only details or exclude such entries consistently before the UI.

### 3.5 Alert builder: the central product experience

Use three short stages: **Stay → Preferences → Notifications & review**. Campground
selection happens before the builder; entering from My alerts starts with search.
Stage labels and a persistent summary explain progress, but avoid forcing a fourth
step for a detail already known. Preserve fields when moving back.

```text
Set an alert                                     Stay • Preferences • Review
Upper Pines · Yosemite

When can you camp?
(•) Specific stay       ( ) Flexible window
[ Arrival ] [ Departure ]

Stay summary: two consecutive camping nights

[ Optional campsite preferences ]

                       Continue
```

**Date intent**

- Specific stay means the complete selected stay in one campsite. Derive minimum
  nights from arrival/departure; do not accidentally default an exact three-night
  trip to any one-night match.
- Flexible window means any consecutive stay of at least N nights inside the window.
  Use “Earliest camping night” and “Latest departure” or equally unambiguous labels.
- Always show a sentence preview: “Watch for at least 2 consecutive nights in one
  campsite between June 12 and June 16.” Examples use synthetic future dates in tests.
- Optional quick choices: next weekend or ±2 arrival days. Compute in the chosen
  campground timezone, let users edit, and show actual dates before saving. Ship only
  after date semantics are fixed; fixed holiday lists need locale handling.
- Reject past/impossible windows, checkout-before-arrival, and minimum nights longer
  than the available window. Enforce the same rules on the server.
- Treat dates as campground-local calendar dates, not UTC instants. Daylight-saving
  changes must not change the number of camping nights.
- Start with well-labeled native date fields. Evaluate a shared range calendar with
  selected range, month navigation, keyboard support, and typed-date alternatives
  once usability testing demonstrates benefit.

**Preferences**

- Default to any supported campsite type. Use real toggle buttons/checkboxes with
  pressed/checked state for Tent, RV, Cabin, Other; allow multiple selections.
- Present electric hookup as a requirement, not an unexplained technical filter.
- Explain that requirements narrow matches; never invent a probability estimate.
  Suggested relaxations can widen dates or reduce minimum nights, but must not suggest
  relaxing safety/accessibility or mandatory RV requirements.
- Accessibility, vehicle length, hookups, pets, and individual site numbers require
  per-provider metadata/capability work. Unknown is not “allowed” or “not available.”
- A campground search inside the builder uses the same debounced accessible behavior
  as public search, with eligible campground results. Avoid filtering a capped mixed
  response until only park hits remain; add an entity filter to search if needed.

**Notifications and review**

- Show a plain-language summary of place, date rule, required preferences, and delivery.
  Use expandable details rather than internal campground/provider IDs.
- Signed-out campers can configure first, then sign in to save. Resume the draft on
  return; cancelled login preserves it. Basic auth has no implied signup path.
- Pushover setup explains install/account/key steps, external cost, and why required.
  A saved key means configured, not verified or guaranteed operational.
- Preferred behavior: allow a deliberate “Save without notifications” choice with a
  clear reminder; do not silently create a monitoring-only alert. Confirm with users
  whether this choice causes more confusion than requiring notification setup.
- Add “Send test notification” only with a real server endpoint and user acknowledgement.
  Distinguish sent-to-provider from confirmed received on-device; avoid a fake checkmark.
- Primary action: “Start watching.” During save, disable duplicate submission and
  preserve the draft on failure. A duplicate response offers “View existing alert.”
- Completion: “You're watching Upper Pines,” summary, actual notification readiness,
  link to My alerts, and “Add another campground.” Use a small static celebratory
  illustration; never celebrate as though a booking happened.
- If beta access is required, show it before final save and preserve the draft through
  the access request. Verify actual policy enforcement/routes before designing around it.

### 3.6 My alerts: reassure, organize, and act

Replace the generic dashboard emphasis with “My alerts,” an obvious “New alert,”
and active/paused/ended filters. Search campground/trip labels locally only over a
fully loaded dataset; implement pagination accurately as datasets grow.

- Cards show campground/park, date rule, requirements, state, last check, and delivery
  readiness. One title link opens details; pause/delete are separate controls.
- Make states mutually understandable: Waiting for first check, Watching, Paused,
  Ended. Monitoring delayed/error is an operational overlay requiring server data.
  “No matches yet” describes results, not a failed monitoring state.
- Ended takes precedence over Active. Use campground-local departure boundary and
  reconcile actual worker lifecycle before presenting definitive ended behavior.
- Surface mutation errors near the card and allow retry. Preserve previous state until
  success or roll back an optimistic update; pending controls have accessible labels.
- Delete confirmation names the campground/dates; focus returns to a sensible item.
  Prefer pause for “I don't need messages right now.” Do not offer Undo for a hard-delete
  API unless a real restore strategy exists.
- First empty state explains how to get started; filtered empty state offers reset.
  Avoid sad/failure imagery for somebody who simply has not created an alert.
- Keep summary statistics secondary and accurate. A loaded subset is not the overall
  total, shared observations are not user-matching openings, and openings are not bookings.
- Future trip labels such as “Birthday weekend” help distinguish similar alerts.
  Trip groups, bulk pause, and archive require models/endpoints and warrant separate work.

### 3.7 Alert detail and reservation handoff

Lead with what the camper can do now. Display the alert's rule and status, then
matching observations as consecutive date blocks with campsite identity, check time,
and provider booking action.

- Initial booking link can use the existing campground metadata URL. Specific
  campsite/date links need provider adapters; never fabricate URL parameters.
- Use “View reservation site” when the destination does not preselect the site.
  Show campsite/date context alongside it so campers can find the opening there.
- Explain briefly that availability may change before booking; do not repeatedly
  interrupt actions with warnings or discourage the camper.
- A stale snapshot shows “Last observed…” rather than implying live verification.
  Automatic refresh updates in place; no forced navigation or losing selected cards.
- Offer supported filter editing. Date editing is separate backend work: move the
  user's subscription to a correct de-duplicated target, not mutate a shared target.
- Distinguish latest results from notification history. A real history records which
  match was sent, when, through which channel, and delivery outcome.
- “I booked a campsite” is optional user feedback in a later increment, followed by
  a deliberate pause action. Never infer a reservation from a link click.

### 3.8 Notification settings: make readiness concrete

Consolidate setup in one reusable experience with links from the builder/dashboard.
Show configured channel, relevant external setup instructions, masked credentials,
edit/remove actions, and test status once implemented.

The backend should expose safe capability/readiness summaries, never application
secrets. Distinguish no user destination, application channel unavailable, test
requested/sent/failed, and user-confirmed receipt. Existing Pushover high-priority
messages can bypass quiet hours; later preferences should explain and control urgency
with provider-appropriate behavior. Changes need backend delivery/settings support.

Longer-term channel decision: email reduces installation friction; browser push
can be convenient but needs permission and service-worker lifecycle handling;
Pushover fits existing/self-hosted workflows. Research deliverability, operating costs,
security, and user preferences before selecting the next channel. Do not ship dead
Email/SMS toggles as a promise of forthcoming support.

## 4. Visual and interaction system

- **Palette:** forest green for primary action, warm neutral surfaces, slate text,
  muted earth tones for secondary accents. Maintain measured contrast in both themes;
  do not pick final token values before checking real components.
- **Typography:** keep a readable sans-serif (current system stack or existing font),
  16px form text, clear heading hierarchy, comfortable line height. Avoid all-caps
  provider names and tiny status badges as the only status presentation.
- **Layout:** consistent page widths/gutters, 8px spacing rhythm, modest rounded
  cards, and intentional whitespace. Search and builder summaries align with content.
- **Images:** responsive, compressed, licensed, sized to prevent shifts. Lazy-load
  below-the-fold images; fallback backgrounds preserve layout.
- **Icons:** existing Lucide set with text for important actions. Label every icon-only
  control and keep dark-theme/status colors coherent.
- **Motion:** short, purposeful transitions for opening filters and success feedback;
  respect reduced motion. Avoid animated scenery competing with search.
- **Feedback:** skeletons resemble final content; background refresh is subtle;
  errors preserve entered work; success is announced with next action.
- **Mobile:** full-width primary controls, 44px target goal, safe-area padding, a
  builder layout that remains useful when the keyboard opens, and no nested scrolling
  traps. Test long campground names and text zoom instead of hiding them by truncation.
- **Accessibility:** semantics before ARIA patches. Reference [W3C combobox](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/)
  and [dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) patterns; map-only
  results and custom calendars require equivalent keyboard-accessible interactions.

## 5. Experience state matrix

| Surface       | Essential states                                                                                 | Recovery / next action                                                 |
| ------------- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| Search        | Idle, short query, debouncing, loading, results, none, failure.                                  | Suggestions, type more, clear, retry; Escape always works.             |
| Park list     | Loading, populated, empty park, filtered empty, list error, map unavailable.                     | Clear filters, retry list, continue with list.                         |
| Campground    | Loading, details, unknown metadata, unsupported, removed, network error.                         | Official site, other campgrounds, retry, return to results.            |
| Builder       | Draft, valid/invalid fields, auth required, setup required, saving, duplicate, failure, success. | Retain values, resume after detour, existing-alert link, retry.        |
| Notifications | Unconfigured, configured, unavailable host channel, testing, failed, sent, receipt confirmed.    | Setup/help, retry test, explicit save without notifications if chosen. |
| My alerts     | None, loading, populated, filtered empty, mutation pending/failed, paused/ended.                 | New alert, reset filters, retry, resume/edit/confirm delete.           |
| Results       | First check pending, no current matches, matches, stale observation, provider delay/error.       | Show honest status, supported edits, official booking link.            |
| Auth/access   | Basic login, Auth0 login/signup, cancelled/error, beta access pending.                           | Return to draft, retry, explore publicly; preserve intent.             |

## 6. Backend and data prerequisites

| Capability                     | Existing foundation                                          | Required before the corresponding UI                                                                                                            |
| ------------------------------ | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Exact/flexible overnight rules | Date window + minimum consecutive nights.                    | Define exclusive departure semantics, fix inclusive extraction, validate both ends and stay length; address existing saved-alert compatibility. |
| Matching results/counts        | Shared target snapshots, filter-aware notification matching. | Apply user requirements to result API with sufficient metadata; return matching blocks/counts consistently.                                     |
| Operational state              | Last successful check timestamp.                             | Safe check state/error/next-check metadata and provider cadence; distinguish delayed/no-match.                                                  |
| Eligible search                | Mixed name hits, limit 20; park metadata list.               | Entity/capability filtering and valid detail behavior for unreservable entries; consistent provider support.                                    |
| Full Explore                   | Name search + individual campground coordinates.             | Paginated browse/geographic filters, total counts, stable sort, coordinate handling, capability/metadata freshness.                             |
| Delivery readiness             | User key save + Pushover task.                               | Host capability summary, test endpoint/status, observable failures; distinguish provider accepted from device received.                         |
| Editing dates                  | PATCH only updates filters/active flag.                      | Subscription retargeting with ownership/de-duplication/duplicate handling; preserve history attribution.                                        |
| Richer filters                 | Type and electric matching, accessibility in DTO.            | Persist/expose required metadata, provider-specific filter capabilities, equipment/site catalogs and matching tests.                            |
| Multiple campgrounds           | One target per scan.                                         | Decide separate alerts versus trip group; atomic/best-effort bulk behavior, duplicate/conflict handling and request limits.                     |
| Alert history                  | Replaced latest snapshots.                                   | Notification events with timestamps, matched blocks, channels/outcomes, ownership and retention policy.                                         |
| Favorites/trip labels          | No reviewed endpoints/models.                                | Persisted user models or explicitly local-only favorites; grouping contract before presenting trip-wide controls.                               |
| Photos/amenities               | Description, coordinates, source URL.                        | Data source, rights, normalization, unknown handling, refresh process.                                                                          |

Do not mutate shared target dates to edit one user's alert. Resolve checkout
compatibility deliberately: existing inclusive windows may change meaning. Before
release, decide whether stored end dates represent last camping night or departure,
and use a migration/version rule where necessary rather than silently reinterpret them.

## 7. Prioritized backlog

Priority definitions: P0 = trust/usability prerequisite, P1 = core launch experience,
P2 = valuable expansion after validation, P3 = deferred idea. Effort is relative
(S/M/L), not a schedule commitment. “Backend” indicates contract/model/worker work,
not merely a frontend call to an existing endpoint.

| ID    | Feature / improvement                                                          | Priority | Effort | Dependency                                                               |
| ----- | ------------------------------------------------------------------------------ | -------- | ------ | ------------------------------------------------------------------------ |
| UX-01 | Accurate coverage/channel/cadence wording and capability-driven entry actions. | P0       | S–M    | Provider/auth/channel capability review.                                 |
| UX-02 | Overnight boundaries, stay validation, exact/flexible matching examples.       | P0       | M      | Backend/provider + saved-date compatibility.                             |
| UX-03 | User-filtered result blocks and accurate counts.                               | P0       | M      | Backend snapshot metadata/filter contract.                               |
| UX-04 | Shared accessible search; stale-response prevention and clear recovery.        | P0       | M      | Existing API; eligible entity filter may extend it.                      |
| UX-05 | Semantic navigation/controls and visible mutation errors.                      | P0       | S–M    | Existing frontend components.                                            |
| UX-06 | Discovery-led landing, nature palette, destination suggestions.                | P1       | M      | Accurate support data; approved licensed assets.                         |
| UX-07 | Task-oriented header, auth-aware actions, skip link/route focus.               | P1       | S      | Auth/capability policy.                                                  |
| UX-08 | Park list filtering, counts, stable sorting and map fallback.                  | P1       | M      | Existing full park list; eligibility decision.                           |
| UX-09 | Campground decision page with Set an alert / reservation site actions.         | P1       | M      | UX-01; metadata fallback.                                                |
| UX-10 | Responsive guided alert builder with supported preferences and summary.        | P1       | L      | UX-02, UX-04, UX-09.                                                     |
| UX-11 | Safe draft preservation and auth/access return flow.                           | P1       | M      | Builder route + verified access policy.                                  |
| UX-12 | Notification onboarding/readiness and deliberate monitoring-only option.       | P1       | M      | Host capability + product decision.                                      |
| UX-13 | Real test-notification journey and duplicate-alert resolution.                 | P1       | M      | Backend test/delivery endpoint; duplicate lookup.                        |
| UX-14 | My alerts state model, accurate pagination/totals, pause/delete feedback.      | P1       | M      | UX-03; operational state as available.                                   |
| UX-15 | Result cards with freshness, matching nights and booking handoff.              | P1       | M      | UX-02/03; existing metadata URL.                                         |
| UX-16 | Mobile, dark-theme, keyboard and low-bandwidth acceptance pass.                | P1       | M      | Every core screen.                                                       |
| UX-17 | Full Explore search with bookmarkable filters and complete result totals.      | P2       | L      | Backend browse/pagination/filter API.                                    |
| UX-18 | Synchronized map/list, Near me and Search this area.                           | P2       | L      | UX-17 + geospatial API/map delivery choice.                              |
| UX-19 | Flexible-date shortcuts and accessible range-calendar enhancement.             | P2       | M      | UX-02 + usability evidence.                                              |
| UX-20 | Additional notification channel (evaluate email/browser push).                 | P2       | L      | Delivery infrastructure/cost decision.                                   |
| UX-21 | Notification history and actionable monitoring diagnostics.                    | P2       | L      | Backend event/operational contracts.                                     |
| UX-22 | Edit dates and duplicate existing alert with prefilled draft.                  | P2       | M–L    | Retargeting and duplicate semantics.                                     |
| UX-23 | Favorites and session recents with privacy controls.                           | P2       | M      | Storage/ownership decision.                                              |
| UX-24 | Multiple campgrounds, trip names/groups and bulk pause.                        | P2       | L      | Group model and multi-target save semantics.                             |
| UX-25 | Provider-specific RV/accessibility/site-number filters.                        | P2       | L      | Metadata and matcher support.                                            |
| UX-26 | Rich campground imagery/amenities and nearby suggestions.                      | P2       | L      | Licensed data + geographic metadata.                                     |
| UX-27 | User-confirmed booking outcome and optional pause follow-up.                   | P3       | M      | Outcome model; no provider booking inference.                            |
| UX-28 | Search aliases/spelling relevance and unsupported-location request path.       | P2       | M–L    | Search/index changes + metadata workflow.                                |
| UX-29 | Campground date-availability preview before creating an alert.                 | P2       | L      | Bounded public API, provider budget, cache, matching/freshness contract. |
| UX-30 | Optional arrival-weekday preferences for flexible windows.                     | P2       | M–L    | Persisted weekday rule and admissible-start matching.                    |
| UX-31 | Small campground comparison shortlist.                                         | P3       | M      | Useful normalized metadata and shortlist storage decision.               |
| UX-32 | Group compatible openings into fewer, more useful notifications.               | P2       | L      | Per-user batching, event history, preferences, provider limits.          |

See [design review](design-review.md) for UX-29–32 behaviors, constraints, and
review questions. These additions do not expand the first-release scope.

Defer social feeds, badges/streaks, generalized AI trip planning, paid fast lanes,
and automatic reservation booking. They do not address the current core friction.

## 8. Delivery sequence and review gates

**Phase A — truth and interaction foundations.** UX-01–05. Align date semantics,
matching results, real coverage, and actionable state; repair shared search and
control/navigation issues. Verify with behavioral tests and concrete date fixtures.
Gate: no UI labels imply unsupported capabilities or mismatched openings.

**Phase B — one excellent end-to-end journey.** UX-06–16. Build the design tokens,
landing/search/park/detail experience, then guided alert/draft/notifications, then
My alerts/results. Ship vertical slices, not a palette refresh followed months later
by functional usability. Gate: public discovery → auth return → saved useful alert
→ booking handoff passes acceptance tasks on phone and desktop.

**Phase C — broad discovery and easier delivery.** UX-17–20, UX-28. Extend result
APIs before map/filter UI; research the next notification channel. Gate: complete
result sets, stable map/list/back navigation, clear operating cost and permissions.

**Phase D — advanced monitoring and organization.** UX-21–27. Add observability,
date edits, favorites/groups, richer suitability filters and feedback based on usage.
Gate: no invented delivery history/booking outcomes; advanced requirements remain
provider-aware and comprehensible.

Each phase updates the feature tasks/global checklist, relevant design docs, and
API codegen when contracts change. Plans remain proposed until reviewed; this session
does not schedule release dates, publish changes, or mark implementation complete.

## 9. Validation plan

Use synthetic data/recorded provider responses for engineering tests. Start with
scenarios that would fail in current behavior, including stale-query selection,
checkout-night inclusion, mismatched result counts, lost auth drafts, and controls
nested in navigation links.

- Component tests: keyboard search, every search state, clear/retry, campground
  filtering, accessible preference selection, builder progression/validation,
  duplicate handling, save errors, and pause/delete failure behavior.
- API/worker tests: overnight boundary/DST/leap-day/month/year transitions, matching
  counts vs shared snapshots, unsupported capabilities, auth ownership, retargeting,
  delivery failure/test state, and multi-target duplicates if that feature ships.
- End-to-end: signed-out discovery to resumed alert; existing-ready user quick save;
  expired/paused/no-results alert; missing notification channel; partial metadata;
  map absent; official-site handoff with accurate date/site context.
- Responsive: 320/390/768/1440px, long names, mobile keyboard/safe areas, 200% text
  scaling, high zoom, dark/light, reduced motion, touch and keyboard.
- Assistive technology: VoiceOver and another supported screen reader; manual focus
  audit. Automated accessibility scanning supplements manual tasks.
- Performance: compare input responsiveness/search request counts and page asset
  weight before/after; defer map and noncritical imagery. Set numeric budgets from
  real baseline/device/network measurements rather than fabricated timings.
- Quality workflows: `task fix`, `task lint`, `task check`, `task test`, applicable
  pre-commit hooks, and production frontend compilation. Run focused tests per slice;
  full checks before a PR. No application quality gates are claimed for this planning
  session because application code is unchanged.

Usability study: 5–8 campers perform park-to-alert, exact two-night stay, flexible
weekend, auth interruption, notification readiness, and booking handoff tasks. Record
completion/assistance, misunderstandings, time, and a brief confidence/ease rating.
Recruit separately rather than contacting people in this session. Include a camper
with mandatory equipment/access needs and keyboard/assistive-technology use.

Minimal optional funnel events: search initiated, destination selected, builder
stage completed/abandoned, auth return completed, alert saved/duplicate, notification
configured/test outcome, and reservation link opened. Avoid raw query/date/location
or personal/credential payloads. Study booking outcomes only via explicit feedback.

## 10. Decisions to settle before implementation

| Decision                  | Recommended starting point                                  | Alternative / remaining evidence                                                |
| ------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Primary experience        | Public discovery followed by guided alert setup.            | Existing users may need a shorter direct path; test both.                       |
| Builder container         | Dedicated responsive page with shared state.                | Small dialog for quick edits; avoid duplicating full flows.                     |
| Date model                | Exact stay + flexible window, departure exclusive.          | Preserve inclusive existing records only with explicit compatibility plan.      |
| Notification requirement  | Encourage readiness, allow deliberate monitoring-only save. | Require configuration if testing shows users consistently miss the distinction. |
| Next channel              | Research email and browser push; retain Pushover.           | Select based on audience/delivery/cost, not visual preference.                  |
| First map increment       | List-first park view/fallback; full map discovery later.    | Map-first is useful only with complete geographic result coverage.              |
| Multiple campground model | Separate alerts first; group later when needed.             | Atomic trip builder introduces persistence and partial-save complexity.         |
| Favorites                 | Session recents first; optional persisted favorites later.  | Local-only saves are simpler but need clear device-specific wording.            |
| Visual identity           | Forest/warm-neutral tokens and truthful outdoor imagery.    | Final palette/compositions require actual mockups and contrast review.          |
| Access/coverage           | UI follows verified runtime policy/capabilities.            | Documentation currently differs from code; resolve before presenting promises.  |

## 11. Planned design deliverables

The [implementation brief](implementation.md) now breaks the first release into
seven work packages with dependency gates, precise date examples, draft recovery,
and error behavior. The [responsive clickable wireframe](wireframes.html) covers
Home, sample destination search, park list/filtering, campground details, three
builder stages, an authentication detour, My alerts, and an opening layout.
It uses fictional places and local-only state; it creates no real alerts.

Full visual browser review, actual notification onboarding, complete empty/error/loading
state sheets, high-fidelity assets, and camper usability sessions remain future
work. DOM-level checks exercise prototype behavior but do not establish visual or
screen-reader quality. The wireframe is a design artifact, not application code.

PR preparation includes limited Chrome spot-checks at 1440px desktop and 390px
mobile widths, with no horizontal overflow at either capture size. See the
[desktop home screenshot](screenshots/home-desktop.png) and
[mobile stay screenshot](screenshots/stay-mobile.png). These captures validate
example layouts only; they do not complete the device/accessibility audit.

```mermaid
flowchart LR
    A[Explore a park or campground] --> B[Choose campground]
    B --> C[Choose exact stay or flexible window]
    C --> D[Optional supported preferences]
    D --> E{Signed in?}
    E -- No --> F[Sign in and restore draft]
    F --> G[Notifications and review]
    E -- Yes --> G
    G --> H[Start watching]
    H --> I[My alerts and matching observations]
    I --> J[Open official reservation site]
    J --> K[Camper completes booking with provider]
```

## Constitution check

The plan preserves frontend/backend boundaries, shared-target de-duplication,
strict types, honest provider-backed availability, and task-based verification.
New data models/endpoints are proposed only for named user features. Each increment
needs tests and documentation; nothing in this research session changes the
application, secrets, external services, or production state.
