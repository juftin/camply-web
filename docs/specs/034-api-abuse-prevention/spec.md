# Feature Specification: API Abuse Prevention

**Feature** · 034 API Abuse Prevention

**Created** · 2026-11-24

## User Scenarios & Testing

### User Story 1 · Use the hosted API through the frontend (P1)

A visitor browses campground information and, where configured, signs in and manages scans from the hosted frontend. The backend operator can reject requests that did not pass through an approved frontend gateway.

**Independent test** · Compare a request through the hosted gateway with one addressed directly to the backend under the protected deployment profile.

1. With protection enabled, a frontend request reaches the API and its existing authentication, invitation, administrator, and CSRF checks.
2. A direct request without valid gateway credentials receives a denial. This applies even if the request has a trusted-looking browser origin or valid user credentials.
3. A browser request to the frontend API from another site is denied at the gateway. Normal same-origin requests continue to work, including cookie login and bearer authentication.
4. A local or self-hosted direct deployment can keep using its bundled UI or its own reverse proxy. Infrastructure liveness and readiness retain their existing behavior.

### User Story 2 · Preserve service under excessive traffic (P1)

A visitor can browse and a signed-in user can manage scans while other clients exceed the usage budget for a particular operation.

**Independent test** · Drive controlled synthetic traffic against each operation class until it runs out of capacity. Retry as a second client and after the original window expires.

1. Public discovery has a separate budget from general reads. Login attempts and access requests have stricter budgets.
2. An authenticated user who exceeds their write, test notification, or provider sync budget receives a retry response before the protected operation runs. Identity remains consistent across sessions and networks.
3. An exhausted budget returns HTTP 429 and a retry delay. A separate client retains its own capacity. After the window expires, the original client can proceed.
4. Requests distributed among protected service instances consume the same budgets. If shared accounting becomes unavailable, protected requests return a temporary service error while infrastructure probes remain available.

### User Story 3 · Reject oversized API bodies (P2)

An operator can bound the resources the API spends reading and parsing request bodies. Valid requests within the documented limit continue using the existing schemas and validation.

**Independent test** · Send bodies immediately below, at, and above the configured application ceiling, including requests without a declared size.

1. A request that exceeds the size ceiling is rejected with HTTP 413 before application parsing or side effects.
2. Byte counting applies even when no body size is declared.
3. A normal login, access request, or scan edit reaches the corresponding handler.

### Edge Cases

- Requests to unknown API paths or API schema/docs cannot avoid the hosted provenance check.
- Only exact liveness and readiness paths with safe probe methods bypass that check. Operators restrict access to infrastructure endpoints at deployment ingress.
- Missing or malformed gateway client identity cannot create a caller-controlled rate bucket. Direct deployments use the trusted server peer or trusted-proxy configuration.
- Changing the address, session, text of the query, or resource identifier does not reset an authenticated account budget. Password login attempts are counted without trusting the submitted username.
- A standalone process can use an expiring memory store. Multiple workers require a shared store for combined limits.
- Traffic to many distinct nonexistent URLs must not cause metrics storage to grow with each new path.
- Deep Explore pages may exceed the pagination window. Existing filters let a visitor narrow the result set and reach the desired area or campground.

## Requirements

- **FR-001** · Protected deployments MUST reject API requests that lack valid server-to-server gateway credentials, including API documentation, schema, and unknown API paths. Exact liveness/readiness requests are exempt.
- **FR-002** · The hosted gateway MUST supply its credential server-side, derive client identity from its hosting platform, reject explicit cross-origin browser requests, and preserve existing end-user credentials and authorization behavior.
- **FR-003** · Local and self-hosted direct deployments MUST function without hosted gateway credentials. A deployment requiring gateway authentication MUST refuse to serve with missing or invalid gateway configuration or automatic shared-admin login.
- **FR-004** · Public or pre-authentication quotas MUST use a trusted network identity. Authenticated quota scopes MUST use the verified account identity, with independent budgets for the categories defined in the API contract.
- **FR-005** · Reaching a quota MUST return HTTP 429 with a positive HTTP `Retry-After`. Requests rejected on quota MUST be stopped before the associated expensive processing or side effect.
- **FR-006** · Protected distributed deployments MUST coordinate quotas across workers, expire counters, and return HTTP 503 with a retry delay during accounting outages. Infrastructure probes MUST continue working.
- **FR-007** · API request bodies MUST be capped at 128 KiB, counted as bytes, with oversized requests denied before application parsing even without a declared length.
- **FR-008** · Operators MUST have documented settings, default quotas, trusted identity assumptions, exposure constraints, rollout steps, and verification commands. Automated tests MUST cover hosted, direct, and interrupted-backend behavior.
- **FR-009** · HTTP request metrics MUST group requests by stable operation and method labels with bounded cardinality, including unknown paths and unsupported methods.
- **FR-010** · Explore MUST reject search offsets above 50,000 with HTTP 422 before running the search and advertise only browsable pages.

### Key Entities

- **Gateway credential** · Server-only proof that a request passed through an approved deployment.
- **Quota policy** · Operation category, client or account identity, budget, and counting window.
- **Quota counter** · Short-lived record of budget consumption for one policy and identity.

## Success Criteria

- **SC-001** · Protected end-to-end checks admit normal gateway requests and reject all tested direct requests, untrusted browser origins, and invalid gateway credentials. Both infrastructure probe routes continue to respond.
- **SC-002** · Every documented quota allows traffic up to its configured threshold, rejects the next counted request with a positive retry delay, and recovers after expiry. Two service instances enforce one combined quota.
- **SC-003** · Declared oversized bodies and oversized streamed data both return HTTP 413. Requests within the ceiling retain schema validation and handler behavior.
- **SC-004** · Normal local and authenticated workflows pass regression tests, and a simulated unavailable shared store yields HTTP 503 without running the protected work.
- **SC-005** · Requests that only differ by a resource ID or unknown URL aggregate under the same metrics labels. Standard probe metrics remain available.
- **SC-006** · Explore accepts a page at the last allowed offset and rejects any deeper page without issuing a search query.

## Assumptions

- The public website offers anonymous discovery. A script can still make requests to those public frontend URLs, so quota enforcement also applies through the gateway. A credential embedded in browser code cannot establish provenance.
- Hosted denotes an explicitly protected deployment behind the Pages gateway. Local Vite, standalone, and self-hosted reverse proxies continue to support direct deployments.
- Existing application authentication and authorization determine who may use private data and operations. Gateway credentials identify transport, and never grant user privileges.
- Infrastructure probes and metrics need private ingress or network restrictions where the service is internet-facing. Existing third-party provider polling limits are outside this feature.
- User-configurable ntfy servers remain supported. Hosted operators need network controls for these outbound requests, which can otherwise reach internal services. The request budgets only limit their frequency.
