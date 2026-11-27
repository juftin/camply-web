---
description: "Dependency-ordered implementation tasks for Shared Provider Cooldown, Pacing & Opt-In Proxy Rotation"
---

# Tasks: Shared Provider Cooldown, Pacing & Opt-In Proxy Rotation

**Input**: Design documents from `docs/specs/037-provider-backoff-proxy-rotation/`

**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/provider-transport-contract.md](contracts/provider-transport-contract.md), [quickstart.md](quickstart.md)

**Tests**: Required by Constitution Principle V (Automated Verification). Write tests before implementation within each story phase and verify they fail before making them pass.

**Organization**: Tasks are grouped by phase and user story (`US1` P1 MVP, `US2` P2, `US3` P3) so each increment can be implemented and validated independently.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel with peers that touch different files and have no incomplete prerequisites.
- **[Story]**: Maps user-story tasks to `US1`, `US2`, or `US3` in [spec.md](spec.md). Setup, Foundational, and Polish phases omit story labels.
- Every task references exact repository-relative file paths (`(new)` marks files created by this feature).

---

## Phase 1: Setup & Error Types

**Purpose**: Establish shared provider error types and verify clean baseline before building transport components.

- [ ] T001 Add `ProxyPoolExhaustedError(ProviderError)` with attributes `provider_name: str`, `retry_after: float | None = None`, and `pool_size: int = 0` and a credential-free message in `src/camply/providers/errors.py`.

---

## Phase 2: Foundational (Transport Configuration, Redaction & Observer Hooks)

**Purpose**: Core base-dependency-only configuration, URL validation/redaction, and zero-dependency observer registry required by all three user stories.

**CRITICAL**: No user story work begins until Phase 2 is complete.

- [ ] T002 [P] Write configuration, URL validation, SOCKS5/socksio gating, deduplication, credential redaction, and observer-hook unit tests in `tests/providers/test_proxy_rotation.py` (new), covering `CAMPLY_PROVIDER_MAX_CONCURRENCY` (`ge=0`, default `4`), `CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS` (`0.0 <= x <= 60.0`, default `0.0`), `CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS` (`0.0 < x <= 600.0`, default `60.0`), `CAMPLY_PROXY_URLS` (comma-separated, trimmed, empty segments skipped, exact duplicates removed in order, `repr=False`), `CAMPLY_PROXY_QUARANTINE_SECONDS` (`0.0 < x <= 3600.0`, default `60.0`), `CAMPLY_PROXY_EXHAUSTED_POLICY` (`"wait"` | `"fail"`, default `"wait"`), invalid schemes/hosts/ports, missing `socksio` error redaction, and observer isolation when a callback raises.
- [ ] T003 Create `src/camply/providers/transport_config.py` (new) implementing `ProviderTransportConfig` (`pydantic_settings.BaseSettings`, `env_prefix="CAMPLY_"`, `case_sensitive=False`, exact field constraints from `data-model.md`, `proxy_urls` with `repr=False`), frozen `ProxyEndpoint` (`index`, `scheme`, `host`, `port`, `label` formatted as `proxy-{index} ({scheme}://{host}[:{port}])`, private `_raw_url` with `repr=False`, `__str__`/`__repr__` returning `self.label`), `redact_proxy_url(raw_url: str) -> str`, `parse_proxy_urls(...)` validating `http`/`https`/`socks5`/`socks5h` and checking `importlib.util.find_spec("socksio")` for SOCKS schemes, frozen `TransportEvent`, and `register_transport_observer` / `unregister_transport_observer` / `emit_transport_event`.

**Checkpoint**: Configuration validation, credential redaction, and observer hooks pass unit tests with zero optional dependencies.

---

## Phase 3: User Story 1 — Shared Per-Provider Cooldown & Polite Concurrency Pacing (Priority: P1) MVP

**Goal**: Eliminate 429 thundering herds across concurrent requests to the same provider, support numeric and RFC 9110 HTTP-date `Retry-After` headers with bounded clamping, cap per-provider in-flight concurrency, and allow optional per-provider minimum request spacing while preserving circuit-breaker accounting and clean `aclose()`.

**Independent Test**: Run `tests/providers/test_provider_cooldown.py` and `tests/providers/test_base_provider.py` to confirm sibling concurrent requests wait together on a shared 429 cooldown, Provider B is unaffected by Provider A's cooldown, in-flight concurrency stays `<= CAMPLY_PROVIDER_MAX_CONCURRENCY` without holding slots during sleep, pacing spaces request starts across instances, circuit breaker counts at most 1 outcome per logical request, and sequential event loops + `aclose()` never deadlock.

### Tests for User Story 1

- [ ] T004 [P] [US1] Create `tests/providers/test_provider_cooldown.py` (new) testing `parse_retry_after` (int, float, RFC 9110 HTTP-date, past HTTP-date, zero/negative, non-finite, oversized value clamped to `max_cooldown_seconds`, unparseable string), monotonic cooldown extension (shorter delay never shortens active longer cooldown), cross-provider isolation, sibling concurrent request pausing on HTTP 429, 429 fallback using `RetryStrategy.base_delay` / `max_delay`, persistence of cooldown after 429 retry exhaustion, bounded per-provider concurrency (`max_concurrency=4` and `0` unlimited) verifying slots are released before backoff sleep, optional `min_interval_seconds` pacing across multiple instances of the same provider, `asyncio.CancelledError` slot cleanup, and sequential `asyncio.run()` event-loop safety.
- [ ] T005 [P] [US1] Add regression assertions in `tests/providers/test_base_provider.py` verifying direct-mode `RetryTransport` shares cooldown across two instances of the same `BaseProvider` subclass, does not leak cooldown between standalone `RetryTransport()` instances, records exactly 1 circuit-breaker failure per exhausted 429 request, preserves non-retry on HTTP 403 in direct mode, and cleanly resets shared state via `BaseProvider.reset_transport_state()`.

### Implementation for User Story 1

- [ ] T006 [US1] Create `src/camply/providers/cooldown.py` (new) implementing `parse_retry_after(raw_header: str | None, *, max_seconds: float, now_utc: datetime | None = None) -> float | None` (delta-seconds + `email.utils.parsedate_to_datetime`) and `ProviderCooldownGate` with monotonic `_cooldown_until`, `_last_request_at`, loop-scoped `WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore]` / `asyncio.Lock`, `trigger_cooldown()`, `wait_for_cooldown()`, `acquire_pacing()` (releasing lock before sleep), `slot(wait_cooldown=True)` context manager (checking cooldown outside and inside semaphore, releasing semaphore in `finally`), structured debug/warning logs, `TransportEvent` emission, and `reset()`.
- [ ] T007 [US1] Integrate `ProviderCooldownGate` into `RetryTransport` and `BaseProvider` in `src/camply/providers/base.py`: accept optional `provider_name: str`, `cooldown_gate: ProviderCooldownGate | None`, and `max_cooldown_seconds: float` on `RetryTransport` (defaulting to an isolated local gate when constructed directly without one); fix 429 fallback backoff to use `self._retry_strategy.base_delay` / `self._retry_strategy.max_delay` clamped to `max_cooldown_seconds`; trigger shared cooldown on every 429 in direct mode (including final attempt exhaustion) without double-sleeping; add class-level `BaseProvider._cooldown_gates` registry and `BaseProvider.reset_transport_state()` reading `ProviderTransportConfig`.

**Checkpoint**: User Story 1 (MVP) is fully functional and independently verified; every deployment gets zero-config shared 429 cooldown and polite concurrency limiting.

---

## Phase 4: User Story 2 — Lightweight Opt-In BYO Proxy Rotation & Quarantine (Priority: P2)

**Goal**: Enable opt-in BYO proxy rotation via `CAMPLY_PROXY_URLS` with round-robin selection across healthy proxies, provider-scoped quarantine on 429/403, global quarantine on proxy connection/timeout/protocol errors, configurable `wait` vs `fail` all-quarantined handling, and a strict fail-closed egress guarantee (never falling back to direct egress).

**Independent Test**: Run `tests/providers/test_proxy_rotation.py` to confirm disabled-by-default zero overhead, round-robin dispatch across multiple proxies, transparent failover on 429/403/`ProxyError`/`ConnectError`/`TimeoutException`, no quarantine on upstream 5xx, single-proxy pool handling, `wait` policy waiting up to `max_cooldown_seconds` and failing fast when exceeding cap, `fail` policy raising `ProxyPoolExhaustedError` immediately without tripping circuit breaker, `trust_env=False` on proxy transports, zero direct-egress fallback, and complete socket cleanup in `aclose()`.

### Tests for User Story 2

- [ ] T008 [P] [US2] Expand `tests/providers/test_proxy_rotation.py` with `ProxyPool` and `RetryTransport` proxy-mode tests covering: disabled direct-mode pass-through when `CAMPLY_PROXY_URLS` is empty; round-robin selection across 3 healthy proxies; provider-scoped quarantine on HTTP 429 (honoring positive clamped `Retry-After` vs `quarantine_seconds`) and HTTP 403 while keeping that proxy healthy for another provider; global quarantine across all providers on `httpx2.ProxyError`, `httpx2.ConnectError`, `httpx2.TimeoutException`, and `httpx2.RemoteProtocolError`; automatic retry through next healthy proxy; no quarantine on upstream HTTP 5xx; single-proxy pool retry lifecycle; `wait` policy sleeping until soonest expiry when `<= max_cooldown_seconds` and raising `ProxyPoolExhaustedError` when `> max_cooldown_seconds`; `fail` policy raising `ProxyPoolExhaustedError` immediately without incrementing circuit breaker; hard invariant that `self._inner` is never called when proxies are configured; `httpx2.AsyncHTTPTransport` constructed with `trust_env=False`; and `aclose()` closing all created proxy transports and draining `_cb_tasks`.

### Implementation for User Story 2

- [ ] T009 [US2] Create `src/camply/providers/proxy.py` (new) implementing `ProxyEntry` (`endpoint`, `global_quarantined_until`, `provider_quarantined_until`, `quarantine_count`, `last_reason`, `quarantine_until(provider_name)`, `is_healthy(provider_name, now)`) and `ProxyPool` (`entries`, `quarantine_seconds`, `max_wait_seconds`, `exhausted_policy`, round-robin `_cursor`, `select(provider_name)` implementing `wait` vs `fail` exhaustion and raising `ProxyPoolExhaustedError`, `quarantine(index, provider_name=..., reason=..., duration=..., global_scope=...)`, `snapshot()`, `reset()`, credential-free `__repr__`, structured logs, and `TransportEvent` emission).
- [ ] T010 [US2] Wire `ProxyPool` into `RetryTransport` and `BaseProvider` in `src/camply/providers/base.py`: include `httpx2.ProxyError` in proxy-mode retryable transport errors; accept optional `proxy_pool: ProxyPool | None` on `RetryTransport`; lazily construct per-proxy `httpx2.AsyncHTTPTransport(proxy=endpoint.raw_url, limits=self._limits, trust_env=False)` in `self._proxy_transports`; never dispatch to `self._inner` when `self._proxy_pool` is active; route 429/403/connection errors through proxy quarantine and immediate rotation while keeping 5xx on exponential backoff without quarantining; do not increment circuit-breaker failures on `ProxyPoolExhaustedError`; close all transports in `self._proxy_transports` alongside `self._inner`, `super().aclose()`, and `self._cb_tasks` in `aclose()`; cache the process-wide `ProxyPool` on `BaseProvider` keyed by normalized proxy config signature and expose `BaseProvider.reset_transport_state()` to clear it; export `ProxyPoolExhaustedError` from `src/camply/providers/errors.py` (and `src/camply/providers/__init__.py` if appropriate).

**Checkpoint**: User Stories 1 and 2 both work independently; opt-in BYO proxy rotation fails closed and never leaks host egress IP.

---

## Phase 5: User Story 3 — Credential Hygiene, Diagnostics & Optional Worker Metrics (Priority: P3)

**Goal**: Guarantee zero credential leakage across logs, exceptions, `repr()`/`str()`, and metrics, and surface optional low-cardinality Prometheus metrics in distributed workers without adding any optional dependency to `camply.providers`.

**Independent Test**: Run `tests/providers/test_proxy_rotation.py`, `tests/worker/test_worker_metrics.py`, `task backend:imports`, and `tests/packaging/test_base_install.py` to confirm zero username/password leakage across all error and log paths, accurate Prometheus counters/histograms with low-cardinality labels in workers, and clean base-wheel operation without `prometheus_client`.

### Tests for User Story 3

- [ ] T011 [P] [US3] Add end-to-end credential-redaction tests in `tests/providers/test_proxy_rotation.py` using `http://alice:supersecret@proxy.example:8080` across `repr()`/`str()` of `ProviderTransportConfig`, `ProxyEndpoint`, `ProxyPool`, and `ProxyPoolExhaustedError`, captured `structlog` logs on selection/quarantine/exhaustion, validation `ValueError` messages, and re-raised proxy transport errors whose upstream message contains credentials.
- [ ] T012 [P] [US3] Add worker metrics observer tests in `tests/worker/test_worker_metrics.py` verifying `camply_provider_cooldown_waits_total{provider, reason}`, `camply_provider_cooldown_wait_seconds{provider}`, and `camply_provider_proxy_events_total{provider, event, reason}` increment when `emit_transport_event` fires, and asserting no proxy URL or credential label exists on any metric family.
- [ ] T013 [P] [US3] Add a base-package regression test in `tests/packaging/test_base_install.py` verifying that an isolated base-only wheel can import `BaseProvider`, validate `ProviderTransportConfig` with `CAMPLY_PROXY_URLS`, and execute cooldown/proxy transport logic without `prometheus_client`, `celery`, or `redis` installed.

### Implementation for User Story 3

- [ ] T014 [US3] Add exception-message credential scrubbing helper in `src/camply/providers/transport_config.py` and apply it in `RetryTransport` (`src/camply/providers/base.py`) whenever re-raising proxy transport errors so configured credential tokens never appear in raised exceptions or structured logs.
- [ ] T015 [US3] Define `PROVIDER_COOLDOWN_WAITS_TOTAL`, `PROVIDER_COOLDOWN_WAIT_SECONDS`, and `PROVIDER_PROXY_EVENTS_TOTAL` in `src/camply/worker/metrics.py` and register a lightweight observer callback via `register_transport_observer` at module initialization using strictly low-cardinality labels (`provider`, `reason`, `event`).

**Checkpoint**: All three user stories pass independently; Import Linter confirms `camply.providers.**` has zero optional dependencies.

---

## Phase 6: Deployment Forwarding, Documentation & Verification

**Purpose**: Expose the new optional environment variables in Compose deployment templates, update architecture/configuration/roadmap documentation, and run all project quality gates.

- [ ] T016 [P] Forward optional `CAMPLY_PROVIDER_MAX_CONCURRENCY`, `CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS`, `CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS`, `CAMPLY_PROXY_URLS`, `CAMPLY_PROXY_QUARANTINE_SECONDS`, and `CAMPLY_PROXY_EXHAUSTED_POLICY` (with matching defaults / empty fallbacks) to provider-executing services (`backend`, `worker`, `camply`) in `docker-compose.yaml`, `deploy/compose/docker-compose.yaml`, `deploy/compose/docker-compose.production.yaml`, and `deploy/compose/docker-compose.standalone.yaml`.
- [ ] T017 [P] Add commented examples for `CAMPLY_PROVIDER_*` and `CAMPLY_PROXY_*` settings in `docs/examples/.env.example` and `deploy/compose/production.env.example`.
- [ ] T018 [P] Document the shared provider cooldown, pacing controls, and opt-in BYO proxy rotation (`CAMPLY_PROXY_URLS`, supported schemes, Gluetun/Tailscale/Squid/WARP examples, fail-closed guarantee, and credential redaction) in `docs/operations/CONFIGURATION.md` and update the Concurrency and Pacing section in `docs/architecture/DESIGN_PROVIDERS.md`.
- [ ] T019 Run all verification commands from `docs/specs/037-provider-backoff-proxy-rotation/quickstart.md`: `task backend:imports`, `task backend:lint`, `task backend:check`, `task backend:test`, `task backend:packaging:test -- tests/packaging/test_base_install.py`, and `uv run --all-extras -- pytest tests/docs/test_docs.py -q`.
- [ ] T020 Register spec `037` in `docs/specs/index.md`, mark `T4.1.1` completed in `docs/CHECKLIST.md`, and mark Phase 4 `Rate Limiting` completed in `docs/PLAN.md` after all verification checks pass.

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (T001)
  └──▶ Phase 2 (T002, T003)
         ├──▶ Phase 3: US1 MVP (T004, T005 → T006 → T007)
         │      └──▶ Phase 4: US2 Proxy Rotation (T008 → T009 → T010)
         │             └──▶ Phase 5: US3 Redaction & Metrics (T011, T012, T013 → T014, T015)
         │                    └──▶ Phase 6: Compose, Docs & Verification (T016, T017, T018 → T019 → T020)
         └──▶ Note: T009 (proxy.py) and T015 (worker/metrics.py) touch separate files from T006/T007 and can overlap once Phase 2 completes.
```

### User Story Dependencies

- **User Story 1 (P1 MVP)**: Depends only on Phase 1–2 (`T001`–`T003`). Independently deployable and testable.
- **User Story 2 (P2)**: Depends on Phase 2 (`T003`) and integrates into `RetryTransport` after `T007` so direct cooldown and proxy rotation compose cleanly without merge conflicts in `src/camply/providers/base.py`.
- **User Story 3 (P3)**: Depends on Phase 2 (`T003`) for `TransportEvent`/redaction and Phase 4 (`T010`) for end-to-end proxy exception scrubbing tests (`T011`, `T014`). `T012` and `T015` (worker metrics) only depend on `T003`.

### Parallel Opportunities

| Phase            | Parallel Tasks                                                                                                                                                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Phase 3 (US1)    | `T004` (`tests/providers/test_provider_cooldown.py`) and `T005` (`tests/providers/test_base_provider.py`) can be written in parallel before `T006`–`T007`.                                                                                  |
| Phase 5 (US3)    | `T011` (`tests/providers/test_proxy_rotation.py`), `T012` (`tests/worker/test_worker_metrics.py`), and `T013` (`tests/packaging/test_base_install.py`) can run in parallel; `T014` and `T015` touch disjoint files and can run in parallel. |
| Phase 6 (Polish) | `T016` (Compose files), `T017` (`.env.example` files), and `T018` (`CONFIGURATION.md` / `DESIGN_PROVIDERS.md`) touch disjoint files and can run in parallel before `T019` and `T020`.                                                       |

## Implementation Strategy

1. **MVP First (Phases 1–3)**: Complete `T001`–`T007` to ship shared per-provider cooldown and polite concurrency limiting for every Camply deployment with zero proxy complexity. Validate at the Phase 3 checkpoint.
2. **Opt-In BYO Proxy Rotation (Phase 4)**: Complete `T008`–`T010` to add round-robin rotation, quarantine, and fail-closed exhaustion for operators who set `CAMPLY_PROXY_URLS`. Validate at the Phase 4 checkpoint.
3. **Credential Hardening & Optional Worker Metrics (Phase 5)**: Complete `T011`–`T015` to verify zero credential leakage, worker Prometheus metrics, and base-wheel isolation.
4. **Polish & Ship (Phase 6)**: Forward env vars in Compose, update docs/examples, pass all quality gates (`T019`), and update tracking docs (`T020`).
