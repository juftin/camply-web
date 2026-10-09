# Campsite experience tasks

Planning-only session. Checked items below are research/planning deliverables,
not implementation. IDs reference [the prioritized plan](plan.md).

## Completed in this session

- [x] Research first-party Campflare and Campnab discovery/alert material; distinguish
      current FAQs from historical product announcements.
- [x] Audit Home, search, park/campground pages, alert form, auth/access, dashboard,
      results, map, API schemas/routers, provider date extraction, and notification worker.
- [x] Record limitations of text-based competitor research and source-only code findings.
- [x] Define camper journeys, requirements, acceptance scenarios, and proposed measures.
- [x] Design screen hierarchy, interaction/state behavior, mobile/accessibility needs,
      and proposed exact/flexible stay choices.
- [x] Map frontend proposals to existing APIs and backend/data prerequisites.
- [x] Prioritize backlog UX-01–28, delivery phases, review gates, and open decisions.
- [x] Link research/specification/plan from frontend guidance and global checklist.
- [x] Remove the initial application prototype after the session was clarified as planning.
- [x] Define seven first-release work packages with dependency gates, recovery rules,
      and concrete exact/flexible date acceptance examples.
- [x] Create a responsive clickable wireframe of the core journey using fictional
      sample data, with no API calls or application changes.
- [x] Document current light/dark theme and component constraints; define additional
      opportunities UX-29–32 without expanding the first release.
- [x] Constrain the first release to additions within the existing UI, preserving
      Home, navigation, blue theme, card layouts, Dashboard, and ScanForm dialog.
- [x] Capture and visually spot-check desktop home and mobile alert-dialog wireframes for
      PR review, confirming no horizontal overflow at those viewport sizes.

## Design validation before implementation

- [ ] Review checkout compatibility and saved-alert date model with project owner.
- [ ] Confirm deployed auth/early-access policy and provider/channel capabilities.
- [ ] Decide notification-required versus deliberate monitoring-only save behavior.
- [ ] Review the responsive wireframe visually on mobile/desktop and add complete
      empty/error/loading state sheets and actual notification onboarding designs.
- [ ] Audit current component contrast/focus and propose targeted fixes only where needed.
- [ ] Validate the clickable wireframe with campers, including planned auth and notification detours.
- [ ] Complete authorized hands-on competitor review and 5–8 camper usability sessions.
- [ ] Establish usability/performance baselines and choose approved analytics scope.

## Phase A: correctness and interaction foundations

- [ ] UX-01: align coverage, supported channels, auth CTAs and cadence wording with
      real capability/policy information. Verify unsupported options are never offered.
- [ ] UX-02: specify exclusive departure, exact-stay and flexible-window semantics;
      resolve existing inclusive records; validate client/server windows and night limits.
      Verify one-night, month/year boundary, leap-day and DST scenarios.
- [ ] UX-03: return user-filtered matching blocks/counts from shared snapshots.
      Verify alerts sharing a target but differing in requirements return different matches.
- [ ] UX-04: unify search with accessible keyboard semantics, current-query selection,
      debouncing, clear/retry and consistent entity eligibility. Verify race/empty/error states.
- [ ] UX-05: replace nonsemantic navigation and nested card actions, surface mutation
      errors, and give controls accessible labels. Verify pause/delete never trigger navigation.

## Phase B: the complete core journey

- [ ] UX-06/07: add supported suggestions and accurate copy to the existing Home;
      improve auth-aware actions/focus inside the existing Header. Preserve theme,
      hero, sections, and navigation. Verify with before/after screenshots.
- [ ] UX-08/09: add filtering/counts to existing park lists and clearer actions to
      existing campground cards/pages, preserving layout.
      Verify missing metadata, unsupported locations, map failures and back navigation.
- [ ] UX-10: enhance shared ScanForm dialog with date validation, semantic preference
      controls, and plain-language summary, keeping current fields/order/actions.
      Verify viewport/focus behavior and full-window vs partial-stay explanations.
- [ ] UX-11: preserve validated drafts through auth/access detours without credentials
      in browser storage. Verify success/cancel/error return journeys in both auth modes.
- [ ] UX-12: implement clear channel onboarding/readiness and agreed save-without-
      notifications behavior. Verify configured does not imply tested or operational.
- [ ] UX-13: implement actual notification test support and duplicate-alert resolution.
      Verify provider acceptance vs device acknowledgement, failure and existing-alert link.
- [ ] UX-14: enhance existing Dashboard/ScanCard status/actions and accurate totals.
      Verify waiting/watching/paused/ended states and failed update/delete recovery.
- [ ] UX-15: implement matching night blocks, freshness and official booking handoff.
      Verify result labels and destination URLs; do not infer booking completion.
- [ ] UX-16: complete keyboard/screen-reader, mobile/zoom, dark-theme, reduced-motion,
      keyboard-open, partial metadata and low-bandwidth acceptance tasks.
- [ ] Run focused behavioral tests, then task fix/lint/check/test and applicable hooks
      before a PR; regenerate API types and update docs after contract changes.

## Phase C: expanded discovery and delivery

- [ ] UX-17: implement complete server-side browse/search filters, pagination, counts,
      stable sorting and URL state. Verify filtering is not limited to autocomplete hits.
- [ ] UX-18: implement synchronized map/list, geographic queries, Near me and explicit
      Search this area. Verify permission rejection, map config failure and keyboard parity.
- [ ] UX-19: validate flexible-date shortcuts and range-calendar usability; ship only
      with correct overnight behavior and accessible typed-date alternative.
- [ ] UX-20: research/choose next notification channel and implement real delivery,
      permissions/preferences and setup. Verify failure/retry and operating costs.
- [ ] UX-28: improve query aliases/spelling and unsupported-location request recovery.

## Phase D: monitoring and organization

- [ ] UX-21: persist notification history and expose actionable monitoring diagnostics.
- [ ] UX-22: implement ownership-safe date retargeting and prefilled duplicate drafts.
- [ ] UX-23: implement recents/favorites with explicit storage/privacy controls.
- [ ] UX-24: implement trip names/groups, multiple campground save semantics and bulk pause.
- [ ] UX-25: implement provider-specific suitability/equipment/accessibility/site filters.
- [ ] UX-26: integrate licensed photos/amenities/geographic alternatives with unknown handling.
- [ ] UX-27: add optional user-confirmed booking outcome and deliberate pause follow-up.

## Additional opportunities after first-release validation

- [ ] UX-29: design bounded campground date-availability preview and seamless handoff
      of date/preferences to alert setup when there are no observed matches.
- [ ] UX-30: design arrival-weekday rules and matching admissible starts in flexible windows.
- [ ] UX-31: validate usefulness of a small campground comparison shortlist before building it.
- [ ] UX-32: design per-user grouping of compatible openings, urgency preferences,
      retry/deduplication behavior, and useful notification summaries.

These later tasks require independent feature designs/contracts and are not implied
implementation authorization from this planning session.
