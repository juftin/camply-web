# Design review and next feature opportunities

Status: proposed additions to the existing UI. Use alongside the
[clickable wireframe](wireframes.html) and [first-release work packages](implementation.md).
Preserving the current design is a scope constraint; individual improvements still
need camper testing and component accessibility review.

## Preserve-and-improve matrix

| Existing UI to preserve                                                  | Small improvement inside it                                                        | Verification                                                                 |
| ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Blue light/dark theme, system typography, Shadcn components              | Reuse current tokens and primitives; fix demonstrated contrast/focus defects.      | Compare screenshots in both themes; inspect actual states.                   |
| Centered Home hero, headline, SearchBar, feature cards, How It Works     | Add suggestions beneath search and correct unsupported claims.                     | Existing composition is recognizable; search reachable on phones.            |
| Header links, account/theme controls, mobile menu                        | Auth-aware actions, skip link, current-page/focus semantics.                       | All existing destinations reachable; keyboard/mobile navigation works.       |
| RecreationArea description/map and campground-list cards                 | Name filter, result count, semantic card links.                                    | No layout replacement; no matches has a reset action.                        |
| Campground header, Monitor action, overview/map, alternatives            | Clarify action wording and add official reservation URL.                           | The existing decision page remains recognizable.                             |
| Single ScanForm dialog, date/minimum fields, type chips, electric switch | Human place names, inline matching summary, validation, readiness, draft recovery. | Same entry points/order; no extra mandatory steps; focus/keyboard/zoom work. |
| Dashboard heading, statistics, settings, scan grid                       | Correct totals, per-card check/readiness, separate actions, visible errors.        | Stats remain; pause/delete never navigate or silently fail.                  |
| ScanDetail Overview and Availability cards                               | Matching date blocks, last observed time, provider link.                           | Existing cards convey a useful booking handoff.                              |

## Current visual tokens

Use `frontend/src/index.css` as the source of truth, including existing light/dark
variants. These are current values, not a proposed replacement palette.

| Role               | Light HSL           | Dark HSL            |
| ------------------ | ------------------- | ------------------- |
| Background / card  | `0 0% 100%`         | `222.2 84% 4.9%`    |
| Foreground         | `222.2 84% 4.9%`    | `210 40% 98%`       |
| Primary            | `221.2 83.2% 53.3%` | `217.2 91.2% 59.8%` |
| Primary foreground | `210 40% 98%`       | `222.2 84% 4.9%`    |
| Muted surface      | `210 40% 96%`       | `217.2 32.6% 17.5%` |
| Muted foreground   | `215.4 16.3% 46.9%` | `215 20.2% 65.1%`   |
| Border / input     | `214.3 31.8% 91.4%` | `217.2 32.6% 17.5%` |
| Radius             | `0.5rem`            | `0.5rem`            |

The wireframe approximates existing tokens and component shapes with standalone
HTML/CSS. It is not a pixel-perfect rendering of the React app. Review before/after
screenshots of the actual components for each implementation slice. Contrast ratios
for a different candidate palette would not validate these existing components;
measure actual input boundaries, text, focus, disabled/hover/selected/error states,
and both themes before claiming conformance. Repair specific defects in place.

## Interaction review

- Keep the centered home composition. Suggestions belong directly under search;
  a scenic hero, replacement headline, or new image system is unnecessary.
- Retain the alert dialog's compact field order. Its minimum nights and date-window
  summary should explain exact versus flexible matching without a mandatory mode
  selector or wizard. Consider progressive disclosure only if testing shows clutter.
- Reuse existing type-chip appearance with semantic controls; preserve all required
  preferences through sign-in/setup and show errors where they happen.
- Solve dialog height, focus return, keyboard, and zoom problems inside the existing
  primitive first. A dedicated page needs independent evidence and review.
- Keep dashboard statistics while making them truthful. Last-check/readiness labels
  supplement existing scan cards rather than replacing the dashboard's structure.
- Avoid sticky actions or navigation changes unless usability evidence supports them.
- Real notifications should use a concise matched-stay summary and provider link.
  The existing message body needs readable dates rather than only site/type.

## Additional opportunities beyond the first release

These extend the original backlog. They are proposals with explicit dependencies,
not additional requirements for the first release.

### UX-29 — Check dates before creating an alert (P2, large)

A read-only, campground-scoped availability preview is the most valuable next leap
from discovering a place to finding an actual stay. On details, choose dates and
see matching observed blocks, then either open the booking site or start watching
for future openings using the same choices.

Required work: a bounded public preview API, provider-rate budget, shared cache,
matching metadata, source/freshness timestamps, and abuse controls. Do not create
personal scans behind anonymous searches or call providers per keystroke. Cache
keys describe public inventory only, never user ownership/delivery credentials.

States: not checked, checking, observed matches, no observed matches, stale, provider
unavailable. Failure to check is not evidence that every campsite is booked.
Success scenario: choosing dates produces usable night blocks and a booking action;
no matches preserves the same dates/preferences for alert setup. Broader “available
now” map discovery requires complete geographic data and bounded date queries too.

### UX-30 — Arrival-day preferences (P2, medium–large)

Flexible campers may want to arrive only on Friday or Saturday. Provide optional
arrival-day chips after choosing a flexible window, with a sentence explaining the
rule. Do not introduce an ambiguous “Weekends only” checkbox: it could mean arrival
days, all occupied nights, or a fixed Friday–Sunday stay.

Required work: persist selected arrival weekdays and apply them to candidate stay
starts in the user's filter matcher, result blocks, and notifications. Existing
maximal open blocks need admissible starts identified; a long block containing a
Friday should not be rejected because it begins on Wednesday. Defaults remain any
arrival day. The summary should say, for example, “At least 2 nights, arriving Friday
or Saturday.” Exact-stay mode does not need a weekday filter.

### UX-31 — Small campground comparison shortlist (P3, medium)

Let an undecided camper compare two or three campgrounds in one park, showing known
location, descriptions, supported requirements, reservation source, and alert
eligibility. Keep it lightweight with a return to selection and a clear Set an alert
for each place; it is not a trip planner or review platform.

Required work: meaningful normalized metadata and a clear ownership/storage decision.
Current sparse metadata may not justify a comparison table yet; validate usefulness
before implementation. Unknown values must remain visible where they affect fit.

### UX-32 — Fewer, more useful notifications (P2, large)

When several suitable sites open during one check, offer one clear summary with the
matched stay and a route to see sites, rather than a burst of nearly identical messages.
Later let campers choose urgency/quiet-hour behavior without silently delaying
competitive openings. This is both delivery work and UX, not just a settings toggle.

Required work: per-user/channel batching identity, match-window deduplication, delivery
history, provider limits, preferences, and deterministic retry behavior. Group by
campground and compatible stay; do not combine different dates into a misleading
single opening. Reopened inventory still needs a meaningful re-alert policy.

## Review walkthrough

1. Enter a fictional destination, open its park, filter campgrounds, and choose Pine Creek.
2. Open the existing-style dialog; set a two-night window with minimum two.
   Explain which nights are included from the summary.
3. Extend the window without increasing minimum; explain flexible matching.
4. Choose a requirement, close/reopen the dialog, and confirm choices remain.
   Real sign-in/setup recovery remains an implementation acceptance task.
5. Consider monitoring-only. Explain whether a phone message will arrive.
6. Inspect Dashboard, pause/resume the sample, and open the synthetic result layout.
7. Decide whether the result would make booking straightforward once connected to
   actual source data and official URLs.

Record confusion and preferred language before changing the prototype. Visual
browser/device, screen-reader, and real camper validation remain pending.
