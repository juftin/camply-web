# Campsite summaries and results

## User stories

- As a camper, receive one summary per saved scan per availability check when new matching openings appear, with a link to that scan in Camply.
- As a local operator, opt into individual alerts linking to the booking provider.
- As a camper opening an alert, browse a compact list of matching sites, their attributes, consecutive stays, and booking actions.

## Requirements

- Summary mode is the default. Summaries count only newly opened, matching sites. Unchanged results do not send alerts; openings that disappear and return can alert again.
- Preserve paused/suspended/ownership delivery guards and shared-target polling.
- Configure the externally accessible Camply URL, including optional path prefix, on the worker. Direct mode preserves existing per-site delivery.
- Persist site names, types, electric and accessibility attributes alongside the latest availability snapshot. Apply identical filters to notifications, scan detail and dashboard counts.
- Group consecutive available nights into check-in/check-out ranges; omit blocks below the saved minimum stay. Never imply that separated blocks form one stay.
- Show freshness and warn that booking-provider availability can change. Keep the list usable on phones and provide search for large result sets.
- Preserve authentication on scan links. No provider requests from the results page.

## Acceptance checks

Synthetic tests cover summary/direct delivery, multiple subscribers and filters, unchanged/reopened results, metadata persistence, filtered counts, legacy snapshots, separated stays, search, booking links and empty states. Inspect mobile/desktop light/dark results screenshots.
