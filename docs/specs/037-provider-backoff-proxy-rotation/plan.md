# Implementation Plan: Shared Provider Cooldown, Pacing & Opt-In Proxy Rotation

**Branch**: `provider-cooldown-proxy-rotation` | **Date**: 2026-11-27 | **Spec**: [Spec 037](spec.md)

**Input**: Feature specification from `docs/specs/037-provider-backoff-proxy-rotation/spec.md`

## Summary

Upgrade Camply's shared provider HTTP transport (`src/camply/providers/base.py`) in two complementary, zero-infrastructure parts:

1. **Always-on shared per-provider cooldown & polite pacing (P1 MVP)**: Introduce an in-process `ProviderCooldownGate` keyed by provider class name so HTTP 429 responses (supporting both numeric and RFC 9110 HTTP-date `Retry-After` headers, clamped to `CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS`) pause all concurrent and subsequent requests to that provider together, preventing thundering herds. Add configurable per-provider in-flight concurrency limiting (`CAMPLY_PROVIDER_MAX_CONCURRENCY`, default `4`) and opt-in minimum start spacing (`CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS`, default `0.0`) with event-loop-safe primitives (`WeakKeyDictionary[AbstractEventLoop, ...]`) so sequential `asyncio.run()` Celery tasks and pytest loops never leak or deadlock.
2. **Lightweight opt-in BYO proxy rotation & quarantine (P2 & P3)**: Add an opt-in `ProxyPool` configured via `CAMPLY_PROXY_URLS` (disabled by default with zero overhead). Native HTTP/HTTPS proxies use `httpx2.AsyncHTTPTransport(proxy=..., limits=..., trust_env=False)` with zero new dependencies; SOCKS5/SOCKS5h URLs work automatically when optional `socksio` is installed and fail fast with a redacted error otherwise. Rotate round-robin across healthy proxies, quarantine failing proxies (provider-scoped on 429/403, global on `ProxyError`/connection/timeout errors), enforce a strict fail-closed egress invariant (`wait` vs `fail` exhausted policy; never fall back to direct egress), redact credentials everywhere, and expose low-cardinality distributed Prometheus metrics via a base-layer observer hook.

See [research.md](research.md), [data-model.md](data-model.md), and [contracts/provider-transport-contract.md](contracts/provider-transport-contract.md).

## Technical Context

**Language/Version**: Python `>=3.11` (3.14 default for development, CI, Docker, and releases; verified on 3.11 and 3.14)

**Primary Dependencies**: Existing base dependencies only — `httpx2==2.16.2`, `pydantic==2.14.3`, `pydantic-settings==2.16.3`, `structlog==26.1.0`, and Python stdlib (`asyncio`, `email.utils`, `importlib.util`, `time`, `urllib.parse`, `weakref`). Optional `prometheus-client` used exclusively in `camply.worker.metrics` via observer registration. No new base or optional dependencies added to `pyproject.toml`.

**Storage**: N/A — all configuration is environment-driven; cooldown and proxy quarantine state is ephemeral in-process memory. No Alembic migrations or database schema changes.

**Testing**: `pytest` + `pytest-asyncio` / `anyio` unit and concurrency tests with mocked `httpx2.AsyncHTTPTransport` and synthetic HTTP responses; existing provider VCR/registry tests; worker Prometheus metrics tests; Import Linter (`task backend:imports`); isolated base-wheel tests (`tests/packaging/test_base_install.py`).

**Target Platform**: Linux, macOS, and Windows base CLI (`camply`), standalone runtime (`camply serve`), and distributed Celery workers (`camply serve worker`).

**Project Type**: Python monorepo package (`src/camply/`) with shared provider layer (`camply.providers`), worker instrumentation (`camply.worker`), Docker Compose templates (`docker-compose.yaml`, `deploy/compose/`), and VitePress docs (`docs/`).

**Performance Goals**: Zero added latency for default direct-mode single scans (concurrency cap `4` covers typical Recreation.gov multi-month bursts, `min_interval_seconds=0.0`); O(N) scan over small BYO proxy lists (typically 1–20 entries) with microsecond selection overhead.

**Constraints**: Strict Import Linter compliance (`camply.providers.**` MUST NOT import `prometheus_client`, `celery`, `redis`, `fastapi`, `sentry_sdk`, or `camply.worker`); 100% backwards compatibility with existing `RetryTransport._inner` test seams when proxies are disabled; zero credential leakage in logs/exceptions/reprs/metrics; zero silent direct-IP leaks when `CAMPLY_PROXY_URLS` is non-empty; clean `aclose()` socket and task cleanup.

**Scale/Scope**: Applies uniformly to all 26 registered providers across all 4 provider families (`RecreationGovProvider`, `UseDirectProvider`, `GoingToCampProvider`, `ReserveAmericaProvider`) through `BaseProvider` and `RetryTransport`.

## Constitution Check

_GATE: Evaluated before Phase 0 research and re-checked after Phase 1 design. All five principles pass with zero exceptions._

| Principle                                  | Pre-Design & Post-Design Audit                                                                                                                                                                                                                                                            | Status |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| **I. Reliability & Precision**             | Shared per-provider cooldown eliminates rate-limit amplification; bounded wait cap (`60s` default) keeps scans below the 90s scanner timeout; proxy quarantine routes around blocked egress IPs without masking upstream availability data.                                               | PASS   |
| **II. Type Safety & Static Analysis**      | Strict `pydantic-settings` config, frozen `ProxyEndpoint`/`TransportEvent` dataclasses, full type annotations compatible with `mypy` (`python_version = "3.11"`), `ruff`, and NumPy-style docstrings.                                                                                     | PASS   |
| **III. Modern Workflow & Automation**      | All checks run via root `Taskfile.yaml` (`task backend:test`, `task backend:lint`, `task backend:check`, `task backend:imports`, `task backend:packaging:test`). Zero new dependencies or external services required.                                                                     | PASS   |
| **IV. Monorepos & Separation of Concerns** | Cooldown, pacing, proxy pool, and observer registration live inside `camply.providers` using base dependencies only. Prometheus wiring lives exclusively in `camply.worker.metrics` (higher layer). Verified against `[tool.importlinter]` in `pyproject.toml`.                           | PASS   |
| **V. Automated Verification**              | Test-first unit and async concurrency tests cover shared 429 cooldown, HTTP-date `Retry-After`, concurrency cap, pacing, round-robin rotation, 429/403/connection quarantine, fail-closed exhaustion, credential redaction, `aclose()` cleanup, worker metrics, and base-wheel isolation. | PASS   |

## Project Structure

### Documentation (this feature)

```text
docs/specs/037-provider-backoff-proxy-rotation/
├── spec.md                                      # Feature specification
├── plan.md                                      # This implementation plan
├── research.md                                  # Codebase & httpx2 audit and design decisions
├── data-model.md                                # Config schema, entities, and state machines
├── quickstart.md                                # Local verification & acceptance commands
├── contracts/
│   └── provider-transport-contract.md           # Env vars, state matrix, redaction & metrics contract
├── checklists/
│   └── requirements.md                          # Specification quality checklist
└── tasks.md                                     # Dependency-ordered implementation tasks
```

### Source Code & Repository Touchpoints

```text
src/camply/
├── providers/
│   ├── errors.py                                # Add ProxyPoolExhaustedError(ProviderError)
│   ├── transport_config.py                      # (new) ProviderTransportConfig, ProxyEndpoint, redact_proxy_url, TransportEvent, observer hooks
│   ├── cooldown.py                              # (new) ProviderCooldownGate, parse_retry_after (delta + HTTP-date), loop-safe semaphore/pacer
│   ├── proxy.py                                 # (new) ProxyEntry, ProxyPool (round-robin, global vs provider quarantine, wait/fail policy)
│   ├── base.py                                  # Integrate cooldown gate & proxy pool into RetryTransport and BaseProvider
│   └── __init__.py                              # Re-export ProxyPoolExhaustedError / transport reset helper if needed
└── worker/
    └── metrics.py                               # Register Prometheus observer for cooldown waits & low-cardinality proxy events

tests/
├── providers/
│   ├── test_base_provider.py                    # Preserve direct-mode regressions; verify 429 base_delay & circuit-breaker composition
│   ├── test_provider_cooldown.py                # (new) Shared cooldown, HTTP-date Retry-After, concurrency cap, pacing, cancellation, loop safety
│   └── test_proxy_rotation.py                   # (new) Round-robin, 429/403/connect quarantine, wait/fail exhaustion, no direct leak, redaction, aclose
├── worker/
│   └── test_worker_metrics.py                   # Verify Prometheus observer counters/histogram and credential-free labels
└── packaging/
    └── test_base_install.py                     # Verify base wheel works with cooldown & proxy config without optional extras

docker-compose.yaml                              # Forward optional CAMPLY_PROVIDER_* and CAMPLY_PROXY_* env vars
deploy/compose/
├── docker-compose.yaml                          # Forward optional CAMPLY_PROVIDER_* and CAMPLY_PROXY_* env vars
├── docker-compose.production.yaml               # Forward optional CAMPLY_PROVIDER_* and CAMPLY_PROXY_* env vars
├── docker-compose.standalone.yaml               # Forward optional CAMPLY_PROVIDER_* and CAMPLY_PROXY_* env vars
└── production.env.example                       # Document commented opt-in proxy & pacing env vars

docs/
├── examples/.env.example                        # Document commented opt-in proxy & pacing env vars
├── operations/CONFIGURATION.md                  # Add Provider Rate Limiting, Pacing & Proxy Rotation reference
├── architecture/DESIGN_PROVIDERS.md             # Document shared cooldown gate, concurrency cap, and opt-in proxy pool
├── specs/index.md                               # Register spec 037
├── CHECKLIST.md                                 # Mark T4.1.1 completed after implementation verification
└── PLAN.md                                      # Mark Phase 4 Rate Limiting completed after implementation verification
```

**Structure Decision**: Keeping configuration/redaction (`transport_config.py`), shared cooldown/pacing (`cooldown.py`), and proxy rotation (`proxy.py`) as three small, single-responsibility modules inside `src/camply/providers/` avoids bloating `src/camply/providers/base.py` (already 1,142 lines), keeps Ruff cyclomatic complexity cleanly under `C901` limits without new ignores in `pyproject.toml`, and obeys every `[tool.importlinter]` contract without exceptions.

## Phased Implementation Design

### Phase 1 & 2 — Foundation (Config, Errors, Redaction & Observer Hooks)

- Add `ProxyPoolExhaustedError(ProviderError)` to `src/camply/providers/errors.py`.
- Create `src/camply/providers/transport_config.py` with `ProviderTransportConfig`, `ProxyEndpoint`, `redact_proxy_url`, `parse_proxy_urls` (including `socksio` detection for `socks5`/`socks5h`), `TransportEvent`, and `register_transport_observer` / `unregister_transport_observer` / `emit_transport_event`.

### Phase 3 — User Story 1 (MVP: Shared Per-Provider Cooldown & Polite Concurrency Pacing)

- Create `src/camply/providers/cooldown.py` with `parse_retry_after` (delta-seconds + RFC 9110 HTTP-date, clamped to `[0.0, max_cooldown_seconds]`) and `ProviderCooldownGate` (monotonic `_cooldown_until`, loop-safe `WeakKeyDictionary` semaphore & pacing lock, `slot()` context manager releasing semaphore before retry sleeps).
- Wire `ProviderCooldownGate` into `RetryTransport` and `BaseProvider` in `src/camply/providers/base.py`:
  - Fix the 429 exponential-backoff fallback to use `RetryStrategy.base_delay` / `RetryStrategy.max_delay` (clamped to `max_cooldown_seconds`).
  - Trigger shared cooldown on every 429 (including final retry exhaustion) in direct mode.
  - Keep standalone `RetryTransport()` constructor creating an isolated local gate so existing unit tests never leak cooldown across tests, while `BaseProvider.__init__()` resolves the shared per-provider gate from `BaseProvider._cooldown_gates`.
  - Add `BaseProvider.reset_transport_state()` for clean test teardown.

### Phase 4 — User Story 2 (Opt-In BYO Proxy Rotation & Quarantine)

- Create `src/camply/providers/proxy.py` with `ProxyEntry` and `ProxyPool` (round-robin cursor, provider-scoped quarantine on 429/403, global quarantine on `ProxyError`/connection/timeout/protocol error, `wait` bounded by `max_cooldown_seconds` vs `fail` policy raising `ProxyPoolExhaustedError`).
- Wire `ProxyPool` into `RetryTransport` and `BaseProvider` in `src/camply/providers/base.py`:
  - Include `httpx2.ProxyError` in proxy-mode retryable transport errors.
  - Lazily construct per-proxy `httpx2.AsyncHTTPTransport(proxy=endpoint.raw_url, limits=self._limits, trust_env=False)` inside `self._proxy_transports`.
  - Guarantee fail-closed egress: when `self._proxy_pool` is active, never touch `self._inner`.
  - Close all created proxy transports, `self._inner` (if present), `super().aclose()`, and `_cb_tasks` cleanly inside `RetryTransport.aclose()`.
  - Cache the process-wide `ProxyPool` keyed by config signature so production shares one pool across provider instances while `monkeypatch.setenv` in tests automatically isolates pools.

### Phase 5 — User Story 3 (Credential Hygiene, Diagnostics & Optional Worker Metrics)

- Scrub any accidental credential substrings when re-raising proxy transport errors and emit structured `structlog` diagnostics with credential-free `ProxyEndpoint.label`.
- Register a lightweight Prometheus observer in `src/camply/worker/metrics.py` tracking `camply_provider_cooldown_waits_total`, `camply_provider_cooldown_wait_seconds`, and `camply_provider_proxy_events_total` (strictly low-cardinality labels, never proxy URLs or credentials).
- Verify base-wheel isolation (`tests/packaging/test_base_install.py`) and Import Linter (`task backend:imports`).

### Phase 6 — Deployment Forwarding, Documentation & Verification

- Forward optional `CAMPLY_PROVIDER_*` and `CAMPLY_PROXY_*` environment variables in Compose files and document commented examples in `.env.example` and `production.env.example`.
- Update `docs/operations/CONFIGURATION.md`, `docs/architecture/DESIGN_PROVIDERS.md`, `docs/specs/index.md`, `docs/CHECKLIST.md`, and `docs/PLAN.md`.
- Execute the full [quickstart.md](quickstart.md) verification suite.

## Complexity Tracking

The design passes all five Constitution gates and all `[tool.importlinter]` contracts without exceptions or complexity waivers.
