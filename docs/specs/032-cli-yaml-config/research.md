# Research for CLI YAML Configuration

## Decode YAML and validate inputs in two stages

**Decision** — Add PyYAML to the base distribution using the version already resolved in `uv.lock`. Use a CLI-local safe loader for one document, reject duplicate mapping keys before a mapping is constructed, and keep plain ISO dates as strings for validation. Interpret unquoted boolean values using the true/false forms. Validate the file structure with Pydantic v2 using strict types and forbidden extras. Parse verified calendar dates into `date` during preparation.

**Rationale** — The manifest already declares Pydantic and has PyYAML typing support. A local loader preserves the legacy flag path and keeps YAML resolver changes from affecting other code. PyYAML's standard safe loader silently overwrites duplicate keys and implicitly converts plain dates and values such as `on`. Format parser errors using line and column only. Format Pydantic errors from known field paths, indices, and controlled messages, since even a validation error's location may contain an arbitrary unknown key.

**Alternatives considered** — The unmodified safe loader loses duplicate-key information. Pydantic alone sees the decoded objects. A hand-written YAML parser would duplicate parsing and safety work.

## Resolve inherited values before semantic validation

**Decision** — Validate all declared values first, including unused defaults. Merge only fields explicitly present on the search and in `defaults`, then fill built-ins. Use Pydantic field-presence tracking to distinguish an omitted `rv_length` from an explicit null. Validate effective date windows, provider capabilities, notification settings, and resolved state paths across the batch before constructing clients.

**Rationale** — Applying model defaults before the merge would hide omissions and could turn a console-only override into inherited alerts. The existing request normalizer, provider capability checks, and environment-based notification configuration supply the CLI semantics. The Draft 2020-12 schema covers portable structure. Shared structural fixtures catch drift, with separate loader and runtime tests for duplicate keys, YAML scalar types, date ordering, name uniqueness, and provider-specific constraints. JSON Schema treats a mathematically integral number such as `10.0` as an integer, while the CLI must reject a YAML float for an integer setting.

**Alternatives considered** — Deep-merging lists would prevent `notifications: []` from disabling alerts. Making every optional field nullable would accept inputs outside the contract. Runtime schema validation alongside the models would duplicate validation without covering provider or credential checks.

## Share provider clients and keep search cycles independent

**Decision** — Run the batch in one existing foreground runner and event loop. Own one provider instance per canonical provider ID and one coroutine per search. Reuse target resolution and the shared availability check. Resolve targets on the first attempt and retry failed resolution on the next continuous cycle. Keep resolved targets for the watch, consistent with current foreground monitoring. Use the provider's own request-level pacing and retries. Close all created clients after the child searches finish or cancel.

**Rationale** — UseDirect, GoingToCamp, and ReserveAmerica pace requests or manage sessions with instance-local locks and timestamps. A shared instance maintains that pacing even when two searches use different aliases for the same provider. The retry transport owns HTTP backoff. The existing `monitor` propagates a failed cycle, so the file-mode scheduler needs a per-search error boundary and independent waits. Reusing the foreground runner keeps signal handling and suppresses raw provider logs.

**Alternatives considered** — A client per search can multiply request rates and sessions. Serializing whole cycles across the file would make slow providers delay unrelated watches. The web poller would add a service dependency to the base CLI.

## Preserve output and alert history

**Decision** — Configure logging once, reuse stay serialization, and collect one outcome per input search in single-pass mode. Use separate alert histories per search and record observations only after a complete successful check. Reuse the existing state-file format and delivery handling. Add search attribution at the terminal and alert presentation boundaries.

**Rationale** — The existing presence-based deduplication supports reopening alerts and optional local persistence. A failed check must leave observations intact. File-mode delivery warnings should identify the search without leaking credentials or raw state paths. Separating serialization from stdout emission lets the flag command retain its flat array and the batch emit a single ordered document.

**Alternatives considered** — Streaming individual JSON results would change the batch contract. A shared history would let one search suppress another's alerts. Treating transient notification errors as provider failures would misreport availability.
