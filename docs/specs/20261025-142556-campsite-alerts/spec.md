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
- Group identical maximal consecutive check-in/check-out ranges into collapsible date sections with compact campsite rows. A site with separated openings appears in each relevant section; do not generate every possible shorter stay. Show unique matching-site and date-range counts, search and soonest-check-in/longest-stay sorting. Initially expand the first two ranges; searches reveal all matching sections.
- Keep scan dates, preferences and monitoring status above the results. Link directly to the full campground on the provider website from the page header, including when no sites match. Obtain that URL from Camply's existing campground endpoint without blocking availability when campground metadata is unavailable.

## Acceptance checks

Synthetic tests cover summary/direct delivery, multiple subscribers and filters, unchanged/reopened results, metadata persistence, filtered counts, legacy snapshots, separated stays, search, booking links and empty states. Inspect mobile/desktop light/dark results screenshots.
