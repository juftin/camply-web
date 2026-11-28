# UI contract: Area and selected-campground monitoring

Proposed extensions to the existing form, discovery, dashboard, results and admin views. Use the established components, responsive layout and theme conventions.

## Entry and selection

- Recreation-area details, Explore list entries and map selections offer “Monitor recreation area.” The scan destination picker distinguishes areas from campgrounds. Existing campground Monitor actions retain their meaning.
- An area draft displays provider/name and defaults to “All campgrounds,” with the full eligible count and text explaining that future eligible campgrounds are included automatically.
- “Selected campgrounds” displays searchable, paginated eligible choices with labeled checkbox controls, selected names/count and remove actions. Keep the draft selection in an area/provider-qualified ID map independent of the current page/query; do not select or deselect hidden items implicitly.
- A one-campground subset is valid and remains area-selected coverage. Explicitly selecting all current choices never changes the mode. No select-all-page control may imply complete area coverage.
- Existing unavailable selections appear with their last known name/ID and unavailable reason, remain removable, and cannot be newly selected. Distinguish waiting for choices, empty eligibility, query with no matches and choice-request failure; retry preserves the draft.
- Changing area/provider clears the old subset and starts that destination in all mode unless the user explicitly chooses a valid new subset. Switching all→selected requires deliberate choices; selected→all clearly states that future members are included. Cancel discards drafts, failed saves preserve them, and reopening loads current saved values.
- No eligible campground disables creation/coverage replacement with an explanation. Pure date/preference edits on unavailable saved coverage remain available. Conflict responses preserve the draft and offer reload/review rather than automatic overwrite.

## Dashboard and scan controls

Group by `(provider, destination_type, destination_id)`. An area group may contain both all and selected scans, each showing coverage mode/count, dates/preferences and active setting. Group summaries count saved scans with openings, not sums of overlapping campsite counts. A saved area scan has one card and one set of controls.

Show selected, eligible, unavailable and matching-campground counts with explicit labels; do not equate total area members with a fixed subset's monitored count. Pause/edit/delete keep existing keyboard names, confirmation, pending and failure behavior. Administration also shows one saved scan and links to each actual shared campground target rather than inventing one target for an area.

## Results and freshness

Branch destination metadata loading by destination type; unavailable metadata never blocks saved observations. The header identifies area, all/selected mode, dates, preferences and monitoring state, with the area provider link when known. Campground scans keep their campground header/link.

Reuse stay-date groups and five-site pagination. Each row shows campground name, site number/name, known attributes and correct campground/site booking destination. Keys, distinct counts and search operate on provider/campground/site identity; search covers campground name and site name/number across every loaded result and resets page positions. Separated dates never combine, and nights from different sites/campgrounds cannot form one stay.

Show successful/pending/failed campground coverage and per-campground last successful check. Area full-check time cannot imply the same freshness for all sites after a failure. No-matches text for partial coverage explicitly says some campgrounds remain unchecked or failed. Preserve retained observations as stale; successful empty results remove prior openings. Saved active preference, parent availability, paused/ended status and last coverage outcome remain distinguishable.

## Accessibility and browser acceptance

Cover desktop/mobile light and dark layouts using current breakpoints. Selection modes and checkbox controls have visible labels, keyboard operation and focus restoration. Announce query loading, selected count and validation errors without moving focus unexpectedly. Long campground names and selections wrap without horizontal overflow.

Browser scenarios cover both entry paths, all/subset creation, selections outside page one, selection search, invalid empty subset, area change/reset, failed saves, edit round-trip, unavailable choices, same site IDs in two campgrounds, partial coverage and booking/notification navigation. Snapshot additions follow the existing synthetic fixture and baseline workflow; inspection precedes baseline updates.
