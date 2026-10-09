# Design review and next feature opportunities

Status: proposed design choices. Use alongside the [clickable wireframe](wireframes.html)
and [first-release work packages](implementation.md). Sample colors/layouts are candidates,
not an approved brand system or completed accessibility audit.

## Proposed visual tokens

The wireframe uses a warm background and a forest action color in light mode,
and subdued green surfaces with a lighter action color in dark mode. The accent
should signal the next action, while status remains labeled in words.

| Role                | Light candidate | Dark candidate | Intended use                                                  |
| ------------------- | --------------- | -------------- | ------------------------------------------------------------- |
| Page background     | `#F7F6EF`       | `#14221C`      | Warm/open canvas, calm dark alternative.                      |
| Card/input surface  | `#FFFFFF`       | `#1E3026`      | Content and editable fields.                                  |
| Main text           | `#213B30`       | `#EEF3E9`      | Headings and body text.                                       |
| Secondary text      | `#56685E`       | `#B9C9BC`      | Supporting explanations, never the only status signal.        |
| Primary action      | `#235642`       | `#B8DBC2`      | Continue, Set an alert, Start watching.                       |
| Primary action text | `#FFFFFF`       | `#14221C`      | Label inside primary button.                                  |
| Soft surface        | `#E9F2E8`       | `#293F31`      | Stay summary and selected navigation.                         |
| Decorative border   | `#CCD4C9`       | `#597163`      | Card separation; not sufficient evidence of control contrast. |

Calculated text contrast for these opaque sRGB pairs:

| Pair                          | Light ratio | Dark ratio |
| ----------------------------- | ----------- | ---------- |
| Main text / page              | 11.19:1     | 14.61:1    |
| Secondary text / card         | 5.94:1      | 8.06:1     |
| Secondary text / soft surface | 5.18:1      | 6.57:1     |
| Primary button text / fill    | 8.46:1      | 10.94:1    |

Ratios were calculated from relative luminance; they do not test every rendered
component, opacity, state, or image overlay. Before adopting tokens, verify input
boundaries, focus rings, disabled controls, links, validation text, hover/selected
states, and actual light/dark surfaces. The light decorative border is subtle;
interactive controls may need a stronger border distinct from card borders.

## Layout and interaction review

- Home search remains ahead of the illustration on phones. Scenic imagery must
  not force a camper to scroll before they can start.
- Park cards answer “Which campground?”; campground details answer “What next?”
  Keep reservation/monitoring eligibility distinct from open inventory.
- Builder headings are questions a camper can answer. The stay summary appears
  alongside the form on desktop and remains readable on mobile.
- Preferences are optional; compare a three-stage builder against a compact
  Stay-and-review variant before freezing the design. Preserve a quick route for
  returning campers without discarding mandatory requirements.
- Mobile actions should live in the normal flow first. Add a sticky action only
  when visual/keyboard/zoom testing shows a benefit and no content obstruction.
- My alerts emphasizes the watched stay, last check, and delivery readiness; these
  are more actionable than prominent aggregate statistics.
- Real notifications should use a concise matched-stay summary and provider link.
  The existing message body needs readable matched dates rather than only site/type.

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
2. Configure an exact two-night stay. Explain which nights are included.
3. Switch to a flexible window and minimum nights; explain what counts as a match.
4. Choose a requirement, take the simulated sign-in detour, and confirm choices remain.
5. Consider monitoring-only. Explain whether a phone message will arrive.
6. Inspect My alerts, pause/resume the sample, and open the synthetic result layout.
7. Decide whether the result would make booking straightforward once connected to
   actual source data and official URLs.

Record confusion and preferred language before changing the prototype. Visual
browser/device, screen-reader, and real camper validation remain pending.
