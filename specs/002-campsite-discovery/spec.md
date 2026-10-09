# Camply: discovery to campsite alert

Status: proposed product specification. Planning only; no application changes.

## Product outcome

Make finding a campground and setting up a useful alert feel easy, reassuring,
and enjoyable. A new camper should understand what camply does, choose a place,
express when they can camp, and know whether they will receive notifications.
A returning camper should see monitoring status and reach the official booking
site with minimal effort.

Build on the existing UI: retain its blue theme, centered home hero, navigation,
card layouts, dashboard, and single-dialog scan creation. Make the current journey
more helpful through clearer choices and fewer mistakes. Broad redesigns are
outside this first pass.

## Assumptions

- Prioritize the community-facing web experience for new and returning campers,
  with phones as a primary device. Preserve self-hosted use.
- Browsing is public. Authentication is required when saving personal alerts.
- Camply remains free and open source; third-party notification costs are disclosed.
- Booking happens through reservation providers. Camply does not reserve inventory.
- Recreation.gov is the current reviewed provider; feature/coverage claims follow
  actual capability data rather than legacy CLI parity or static marketing lists.
- Proposals below are hypotheses pending usability testing. Pushover is the current
  implemented channel; additional channels are separate product decisions.

## Priority journeys

| Camper                  | Need                                                              | Successful experience                                                         |
| ----------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Knows the campground    | Watch a particular place for a family trip.                       | Search → details → exact stay → notification setup → saved alert.             |
| Knows the park          | Compare campground options without understanding provider jargon. | Search park → filter campground list → choose → alert.                        |
| Flexible weekend camper | Find any suitable stay in a date window.                          | Choose window/minimum nights → optional filters → review clear matching rule. |
| RV/trailer camper       | Avoid unusable openings.                                          | See supported equipment/site filters and metadata gaps before saving.         |
| Returning camper        | Confirm monitoring works and act on an opening.                   | Dashboard → current status/results → official reservation site.               |
| Unauthenticated camper  | Explore without commitment, then save an alert.                   | Configure draft → sign in → resume draft with no re-entry.                    |
| Self-hosted user        | Use available auth/notification integrations.                     | Capability-aware UI without unsupported signup or channels.                   |

## User-facing language

Keep existing navigation and familiar Dashboard/New Scan labels initially. Test
focused copy improvements such as “Set an alert” for Monitor and human place names
instead of internal IDs. Explain that a scan watches for openings and a notification
is a message. Do not require a global terminology migration. A campground contains
individual campsites; a park/recreation area contains campground options.

Describe a saved alert separately from a push message: an alert watches a place
and dates; a notification is a message about a detected opening. Availability is
observed at a particular time and can change before the camper books.

## Functional requirements

- **FR-01 Discover:** Search is the primary entry action; suggestions correspond to
  real supported searches. No signup required to explore.
- **FR-02 Search:** Accessible autocomplete, visible loading/empty/error states,
  retry/clear, and selection of only the current query's results.
- **FR-03 Browse:** Park pages have name filtering, supported filters, result counts,
  keyboard-accessible campground links, and recovery from missing maps/metadata.
- **FR-04 Understand:** Campground pages explain location, source, available metadata,
  alert eligibility, and official booking route without claiming live inventory.
- **FR-05 Configure:** Enhance the existing ScanForm dialog: one campground,
  date window/minimum nights, supported optional filters, clear matching summary,
  and notification readiness. Keep fields in one form.
- **FR-06 Preserve:** Draft survives dialog reopening, setup detours, and sign-in.
  Store no passwords or notification credentials in browser drafts. Reject invalid/unsupported drafts.
- **FR-07 Validate:** Client and server agree on overnight boundaries, valid future
  windows, minimum-stay limits, and timezone handling. Explain errors next to fields.
- **FR-08 Deliver:** Show saved, configured, tested, and operational notification states
  distinctly. Delivery testing needs a new API; saving a key does not imply testing.
- **FR-09 Confirm:** Success shows the watched place/dates and next actions. Duplicate
  alerts resolve to the existing item instead of making the camper start over.
- **FR-10 Manage:** The existing dashboard supports understandable statuses,
  consistent pause/resume, filter edits, explicit delete confirmation, failure feedback, and accurate totals.
- **FR-11 Act:** Results show observed matching date blocks, freshness, and a useful
  booking handoff. Snapshot results are distinguished from sent-notification history.
- **FR-12 Capability:** Hide or explain unsupported providers, filters, and channels;
  missing metadata is unknown rather than a negative feature claim.
- **FR-13 Preserve the UI:** Reuse existing page structures, Shadcn primitives,
  theme tokens, navigation, and ScanForm dialog. New copy/help/filter controls fit
  those components. No rebrand, replacement hero, alert route, or mandatory wizard.

## Nonfunctional requirements

- Mobile layout supports 320px-wide screens; larger touch targets, stable loading
  layouts, and no essential hover-only actions.
- Target WCAG 2.2 AA, with keyboard and screen-reader evaluation of every core flow.
  Do not imply formal conformance without an audit.
- Support light/dark themes and reduced motion; status has text as well as color.
- Discovery remains usable without a map, map key, photos, or location permission.
- Search input remains responsive; requests are debounced and cancellable or stale
  responses ignored. Maps load on demand.
- Preserve strict TypeScript/Python, existing query/client boundaries, and task-based
  quality workflows. Each increment receives meaningful regression tests.
- Collect only approved, minimal analytics; exclude search strings, precise trip
  dates/locations, credentials, and personal information from default event payloads.

## Proposed acceptance scenarios

1. A camper enters a park name, sees parks and campgrounds distinguished, opens a
   park, filters campground names, and reaches a valid campground using keyboard only.
2. Rapidly changing a query cannot navigate to an old result; Escape works during
   loading, zero matches, and error states; retry preserves the query.
3. Selecting an unreservable or unsupported campground explains eligibility and
   offers another choice instead of opening a builder that cannot succeed.
4. A two-night window with minimum two includes both nights and excludes checkout
   night. A longer window with minimum two describes flexible matching in the same
   form's inline summary; no extra stage or mode selection is required.
5. Signing in while saving returns to the same campground/date/filter draft.
6. A saved Pushover key shows configuration state; only an acknowledged test/delivery
   can show verified status. Monitoring without notifications is an explicit choice.
7. Pausing an alert never navigates away; failed mutations retain previous state and
   offer retry. An expired alert has one clear ended status.
8. A result that does not meet the user's saved filters is not labeled a matching
   opening. A stale observation is labeled with its check time.
9. The booking action opens the provider URL, with the campground/date/site context
   visible even when the provider cannot deep-link to a specific campsite.
10. Back navigation restores results/filter/scroll state. A map failure preserves
    the list. A notification setup detour preserves the alert draft.
11. Existing users recognize Home, campground details, Dashboard, and ScanForm;
    additions retain their visual identity and familiar navigation/actions.

## Success measures (proposed targets, not measured baselines)

- At least 80% of usability-study participants complete the core alert task without
  assistance; at least 90% correctly explain whether they will get notifications.
- Returning, notification-ready users create a simple campground alert in under
  30 seconds; new users complete within two minutes excluding external auth/setup.
- No observed stale-result selections, lost drafts, or action-triggered navigation.
- All accepted exact/flexible date examples yield the expected night blocks in tests.
- Core keyboard-only tasks pass; mobile primary actions remain visible with the
  software keyboard, safe areas, and 200% text resizing.
- Track discovery-to-builder, builder completion, notification readiness, and
  reservation click-through separately. Booking success is user-confirmed only;
  a click-through is not proof of a reservation.

## Out of scope for the first delivery

Automatic booking, paid alert tiers, user reviews/social feeds, native mobile apps,
a general itinerary planner, fabricated popularity/success scores, live inventory
across unscheduled campgrounds, and broad provider parity. Map search, email/browser
push, favorites, trip grouping, equipment metadata, and alert history are planned
candidates with explicit prerequisites in [the plan](plan.md).

See [research](research.md) for evidence and [tasks](tasks.md) for staged work.
