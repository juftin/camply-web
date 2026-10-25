# Compact campground results

## User stories

- Review one collapsed campground summary instead of a page filled with scan cards.
- Browse a bounded list of matching campsites while retaining search, consecutive stays and booking actions.
- Stop showing sites when a successful provider check removes them or their remaining nights no longer meet the saved minimum stay.

## Requirements

- Group dashboard scans by provider and campground identity, with a scan count and the number of scans with openings. Preserve each scan's controls and dates inside the group.
- Preserve the upstream stay-date grouping, sorting, unique-site counts and campground provider link. Limit each date group to five campsites per page. Search all results, reset pagination for a new search and keep the current page valid after refreshed results disappear.
- Exclude past nights using the UTC date, restrict nights to the target's check-in/check-out range, then apply the minimum stay. Apply the same result filtering to detail and dashboard counts, including paused scans.
- Successful checks replace results, including empty checks. Provider failures preserve the last successful snapshot and its timestamp; elapsed time alone cannot prove that a campsite was booked.
- Retain last-checked information and explain that paused scans are not refreshed. Keep loading/error/empty states and notification destinations working.

## Acceptance checks

Verify provider-qualified grouping, expansion and existing controls; independent date-group pagination, complete-result search and refreshed result shrinkage; expired nights and consistent API counts; removal after empty checks and snapshot preservation on errors. Capture desktop/mobile and light/dark evidence with the local comparison gallery.
