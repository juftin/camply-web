# Feature Specification: Shared Provider Cooldown, Pacing & Opt-In Proxy Rotation

**Feature Branch**: `provider-cooldown-proxy-rotation`

**Created**: 2026-11-27

**Status**: Draft

**Input**: Phase 4 (`T4.1.1`) — Shared per-provider cooldown/backoff, polite concurrency pacing, and lightweight opt-in BYO proxy rotation (`CAMPLY_PROXY_URLS`) that works across CLI, standalone, and distributed worker runtimes with zero extra infrastructure by default.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Shared Per-Provider Cooldown & Polite Concurrency Pacing (Priority: P1)

As a self-hoster or CLI camper running concurrent availability checks against the same booking provider, when one request hits a rate limit (HTTP 429), I want all other in-flight and queued requests to that provider to pause together until the cooldown window passes—and I want outgoing concurrency per provider to stay politely bounded by default—so I avoid thundering herds and IP bans without paying for or managing any proxy infrastructure.

**Why this priority**: Every deployment (CLI, standalone, and distributed workers) immediately benefits from eliminating thundering-herd retry amplification at zero cost and zero configuration. This is the core MVP that makes provider traffic polite and resilient by default.

**Independent Test**: Run multiple concurrent requests against a synthetic provider that returns HTTP 429 with `Retry-After` on the first request. Verify sibling requests wait until the shared cooldown expires before dispatching, verify in-flight concurrency never exceeds the configured per-provider cap, verify each logical request records at most one circuit-breaker outcome, and verify closing the client never deadlocks.

**Acceptance Scenarios**:

1. **Given** a provider running in direct egress mode (no proxies configured) with multiple concurrent requests in flight, **When** one request receives HTTP 429 with a `Retry-After` header (delta-seconds or HTTP-date), **Then** a shared per-provider cooldown deadline is set and all sibling concurrent and subsequent requests to that provider wait until the deadline expires before sending.
2. **Given** a provider receives HTTP 429 without a `Retry-After` header, **When** retry backoff is computed, **Then** the provider's configured exponential backoff delay sets the shared cooldown deadline (clamped to the configured maximum cooldown cap) rather than allowing concurrent requests to keep firing.
3. **Given** an active shared cooldown of 10 seconds for Provider A, **When** another request to Provider A receives a shorter 2-second delay, **Then** the shared cooldown deadline is not shortened; meanwhile requests to Provider B proceed unaffected.
4. **Given** a burst of 12 concurrent requests to the same provider with the default concurrency limit (4), **When** all requests execute concurrently, **Then** at most 4 requests are in flight upstream at any instant, and no request holds a concurrency slot while sleeping for retry or cooldown backoff.
5. **Given** an operator configures a positive minimum request interval for providers, **When** consecutive requests are dispatched to the same provider across one or multiple provider instances in the same process, **Then** request starts are spaced by at least the configured interval without blocking unrelated providers.
6. **Given** a request exhausts all 429 retries, **When** it raises a rate-limit error, **Then** the shared cooldown remains active for subsequent callers, the per-provider circuit breaker increments its failure counter exactly once for that logical request, and closing the client completes promptly without hanging.

---

### User Story 2 - Lightweight Opt-In BYO Proxy Rotation & Quarantine (Priority: P2)

As an operator running high-frequency scans who brings their own egress proxies (such as a single VPN proxy container, Tailscale exit node, self-hosted Squid/tinyproxy, Cloudflare WARP proxy, or a commercial rotating proxy), I want to supply a comma-separated list of proxy URLs via configuration so requests rotate round-robin across healthy proxies, temporarily quarantine misbehaving or blocked proxies, retry transparently via another healthy proxy, and never silently leak my host's real IP address.

**Why this priority**: Operators who hit strict IP-based rate limits or WAF blocks need an easy, vendor-agnostic egress escape hatch without coupling Camply to container orchestration, VPN management, or untrusted public proxy scrapers.

**Independent Test**: Configure two or more synthetic HTTP proxies via `CAMPLY_PROXY_URLS`, send requests against a synthetic upstream that returns 200, 429, 403, or drops connections on specific proxies, and verify round-robin selection, quarantine on failure, transparent retry on the next healthy proxy, bounded wait vs fail-fast exhaustion behavior, and strict refusal to fall back to direct egress.

**Acceptance Scenarios**:

1. **Given** `CAMPLY_PROXY_URLS` is unset or empty, **When** provider requests are made, **Then** proxy rotation is completely disabled with direct egress and unchanged behavior (including not retrying HTTP 403).
2. **Given** `CAMPLY_PROXY_URLS` contains multiple healthy HTTP or HTTPS proxy URLs, **When** sequential or concurrent requests are made, **Then** requests are distributed round-robin across healthy proxies.
3. **Given** a pool of healthy proxies where Proxy 0 returns HTTP 429 or HTTP 403 (WAF block) for Provider A, **When** a request is dispatched to Provider A, **Then** Proxy 0 is quarantined for Provider A for the configured duration (or positive clamped `Retry-After` on 429), and the request retries automatically via Proxy 1 without triggering a global cooldown across healthy proxies.
4. **Given** Proxy 0 fails with a proxy connection, timeout, or protocol error, **When** a request is dispatched, **Then** Proxy 0 is quarantined globally across all providers for the configured quarantine duration and the request retries via the next healthy proxy.
5. **Given** all configured proxies are quarantined and the exhausted policy is `wait` (default), **When** the soonest quarantine expiry is within the configured maximum cooldown wait, **Then** the request waits until that proxy exits quarantine and retries through it without ever sending a direct request; if the wait exceeds the cap, the request fails fast with a proxy-pool-exhausted error.
6. **Given** all configured proxies are quarantined and the exhausted policy is `fail`, **When** a request is dispatched, **Then** it fails immediately with a proxy-pool-exhausted error without waiting, without falling back to direct egress, and without tripping the provider's upstream circuit breaker.
7. **Given** `CAMPLY_PROXY_URLS` contains a malformed URL, unsupported scheme, or a SOCKS5 URL in an environment without SOCKS support installed, **When** configuration is validated, **Then** startup fails fast with an actionable, credential-free error rather than silently ignoring the proxy list or falling back to direct egress.

---

### User Story 3 - Credential Hygiene, Diagnostics & Optional Worker Metrics (Priority: P3)

As an operator supplying authenticated proxy URLs (`http://user:pass@host:port`) in CLI, standalone, or distributed deployments, I want proxy credentials to be strictly redacted from every log line, exception, object representation, and metric label while still having clear structured logs and optional distributed worker Prometheus counters so I can monitor rate-limit waits and proxy health safely.

**Why this priority**: Authenticated proxies contain secrets that must never leak into logs, Sentry traces, terminal output, or Prometheus series. Observability makes rate-limit pacing and proxy quarantine debuggable in production without adding optional dependencies to the base package.

**Independent Test**: Configure an authenticated proxy URL containing distinctive username and password tokens, trigger normal rotation, 429 quarantine, proxy connection failure, config validation error, and pool exhaustion, and assert the secret tokens never appear in logs, exception strings, `repr()`/`str()` outputs, or Prometheus metric names/labels. Verify base-only package installs work without optional monitoring or worker dependencies.

**Acceptance Scenarios**:

1. **Given** an authenticated proxy URL `http://alice:supersecret@proxy.example:8080`, **When** the proxy is logged, represented via `repr()`/`str()`, quarantined, or encounters a connection or validation error, **Then** neither `alice` nor `supersecret` appears anywhere in logs, exception messages, or representations; only a safe slot/endpoint label such as `proxy-0 (http://proxy.example:8080)` is emitted.
2. **Given** a provider enters a shared cooldown wait, rotates proxies, quarantines a proxy, or exhausts its proxy pool, **When** the event occurs in CLI, standalone, or distributed mode, **Then** a structured log entry records the provider name, event reason, safe proxy label (if applicable), and wait/quarantine duration.
3. **Given** a distributed worker with optional metrics enabled, **When** cooldown waits or proxy rotation/quarantine/exhaustion events occur, **Then** low-cardinality Prometheus metrics increment with provider and reason/outcome labels (never raw proxy URLs or credentials), while base package installations operate cleanly without any monitoring dependency.

---

### Edge Cases

- **Hostile or extreme `Retry-After` values**: Upstream returns `Retry-After: 86400` (24 hours) or a past HTTP-date or negative/non-numeric value. Negative or past values clamp to `0` (falling back to exponential backoff when non-positive or unparseable); oversized values clamp to `CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS` (default 60s) so workers cannot stall past task timeouts.
- **HTTP-date `Retry-After` headers**: RFC 9110 HTTP-date format (e.g., `Wed, 21 Oct 2026 07:28:00 GMT`) is parsed into delta-seconds relative to current UTC time before clamping.
- **Single-proxy pool (`len == 1`)**: Configuring a single BYO proxy (such as one Gluetun container or Tailscale exit node) works cleanly; on 429/403/connection failure that proxy is quarantined and `wait` vs `fail` exhausted policy governs retry timing without infinite tight loops or direct-IP fallback.
- **Duplicate or trailing-comma proxy entries**: `CAMPLY_PROXY_URLS="http://p1:8080, , http://p1:8080,"` trims whitespace, ignores empty segments, deduplicates identical proxy URLs while preserving order, and rejects entries that are empty overall by disabling proxy mode cleanly.
- **Ambient `HTTP_PROXY` / `HTTPS_PROXY` environment variables**: When `CAMPLY_PROXY_URLS` is explicitly configured, provider proxy transports ignore ambient environment proxy settings so requests never double-proxy or bypass the managed pool.
- **Cancellation during cooldown or pacing wait**: Cancelling a task awaiting cooldown, semaphore acquisition, or pacing sleep cancels cleanly, releases any held concurrency slot, and does not corrupt shared cooldown timestamps or proxy cursor state.
- **Multiple event loops in one process**: Sequential `asyncio.run()` invocations (such as Celery worker tasks or pytest async tests) reuse monotonic cooldown/quarantine timestamps safely without binding event-loop synchronization primitives across closed loops.
- **Existing provider-specific pacing**: Providers with existing per-instance request pacing (UseDirect, GoingToCamp, ReserveAmerica) continue to work unchanged; global `CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS` defaults to `0.0` so no artificial double-sleeping is introduced by default.
- **HTTP 5xx under proxy rotation**: Upstream 5xx server errors are retried with exponential backoff without quarantining healthy proxies, since 5xx indicates upstream server instability rather than egress IP blocking.
- **HTTP 403 in direct mode vs proxy mode**: In direct mode, HTTP 403 is not retried (preserving existing auth/permission error semantics); in proxy mode, HTTP 403 quarantines the egress proxy for that provider and retries via the next healthy proxy.
- **Client `aclose()` lifecycle**: Closing a provider client closes its direct transport and any lazily created per-proxy transports and reaps pending circuit-breaker tasks without clearing process-wide shared cooldown or proxy quarantine state.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST maintain a shared in-process cooldown gate per provider so that when any request in direct mode receives an HTTP 429 rate-limit response, all concurrent and subsequent requests to that same provider wait until the shared cooldown deadline expires before sending.
- **FR-002**: System MUST parse `Retry-After` headers in both numeric delta-seconds and RFC 9110 HTTP-date formats, clamp computed cooldown durations to `[0.0, CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS]`, and fall back to the provider's exponential backoff strategy when `Retry-After` is absent, non-positive, or unparseable.
- **FR-003**: System MUST ensure shared cooldown deadlines only move forward monotonically (`max(current_deadline, new_deadline)`) so concurrent shorter backoff responses cannot shorten an active longer cooldown, and cooldown state for one provider MUST NOT delay requests to any other provider.
- **FR-004**: System MUST enforce a configurable per-provider in-flight concurrency limit (`CAMPLY_PROVIDER_MAX_CONCURRENCY`, default `4`; `0` disables the cap) and MUST NOT hold concurrency slots while sleeping for retry backoff or cooldown waits.
- **FR-005**: System MUST support an optional per-provider minimum request-start spacing interval (`CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS`, default `0.0` / disabled) that spaces outgoing requests across concurrent tasks and provider instances targeting the same provider.
- **FR-006**: System MUST preserve exact circuit-breaker accounting: each logical provider request MUST record at most one success or failure against the provider's circuit breaker regardless of internal retries or proxy hops, and fast-fail `ProxyPoolExhaustedError` outcomes MUST NOT trip the upstream provider circuit breaker.
- **FR-007**: System MUST keep proxy rotation disabled by default when `CAMPLY_PROXY_URLS` is unset or empty, incurring zero proxy overhead and preserving existing direct-egress behavior (including not retrying HTTP 403 responses).
- **FR-008**: System MUST parse and validate `CAMPLY_PROXY_URLS` as a comma-separated list of proxy URLs, natively supporting `http://` and `https://` proxies (with optional `user:pass@` basic authentication) with zero extra dependencies, and supporting `socks5://` and `socks5h://` when optional SOCKS support (`socksio`) is installed in the Python environment.
- **FR-009**: System MUST fail fast with a clear, credential-redacted validation error when `CAMPLY_PROXY_URLS` contains a malformed URL, an unsupported scheme, or a SOCKS5 URL when `socksio` is unavailable, and MUST NEVER silently fall back to direct egress when `CAMPLY_PROXY_URLS` is non-empty.
- **FR-010**: System MUST select healthy proxies in round-robin order across the configured pool, ignoring ambient `HTTP_PROXY`/`HTTPS_PROXY` environment variables for managed proxy transports.
- **FR-011**: System MUST quarantine a proxy upon HTTP 429 (provider-scoped, using positive clamped `Retry-After` or `CAMPLY_PROXY_QUARANTINE_SECONDS`), HTTP 403 (provider-scoped, using `CAMPLY_PROXY_QUARANTINE_SECONDS`), or proxy connection/timeout/protocol error (global across providers, using `CAMPLY_PROXY_QUARANTINE_SECONDS`), and MUST retry the request via the next healthy proxy within the configured retry budget.
- **FR-012**: System MUST NOT quarantine a proxy on upstream HTTP 5xx responses, instead retrying with standard exponential backoff.
- **FR-013**: System MUST handle all-proxies-quarantined conditions according to `CAMPLY_PROXY_EXHAUSTED_POLICY`: `"wait"` (default) waits up to `CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS` for the soonest quarantine expiry before retrying (raising `ProxyPoolExhaustedError` if the wait exceeds the cap); `"fail"` raises `ProxyPoolExhaustedError` immediately; neither policy may ever send a request via direct egress.
- **FR-014**: System MUST redact credentials from all proxy URLs before logging, raising exceptions, formatting object `repr()`/`str()`, or emitting telemetry, identifying proxies solely by a safe slot/host label (e.g., `proxy-0 (http://proxy1:8080)`).
- **FR-015**: System MUST operate cleanly across sequential event loops and cleanly close all direct and per-proxy network resources plus pending circuit-breaker tasks during `aclose()` without deadlocking or leaking sockets.
- **FR-016**: System MUST emit structured log events for shared cooldown waits, proxy selection/quarantine, and pool exhaustion, and MUST provide a dependency-free observer hook in the provider layer so distributed workers can record low-cardinality Prometheus metrics without introducing optional dependencies into the base package.
- **FR-017**: System MUST work identically in base CLI, standalone runtime, and distributed Celery workers without requiring Valkey, Redis, Docker, or any external proxy orchestration service.

### Key Entities

- **Provider Transport Configuration**: Process-level environment settings governing per-provider concurrency cap, optional minimum pacing interval, maximum cooldown wait cap, opt-in BYO proxy URL list, default proxy quarantine window, and all-quarantined policy.
- **Provider Cooldown Gate**: In-process shared state per provider tracking the monotonic cooldown deadline, last request start timestamp, and event-loop-safe concurrency/pacing primitives.
- **Proxy Endpoint**: Immutable validated representation of one configured proxy containing its slot index, credential-free display label, scheme/host/port, and private connection URL excluded from string/repr serialization.
- **Proxy Pool**: In-process shared pool holding proxy entries, round-robin cursor, global and per-provider quarantine deadlines, and wait-vs-fail exhaustion semantics.
- **Transport Event**: Lightweight, credential-free telemetry event emitted on cooldown waits, proxy rotations, proxy quarantines, and pool exhaustion for structured logging and optional worker metrics.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Under a simulated burst of 10 concurrent requests to a provider where the first response returns HTTP 429 with `Retry-After`, 100% of queued sibling requests wait until the shared cooldown deadline expires instead of firing during the cooldown window.
- **SC-002**: Under a simulated burst of 20 concurrent requests with default settings, peak concurrent upstream requests to any single provider never exceed the configured concurrency cap (`4`), and total elapsed time for a single 4-request scan adds 0ms of artificial spacing delay.
- **SC-003**: With `CAMPLY_PROXY_URLS` unset (default), 100% of existing provider unit, VCR, and packaging tests pass unchanged with zero direct-mode behavioral regressions.
- **SC-004**: With a 3-proxy pool where 1 proxy fails with HTTP 429, HTTP 403, or connection error, 100% of affected requests succeed transparently on a healthy alternate proxy within the retry budget, and 0 requests are sent to the quarantined proxy until its quarantine window expires.
- **SC-005**: When all configured proxies are quarantined under either `wait` (exceeding cap) or `fail` policy, 0 requests ever leak over direct egress (host IP).
- **SC-006**: Across all logs, exception messages, string/repr outputs, and Prometheus metrics produced during validation, rotation, quarantine, and error scenarios with authenticated proxies, 0 credential substrings (`username` or `password`) appear anywhere.
- **SC-007**: Base-package import-boundary checks and isolated base-wheel installations succeed with 0 optional server, distributed, or Prometheus dependencies imported by `camply.providers`.

## Assumptions

- **In-process state is sufficient for v2**: Cooldown gates and proxy quarantine state are intentionally kept in-process (matching existing `ProviderCircuitBreaker` scope) so base CLI, standalone runtime, and Celery workers share one zero-infrastructure implementation without requiring Valkey/Redis. Cross-worker distributed cooldown synchronization via Valkey is explicitly out of scope and can be layered later if production telemetry shows multi-replica contention.
- **BYO proxies only**: Operators who want proxy egress supply their own HTTP/HTTPS (or optional SOCKS5) proxy URLs (e.g., a single Gluetun container, Tailscale exit node, Oracle Cloud free-tier Squid/tinyproxy, Cloudflare WARP, or a paid proxy service). Bundled VPN orchestration (OpenVPN/WireGuard/Gluetun lifecycle) and untrusted free public proxy scraping are explicitly out of scope.
- **No database schema changes**: All configuration is environment-driven and all cooldown/quarantine state is ephemeral in-memory runtime state, requiring no Alembic migrations or database tables.
- **Per-provider key matches existing circuit breaker**: Shared cooldown and per-provider proxy quarantine use the concrete provider class name (e.g., `RecreationGovProvider`, `ReserveCaliforniaProvider`, `WashingtonStateParksProvider`), matching `ProviderCircuitBreaker` so each distinct provider deployment is isolated.
- **Compatibility with existing provider pacing**: Existing per-instance pacing in UseDirect, GoingToCamp, and ReserveAmerica remains intact; the shared transport layer complements it with cross-instance cooldown coordination, bounded concurrency, and optional cross-instance pacing.
