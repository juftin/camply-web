# Data Model for CLI YAML Configuration

## Configuration file

A configuration contains a required integer `version`, an ordered, non-empty list of named searches, and an optional mapping of shared settings. The current release accepts `version: 2`. File order is the order of outcomes in a single-pass JSON response. The checked-in `docs/cli-yaml-config.schema.json` defines the portable object structure.

| Entity          | Fields and constraints                                                                                                                                                                                                                                                                   |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Shared settings | Optional notification channels, interval, weekdays, weekend selection, stay length, campsite types, electric and accessibility requirements, and RV length. Each uses the same validation as the corresponding search field, with RV length restricted here to an integer from 1 to 200. |
| Search          | Unique non-blank name, explicit provider, one or both target lists, paired date windows, optional campsite selectors, per-search overrides, and optional state file. At least one target list and one window are populated.                                                              |
| Date window     | One inclusive `start_date` and exclusive `end_date` in ISO calendar format. End follows start. Optional `days` and `weekends` override inherited filters independently. The union of eligible nights must accommodate the requested stay length.                                         |
| Prepared search | Search name, canonical provider ID and name, normalized target selectors, shared core `SearchRequest`, interval, resolved channel settings, and optional config-relative state path resolved for conflict detection. Construct all prepared searches before starting network work.       |

Field precedence is explicit date-range value for `days` and `weekends`, then explicit search value, shared setting, and built-in default. Preserve field presence through raw model validation. Explicit empty lists replace inherited lists, false overrides true, and an explicit null for search `rv_length` clears the filter. Other fields reject explicit null. Run provider capability checks on the resolved request. State paths belong to individual searches and may not resolve to the configuration file or another search's state path.

## Search outcome

Each single-pass search yields its name, canonical provider name, status, and list of serialized stays. An `ok` outcome may have no stays. An `error` outcome has no stays and a corresponding sanitized diagnostic. Stays use the current CLI JSON fields. Availability results and notification delivery outcomes are independent.

## Alert history

Each search owns its own set of previously observed stay identities, using the existing state-file format when persistence is configured. A stay identity includes provider, campground, campsite, arrival, and checkout.

| Event                             | History transition                                                                                                        |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Successful check                  | Replace observations with the current qualifying stays. Attempt alerts for newly observed stays on the selected channels. |
| Failed check                      | Preserve previous observations and skip availability alerts for that attempt.                                             |
| Successful check confirms closure | Remove the closed stay from observations. A subsequent opening can alert again.                                           |
| State file missing or unreadable  | Start with empty in-memory history. Warn for unreadable state. A write failure warns and retains in-memory history.       |
| Notification delivery fails       | Preserve the latest observations and emit a warning. Other channels and searches continue.                                |
