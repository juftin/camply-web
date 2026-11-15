# Research: Nights of the week

## Existing behavior and clarification review

Reviewed the feature against the constitution, current CLI contract, scan create/edit routes, saved models, result helpers, form, cards, and worker delivery paths. Scope, roles, dates, lifecycle, error handling, dependencies, and completion signals are clear. No clarification questions are needed. Existing authentication, provider behavior, scheduling, and telemetry remain unchanged.

## Decisions

1. **Decision**: Add `allowed_weekdays` to each subscription, using Monday=0 through Sunday=6. Store unrestricted preferences as null; expose all seven in responses. **Rationale**: Matches calendar weekday semantics and existing subscriber filters, supports SQLite and PostgreSQL, and preserves older scans without a backfill. **Alternative**: Adding days to target identity would duplicate shared provider polling.
2. **Decision**: Filter weekdays inside the existing database availability helper before consecutive grouping; reuse this for results, counts, detection, and delivery. **Rationale**: One matching rule avoids counting or alerting on excluded dates. The CLI already filters its eligible-date set before calling this helper. **Alternative**: Filtering only the form or only arrival dates would leave incorrect results and alerts.
3. **Decision**: Reject explicitly empty lists and invalid/noninteger day values; normalize duplicates and ordering. Omitted create means unrestricted; omitted PATCH preserves; all seven explicitly resets. **Rationale**: Avoids accidentally widening an empty user selection. **Alternative**: Empty-as-unrestricted is compact but ambiguous in a seven-button selector.
4. **Decision**: Validate feasibility against remaining dates when creating or modifying dates/night/stay criteria, before mutation; do not validate it for status-only changes. **Rationale**: Rejects impossible weekend three-night scans while allowing expired scans to be managed. **Alternative**: A schema-only validator cannot inspect merged PATCH state.
5. **Decision**: Use existing buttons with pressed state in the form, “Weekends” and “Any night” shortcuts, and a shared display formatter for card/detail summaries. **Rationale**: Adds accessible controls without new dependencies or redesigning dates. All seven days default selected; deselecting all leaves an explicit validation error.
6. **Decision**: Preserve exact-length CLI stays and minimum-length/maximal-block web stays. **Rationale**: This feature aligns eligible nights without changing either established stay contract.
7. **Decision**: Reuse worker outbox `current_payload` for distributed delivery as well as standalone delivery, loading the current scan target and rechecking target linkage. **Rationale**: Existing distributed delivery validates ownership and activity but not saved preferences; detection-time payloads can become stale after edits. Legacy unscoped notification calls retain their behavior.

## Constraints and verification

No new package or provider integration is required. Keep matching in the base database package, independent of optional server/worker dependencies. Migration must upgrade/downgrade populated SQLite data and compile for PostgreSQL; run PostgreSQL smoke if Docker is available. Synthetic tests must cover all 127 weekday subsets, date boundaries, impossible constraints, saved compatibility, target sharing, current alert matching, and UI selection/editing. Generate the OpenAPI client using `task api:generate` and verify with `task api:check`.
