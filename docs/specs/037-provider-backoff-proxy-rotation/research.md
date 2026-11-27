# Research: Shared Provider Cooldown, Pacing & Opt-In Proxy Rotation

**Feature**: [037-provider-backoff-proxy-rotation](spec.md) | **Date**: 2026-11-27

## 1. Audit of Current Provider HTTP Transport (`src/camply/providers/base.py`)

A full read of `src/camply/providers/base.py` (1,142 lines), `src/camply/providers/errors.py`, all four provider families (`recreation_gov`, `usedirect`, `going_to_camp`, `reserve_america`), and `tests/providers/test_base_provider.py` revealed the following concrete facts:

### 1.1 Single choke point across all 26 providers

Every registered provider in `src/camply/providers/__init__.py` subclasses `BaseProvider` and issues all upstream HTTP calls (availability queries, upstream search, catalog sync, streaming ZIP downloads, and enrichment) through `self.async_client` (`httpx2.AsyncClient` backed by `RetryTransport`). No provider constructs a raw `httpx2.AsyncClient` or bypasses `RetryTransport`.

### 1.2 Existing per-instance pacing vs shared state

| Provider family                       | Current pacing                                | Concurrent calls within one scan?                                                                                                |
| ------------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `RecreationGovProvider`               | None                                          | Yes — `asyncio.gather(campsites_task, *availability_tasks)` fires parallel requests for metadata + every month in the date range |
| `UseDirectProvider` (10 subclasses)   | Per-instance `asyncio.Lock` + `1.0s` interval | Sequential within one instance, uncoordinated across instances                                                                   |
| `GoingToCampProvider` (14 subclasses) | Per-instance `asyncio.Lock` + `0.5s` interval | Sequential within one instance, uncoordinated across instances                                                                   |
| `ReserveAmericaProvider`              | Per-instance `asyncio.Lock` + `1.0s` interval | Sequential within one instance, uncoordinated across instances                                                                   |

In `src/camply/worker/engine/scanner.py` (`check_target`) and `src/camply/worker/engine/catalog.py`, each scan instantiates a fresh `provider_cls()` and closes `provider.async_client` in `finally`. In `src/camply/cli/campsite_batch.py`, multiple concurrent searches for the same provider share one `BaseProvider` instance. Therefore, shared per-provider cooldown, concurrency bounding, and proxy quarantine MUST live in process-wide shared state keyed by `type(self).__name__` (matching `BaseProvider._circuit_breakers`), surviving individual `provider.async_client.aclose()` calls.

### 1.3 Concrete defects and gaps in current `RetryTransport`

1. **Isolated 429 sleeps (thundering herd)**: `_handle_retryable_response()` calls `await asyncio.sleep(delay)` locally inside the failing request while concurrent sibling requests to the same provider continue sending upstream and amplifying rate limits.
2. **429 fallback delay bug**: When HTTP 429 lacks a `Retry-After` header, `_handle_retryable_response()` currently computes exponential backoff using `_5xx_base_delay` (`0.5s`) and `_5xx_max_delay` (`30.0s`) instead of `RetryStrategy.base_delay` (`1.0s`) and `RetryStrategy.max_delay` (`60.0s`).
3. **Numeric-only `Retry-After` parsing**: `_parse_retry_after()` only parses `float(raw)` and ignores RFC 9110 HTTP-date values (e.g., `Wed, 21 Oct 2026 07:28:00 GMT`), and does not clamp extreme values (e.g., a 24-hour header could stall a worker past the 90-second `asyncio.wait_for` timeout in `scanner.py:148`).
4. **Missing `httpx2.ProxyError` in retryable transport errors**: `_RETRYABLE_CONNECTION_ERRORS` currently contains `(httpx2.ConnectError, httpx2.TimeoutException, httpx2.RemoteProtocolError)`. Verified in `.venv`, `httpx2.ProxyError` inherits directly from `httpx2.TransportError`, not `ConnectError`, so proxy tunnel failures would not be caught unless explicitly included.
5. **Test compatibility coupling to `transport._inner`**: `tests/providers/test_base_provider.py` directly replaces `transport._inner` with `MagicMock(spec=httpx2.AsyncHTTPTransport)` and wraps `transport._inner.aclose` in `test_client_close_releases_retry_connection_pool`. Preserving `self._inner` for direct mode (when no proxy pool is active) keeps all existing tests passing unchanged.
6. **Event-loop reuse across `asyncio.run()` calls**: Celery tasks (`src/camply/worker/tasks/scanner.py:110`) call `asyncio.run(...)` per task, and `pytest-asyncio` uses function-scoped loops (`pyproject.toml:226`). Storing `asyncio.Semaphore` and `asyncio.Lock` per `(provider_name, running_loop)` via `WeakKeyDictionary[asyncio.AbstractEventLoop, ...]` avoids cross-loop `RuntimeError` while keeping monotonic timestamps (`float`) loop-independent.

## 2. Verification of `httpx2` Proxy & Transport API in `.venv`

Directly verified against the locked environment (`Python 3.14.10`, `httpx2==2.16.2`):

```text
AsyncHTTPTransport.__init__(
    self,
    verify: ssl.SSLContext | str | bool = True,
    cert: CertTypes | None = None,
    trust_env: bool = True,
    http1: bool = True,
    http2: bool = False,
    limits: Limits = Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=5.0),
    proxy: ProxyTypes | None = None,
    uds: str | None = None,
    local_address: str | None = None,
    retries: int = 0,
    socket_options: Iterable[SOCKET_OPTION] | None = None,
) -> None
```

Key empirical findings from `.venv` inspection:

- **Native HTTP & HTTPS proxy support (zero new dependencies)**: `httpx2.AsyncHTTPTransport(proxy="http://proxy:8080")`, `httpx2.AsyncHTTPTransport(proxy="https://proxy:8443")`, and `httpx2.AsyncHTTPTransport(proxy="http://user:pass@proxy:8080")` all instantiate `httpcore2.AsyncHTTPProxy` natively with `proxy_auth=proxy.raw_auth`.
- **SOCKS5 requires optional `socksio`**: `httpx2.AsyncHTTPTransport(proxy="socks5://proxy:1080")` and `socks5h://` execute `import socksio` inside `httpx2.AsyncHTTPTransport.__init__` and raise `ImportError: Using SOCKS proxy, but the 'socksio' package is not installed.` when `socksio` is absent. Because `socksio` is not in base dependencies, validating `importlib.util.find_spec("socksio")` during `ProviderTransportConfig` parsing lets us accept `socks5://`/`socks5h://` automatically if the operator installed `socksio`, while failing fast with a clear, credential-redacted error otherwise.
- **`AsyncClient(transport=...)` and `trust_env`**: When `transport=RetryTransport(...)` is passed to `httpx2.AsyncClient`, `_mounts` remains `{}` even if `HTTPS_PROXY` is set in the environment. Passing `trust_env=False` when constructing each per-proxy `httpx2.AsyncHTTPTransport(proxy=..., limits=..., trust_env=False)` additionally prevents ambient SSL/proxy env leakage on managed proxy transports.
- **Exception hierarchy**:
  - `httpx2.ProxyError -> httpx2.TransportError -> httpx2.RequestError -> httpx2.HTTPError`
  - `httpx2.ConnectError -> httpx2.NetworkError -> httpx2.TransportError`
  - `httpx2.TimeoutException` covers `ConnectTimeout`, `ReadTimeout`, `WriteTimeout`, and `PoolTimeout`
  - `httpx2.RemoteProtocolError -> httpx2.ProtocolError -> httpx2.TransportError`
- **Credential redaction in `httpx2`**:
  - `repr(httpx2.Proxy("http://alice:supersecret@proxy.example.com:8080"))` produces `Proxy('http://proxy.example.com:8080', auth=('alice', '********'))` — notice the **username `alice` is still exposed**!
  - Therefore, Camply MUST NOT log `repr(httpx2.Proxy)` or raw proxy URLs. Instead, `ProxyEndpoint` MUST strip both username and password and expose only `proxy-{index} ({scheme}://{host}:{port})` (omitting port if none was specified) while keeping the raw URL private (`repr=False`).

## 3. Architectural Decisions

### Decision 1: In-process shared cooldown & BYO proxy pool vs Gluetun/VPN orchestration or Valkey state

- **Decision**: Implement an in-process `ProviderCooldownGate` (always on, zero config) plus an opt-in in-process `ProxyPool` configured via `CAMPLY_PROXY_URLS`.
- **Rationale**:
  - Zero cost ($0) and zero extra containers, VPN credentials, or daemon processes.
  - Works identically in base CLI (`camply campsites`), standalone (`camply serve`), and distributed Celery workers (`camply serve worker`) without requiring Valkey, Redis, or Docker.
  - Decouples Camply from any specific egress provider: operators who want VPN or multi-IP egress can point `CAMPLY_PROXY_URLS` at a single Gluetun HTTP proxy container, a Tailscale exit node, an Oracle Cloud free-tier Squid/tinyproxy instance, Cloudflare WARP proxy, or a commercial rotating proxy.
- **Alternatives considered**:
  - _Bundled OpenVPN/Gluetun orchestration (like stale PR #65)_: Rejected — adds heavy privileged Docker/VPN operational complexity, paid VPN coupling, and breaks CLI/standalone parity.
  - _Free public proxy list scraping_: Rejected — unreliable, high latency, and severe MITM/security risk.
  - _Valkey-backed distributed cooldown/quarantine_: Rejected for initial scope — violates base-package / standalone simplicity and requires extra network round trips per HTTP request. Can be layered later behind the same gate/pool interfaces if multi-replica telemetry warrants it.

### Decision 2: Per-provider vs global proxy quarantine scoping

- **Decision**: Scope HTTP `429` and `403` proxy quarantines per `(provider_name, proxy_index)`, and scope proxy transport/connection/timeout errors (`ProxyError`, `ConnectError`, `TimeoutException`, `RemoteProtocolError`) globally across all providers for that proxy.
- **Rationale**: A rate limit or WAF block from Recreation.gov does not mean the same proxy IP is blocked by ReserveCalifornia or GoingToCamp, whereas an unreachable or timing-out proxy is broken for every provider. Evaluating `max(global_quarantined_until, provider_quarantined_until.get(provider_name, 0.0))` keeps the implementation to a few lines while maximizing pool utilization.
- **Alternatives considered**:
  - _Purely global quarantine for all failures_: Rejected — unnecessarily starves unrelated providers when a single strict provider emits 429/403.
  - _Purely per-provider quarantine for connection errors_: Rejected — wastes retries rediscovering a dead proxy on every provider.

### Decision 3: Direct-mode cooldown vs proxy-mode quarantine interaction

- **Decision**: In direct mode (no proxies configured), HTTP 429 triggers the shared `ProviderCooldownGate` so all concurrent requests to that provider wait together. In proxy mode, HTTP 429 or 403 quarantines that specific proxy for that provider and retries immediately on the next healthy proxy (bypassing the direct cooldown gate while healthy proxies exist). If every proxy in the pool becomes quarantined, the pool's `wait` policy naturally acts as a shared cooldown waiting for the soonest quarantine expiry (bounded by `CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS`), while `fail` raises `ProxyPoolExhaustedError` immediately.
- **Rationale**: Triggering a provider-wide cooldown when 1 of 3 proxies gets 429 would defeat the purpose of rotating to healthy alternate egress IPs. Conversely, when all proxies are rate-limited (e.g., endpoint-wide upstream limit or a 1-proxy pool), all proxies become quarantined and `wait` mode pauses cleanly until the soonest expiry.

### Decision 4: Fail-closed egress invariant when proxies are configured

- **Decision**: When `CAMPLY_PROXY_URLS` is non-empty, `RetryTransport` NEVER dispatches requests over direct egress (`self._inner`). There is no `allow_direct_fallback` toggle.
- **Rationale**: Operators configure proxies specifically to avoid exposing or burning the host's real IP. Silent fallback during an all-quarantined spike would leak the real IP unexpectedly and violate operator expectations.

### Decision 5: Import-Linter-compliant observability hook

- **Decision**: Define a lightweight, zero-dependency observer callback registration (`register_transport_observer` / `TransportEvent`) inside `camply.providers`, emitting structured logs via `structlog` everywhere. In `camply.worker.metrics`, register a Prometheus observer that translates `TransportEvent`s into low-cardinality counters and histograms (`camply_provider_cooldown_waits_total`, `camply_provider_cooldown_wait_seconds`, `camply_provider_proxy_events_total`).
- **Rationale**: `pyproject.toml` `[tool.importlinter]` strictly forbids `camply.providers.**` from importing `prometheus_client`, `celery`, `redis`, or `fastapi`. Dependency inversion keeps `camply.providers` 100% base-dependency-only while still surfacing production Prometheus telemetry in distributed workers.

### Decision 6: Non-breaking defaults for concurrency and pacing

- **Decision**: Set `CAMPLY_PROVIDER_MAX_CONCURRENCY=4` (`0` disables), `CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS=0.0` (disabled by default), `CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS=60.0`, `CAMPLY_PROXY_URLS=""` (disabled), `CAMPLY_PROXY_QUARANTINE_SECONDS=60.0`, and `CAMPLY_PROXY_EXHAUSTED_POLICY="wait"`.
- **Rationale**:
  - `max_concurrency=4` lets Recreation.gov's typical multi-month scan (metadata + 1–3 months) execute in full parallel with zero regression while capping large fan-outs (e.g., recreation-area scans or multi-search CLI YAML batches) to polite upstream load.
  - `min_interval_seconds=0.0` avoids adding artificial latency to fast VCR/unit tests or stacking on top of UseDirect/GoingToCamp/ReserveAmerica's existing per-provider intervals.
  - `max_cooldown_seconds=60.0` keeps waits safely below the 90-second per-target timeout in `src/camply/worker/engine/scanner.py:148`.
