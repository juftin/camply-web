# Implementation Plan

Reuse the existing map viewport predicate for Explore search by moving shared geographic SQL helpers into `db/search_bounds.py`. Add optional validated west/south/east/north inputs to Explore, applying bounds before counts, facets, and pagination. No schema migration or dependency is needed.

Keep map membership/context independent of list bounds. ExploreMap reports the latest bounds at 150 ms intervals during movement and after it ends to SearchPage, which resets the list page and supplies bounds to its existing query. Listen to camera movement without requiring DOM event metadata; distinguish unchanged-camera resizes from navigation. Save the camera immediately for collapse/reopen. Explicit search/filter contexts discard prior bounds.

Resolve initial approximate coordinates through ipapi.co's documented browser HTTPS API using an isolated, credential-free request with a short timeout, TanStack Query caching, and no retries. Use a regional extent, preserve explicit links, and abandon initialization when the visitor interacts. Fail open to ordinary catalog discovery.

Use MapLibre's Popup with DOM text nodes for marker hover/focus details and remove popups/listeners with markers. Preserve click selections and keyboard actions.

Constitution check: public catalog discovery only, typed interfaces, existing Task workflows and monorepo boundaries, no migrations or speculative infrastructure. Behavioral regressions precede implementation; run frontend/backend tests, lint, type checks, and API generation/check.
