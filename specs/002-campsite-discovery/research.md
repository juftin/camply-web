# Campsite experience research

Status: planning and research only. Reviewed October 8, 2026.

## Method and limitations

Reviewed public competitor pages, first-party FAQs/product updates, camply's
frontend components, API schemas/routers, and polling/notification implementation.
Competitor observations below describe documented features, not a completed
hands-on evaluation of authenticated flows. Campflare's map exposes little content
to text browsing, and Campnab's homepage is script-dependent. Screenshots, visual
comparisons, and moderated user testing remain future research tasks. Historical
posts demonstrate product patterns; current FAQs take precedence when features
have changed. Recommendations are design hypotheses, not measured user findings.

## Competitor patterns worth adapting

| Source                                                                                   | Observed pattern                                                                                                             | Proposed application to camply                                                                           |
| ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| [Campflare home](https://campflare.com/)                                                 | Destination search, suggested campgrounds, map entry point, and a clear free-access proposition.                             | Lead with search; offer starting points; make map discovery a later companion to a usable list.          |
| [Campflare FAQ](https://campflare.com/info)                                              | Explains notification behavior, cancellation of requests, and why longer consecutive stays are harder to find.               | Place small, relevant explanations next to date/stay choices and alert controls.                         |
| [Campnab FAQ](https://campnab.com/faq)                                                   | Park → campground → filters → dates; flexible arrivals; specific-site filters; explicit handoff to the reservation provider. | Use a guided alert builder with optional refinement and an explicit booking handoff.                     |
| [Campnab dashboard update](https://campnab.com/blog/improvements-to-the-dashboard)       | Scan summaries, visible state/actions, and links to alert records.                                                           | Make alert cards explain what is watched, whether monitoring is operating, and what action is available. |
| [Campnab scan naming](https://campnab.com/blog/new-name-your-campnab-scans)              | User-defined names help distinguish scans.                                                                                   | Consider trip names after core management works; needs persisted metadata.                               |
| [Campnab flexible-date announcement](https://campnab.com/blog/announcing-flexible-dates) | Early example of presenting date flexibility as a simple choice.                                                             | Separate exact stays from flexible windows; use current FAQ for present competitor behavior.             |

The inference: discoverability, understandable choices, and visible monitoring
state are stronger starting points than copying branding, pricing mechanics, or
adding many map layers. Camply can combine discovery with a friendly alert journey
while preserving its free, open-source, self-hostable product direction.

## Current camply journey: findings from source

| Area and evidence                                                                      | Finding                                                                                                                                                                                       | Product consequence                                                                                                                                     |
| -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `frontend/src/pages/Home.tsx`                                                          | Prominent signup CTA competes with search; email/SMS/push and broad coverage claims exceed reviewed implementation; no destination suggestions.                                               | First-time campers face a vague start and potentially misleading expectations.                                                                          |
| `frontend/src/components/Header.tsx`                                                   | Navigation emphasizes Providers, Ethos, and Contribute; desktop auth actions assume signup exists even though Basic mode is sign-in only.                                                     | Navigation reflects infrastructure/community organization more than camping tasks.                                                                      |
| `frontend/src/components/SearchBar.tsx`, `SearchDropdown.tsx`, `hooks/useSearch.ts`    | Debounced search retains previous data; no combobox/listbox semantics; Escape handling requires nonempty results; Enter requires prior arrow selection.                                       | Old destinations can remain selectable, and discovery is harder using assistive technology.                                                             |
| `frontend/src/pages/RecreationArea.tsx`                                                | Unfiltered campground list; navigation uses clickable divs; map/list selection is not connected.                                                                                              | Large parks are hard to browse; keyboard navigation is incomplete.                                                                                      |
| `frontend/src/pages/Campground.tsx`                                                    | Description/map dominate; alert action is called Monitor; no clear reservation handoff CTA or notification readiness information.                                                             | Users must infer the next step and whether notifications will work.                                                                                     |
| `frontend/src/components/ScanForm.tsx`                                                 | Separate search sends a request per change without debouncing/cancellation; selected campground shows internal IDs; type choices are clickable badges; no stay/window consistency validation. | Form feels technical, search responses can race, and essential controls lack standard keyboard behavior.                                                |
| `frontend/src/pages/Auth.tsx`, `App.tsx`, `Dashboard.tsx`                              | Sign-in navigates to dashboard; no persisted alert draft/return journey. `EarlyAccess.tsx` exists but is not routed in App and Dashboard does not apply an early-access guard.                | Sign-in interrupts alert intent; actual access policy needs verification instead of assuming the documented flow exists.                                |
| `frontend/src/pages/Dashboard.tsx`, `ScanCard.tsx`                                     | Stat totals use loaded scans, not total pagination; mutation errors are not displayed; switches/buttons are nested inside a navigation Link; ended and active badges may coexist.             | Counts and actions can mislead or behave unpredictably.                                                                                                 |
| `frontend/src/pages/ScanDetail.tsx`                                                    | Results are date badges without booking action; empty/error views do not distinguish monitoring states or retryable failures.                                                                 | Finding an opening does not produce a clear route to booking.                                                                                           |
| `frontend/src/components/MapComponent.tsx`                                             | Google Maps assumes a key; coordinate checks in pages use truthiness; markers are not navigable selections.                                                                                   | Maps need configuration fallbacks and support for valid zero coordinates.                                                                               |
| `backend/.../schemas.py`, `routers/scans.py`                                           | Create accepts one campground/window; PATCH edits filters/active flag but not dates; duplicate targets return 409; no server validation of date ordering/window-length consistency.           | Multiple campgrounds, editable dates, and richer validation need explicit backend work.                                                                 |
| `backend/.../routers/scans.py`, `worker/tasks/scanner.py`                              | List/detail return shared target results; counts are not narrowed by user filters. Scanner replaces result snapshots rather than retaining alert history.                                     | These results must not be labeled matching sites or notifications sent without changing the contract.                                                   |
| `backend/packages/providers/providers/recreation_gov/provider.py`                      | Availability extraction includes `start_date <= date <= end_date`, while UI/schema describe check-out.                                                                                        | Resolve overnight boundaries before promising exact-stay or flexible-window behavior.                                                                   |
| `backend/packages/worker/worker/tasks/scanner.py`                                      | Minimum consecutive stay, campsite types, and electric filtering are implemented for notification matching.                                                                                   | Existing checklist items overstate missing work; confirm supported behavior in tests rather than adding duplicate logic.                                |
| `backend/packages/providers/providers/__init__.py`, `frontend/src/pages/Providers.tsx` | Provider registry currently contains Recreation.gov; Providers page advertises several static integrations.                                                                                   | Coverage UI should be backed by capabilities, with planned integrations clearly separated.                                                              |
| `worker/tasks/notifications.py`, `notifications/pushover.py`                           | Missing user key skips delivery; missing application token logs and returns; outgoing push uses high priority and no readable dates in the message body.                                      | Saved configuration is not verified delivery. Notification readiness, precise match content, and eventual priority preferences need design/API support. |

Paths abbreviated with `backend/...` refer to `backend/packages/backend/backend`.
Findings are source-level observations, not claims of reproduced production incidents.

## Technical feasibility boundaries

Existing public APIs support name search, provider metadata, recreation-area
metadata/lists, and campground details. Existing authenticated APIs support one
campground per scan, scan snapshots, filter/pause edits, deletion, and saving a
Pushover user key. Campground details include an official booking URL.

Missing contracts include geographic/state/date search filters, search pagination,
provider capability summaries, photos/amenities/equipment metadata, favorites,
trip groups, date edits, verified delivery/test status, monitoring error details,
notification history, and user-confirmed booking outcomes. Broad filter categories
and map inventories should not be simulated by filtering only 20 text-search hits.

## Accessibility and notification references

- Use the [W3C combobox pattern](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/)
  as a reference for search behavior and focus relationships.
- Use the [W3C modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
  for builder focus management; a custom calendar also requires dedicated keyboard
  interaction and assistive-technology testing.
- Aim for 44px touch targets as a camply design choice. The [WCAG 2.2 minimum target
  criterion](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)
  uses 24px with exceptions; do not conflate those values.
- [Pushover licensing](https://pushover.net/licensing) describes a paid client
  license after its trial. Explain third-party costs before setup; avoid presenting
  the complete notification journey as cost-free unless another channel exists.

## Research still needed

The follow-up [implementation brief](implementation.md) checks notification-test
semantics against [Pushover's API](https://pushover.net/api): destination validation,
provider acceptance, and user-confirmed receipt are separate states. The
[design review](design-review.md) adds calculated token contrast and proposed
availability previews, arrival weekdays, comparisons, and grouped notifications.
These are planning/design findings, not a hands-on competitor assessment.

1. Walk both competitor flows on mobile and desktop with authorized test accounts;
   record search, date-selection, notification setup, and error recovery screens.
2. Observe 5–8 campers completing camply discovery/alert tasks, including beginners,
   RV users, a flexible-weekend camper, and someone using keyboard/screen reader.
3. Verify actual provider metadata, refresh intervals, closures, and reservation
   boundaries with synthetic fixtures and recorded provider responses.
4. Establish completion-time, abandonment, and comprehension baselines before
   measuring improvements. Recruiting/accounts are not part of this session.
