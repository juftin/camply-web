# Search Map and List Interaction

This change supersedes the map-only panning behavior in the earlier [mapping specification](../007-open-source-explore-maps/spec.md), notably FR-009.

## Requirements

- Settled map zooms and pans filter the complete paginated Explore list, totals, and facets to visible valid coordinates; movement resets pagination to page one.
- Keep the chosen camera during list updates, sorting, pagination, and map collapse. Explicit query/filter changes frame their matching catalog locations.
- On an unfiltered initial visit, use an approximate IP-based regional extent without a device-location permission prompt. Explicit searches take precedence. Lookup failure falls back to catalog discovery, and a late response must not override user interaction.
- Markers show name, provider, entity type, and available region on hover and keyboard focus. Groups describe their place count. Click/keyboard activation retains existing selection actions.
- Under an active viewport filter, unmappable places are excluded. Clearing filters restores broad discovery; map errors preserve list access.

## Acceptance

Verify filtering before pagination/counts/facets, antimeridian and zero coordinates, invalid/partial bounds, movement debounce, camera preservation, IP success/failure/late response, and hover/focus cleanup. Existing detail/monitor behavior must keep passing.
