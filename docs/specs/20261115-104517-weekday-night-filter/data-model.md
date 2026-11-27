# Data model: Nights of the week

## UserScan

Add `allowed_weekdays: list[int] | None`, stored as nullable JSON on `user_scans`. Null means unrestricted and is the value for all pre-existing rows. Integers use Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6. A restricted value is sorted and duplicate-free; an explicit all-seven selection normalizes to null for storage. No empty list is accepted from user input.

The additive Alembic migration has no backfill and preserves all existing filters, identity, and target linkage. Downgrade removes only the new column. SQLAlchemy uses the same JSON type in both supported databases. Test populated upgrade/downgrade/re-upgrade and persistence after a new session.

## Interfaces and transitions

Creation omission becomes all seven; explicit nonempty lists are validated then normalized. Updates omit the field to preserve the saved value; all seven resets. Explicit null is invalid for submitted preferences, distinct from the storage sentinel. Responses always expose a nonempty list, including all seven for old rows.

When date/night/stay criteria change, validate the merged values against remaining dates before target creation or scan mutation. No current provider availability is needed. Status-only and unrelated edits bypass feasibility validation. Invalid changes preserve prior state; existing expired scans remain readable and pausable/resumable.

## Unchanged entities

`UniqueTarget` still uses provider, campground, start and exclusive end only. `ScanResult` remains the shared unfiltered observation. The outbox schema and top-level notification shape remain unchanged. New opening/summary metadata carries the originating target ID so distributed delivery can reject alerts queued before retargeting; older payloads without this metadata remain compatible and are revalidated against current dates and preferences. One subscriber's edit cannot narrow the shared snapshot or another subscriber's results.
