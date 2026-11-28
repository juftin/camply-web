# Upstream provider campground and recreation-area search

Users of the Python provider interface can discover campgrounds and recreation areas directly
from every registered upstream provider without populating or opening a database.
Results have stable provider-scoped campground IDs, optional parent park IDs,
location fields, and public booking URLs usable by a future CLI.

`search(query="", *, state=None, recreation_area_id=None, entity_type=None, limit=50)` returns
at most 1–1000 results. Query whitespace is trimmed; blank queries browse the
catalog. State is a two-letter code, matched case-insensitively. Parent filters
are exact provider-native string IDs. Invalid arguments fail before network IO.
Catalog adapters match text case-insensitively against campground, parent, and
city names; Recreation.gov uses upstream relevance (including nearby matches).
Hidden/disabled areas are excluded. Visible areas remain discoverable without
bookable campgrounds; campground results exclude non-overnight and unbookable
entries wherever source metadata identifies them. HTTP, schema, and pagination errors propagate.

No CLI command, web integration, availability changes, or persistence changes.

Entity selection accepts `SearchEntityType.CAMPGROUND` / `"campground"`,
`SearchEntityType.RECREATION_AREA` / `"recreation_area"`, or `None` (default).
`SearchEntityType` is a string enum; `None` selects both. The `"both"` string
is rejected.
Typed results expose an explicit discriminator and native identity. Recreation
areas have no campground ID; campgrounds retain optional parent identity.
Uniqueness includes entity type. The result limit covers the combined list.
Area-only searches use park catalogs alone where available. ReserveAmerica
returns no recreation areas and makes no requests for area-only searches.
