# Implementation plan

1. Reuse scan cards inside native expandable campground groups on the dashboard. Count scans with openings rather than summing possibly overlapping campsite matches.
2. Retain the upstream date-grouped results component and paginate each group at five sites. Search the complete result set, reset each group to the first page on search changes, and clamp its pagination when results refresh.
3. Filter persisted nights to the current/future target interval before evaluating minimum stays. Keep worker snapshot replacement transactional and cover successful removal and failed refreshes with regressions.
4. Verify focused and repository checks, review snapshot comparisons and update architecture notes and the global checklist.

Constitution check: no dependencies, schema changes, provider calls from the UI or arbitrary availability timeouts. Existing polling remains authoritative for booked sites; the API also expires past nights at read time.
