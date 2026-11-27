"""Tests for provider transport configuration, credential redaction, and proxy rotation."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx2
import pytest
import structlog
from pydantic import ValidationError

from camply.providers.base import (
    BaseProvider,
    ProviderCircuitBreaker,
    RetryStrategy,
    RetryTransport,
)
from camply.providers.errors import (
    ProviderRateLimitedError,
    ProxyPoolExhaustedError,
)
from camply.providers.proxy import ProxyPool
from camply.providers.transport_config import (
    ProviderTransportConfig,
    ProxyEndpoint,
    TransportEvent,
    emit_transport_event,
    parse_proxy_urls,
    redact_proxy_url,
    register_transport_observer,
    scrub_credentials,
    unregister_transport_observer,
)


class TestProviderTransportConfig:
    """Tests for ProviderTransportConfig environment loading and validation."""

    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Default transport settings disable proxies and pacing with concurrency 4."""
        for key in (
            "CAMPLY_PROVIDER_MAX_CONCURRENCY",
            "CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS",
            "CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS",
            "CAMPLY_PROXY_URLS",
            "CAMPLY_PROXY_QUARANTINE_SECONDS",
            "CAMPLY_PROXY_EXHAUSTED_POLICY",
        ):
            monkeypatch.delenv(key, raising=False)

        config = ProviderTransportConfig()
        assert config.provider_max_concurrency == 4
        assert config.provider_min_interval_seconds == 0.0
        assert config.provider_max_cooldown_seconds == 60.0
        assert config.proxy_urls == ""
        assert config.proxy_quarantine_seconds == 60.0
        assert config.proxy_exhausted_policy == "wait"
        assert config.parsed_proxies() == ()

    def test_environment_overrides_and_case_insensitive_policy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Environment variables override defaults and normalize exhausted policy case."""
        monkeypatch.setenv("CAMPLY_PROVIDER_MAX_CONCURRENCY", "0")
        monkeypatch.setenv("CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS", "0.25")
        monkeypatch.setenv("CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS", "120.5")
        monkeypatch.setenv("CAMPLY_PROXY_QUARANTINE_SECONDS", "90")
        monkeypatch.setenv("CAMPLY_PROXY_EXHAUSTED_POLICY", "FAIL")
        monkeypatch.setenv("CAMPLY_PROXY_URLS", "http://proxy1:8080")

        config = ProviderTransportConfig()
        assert config.provider_max_concurrency == 0
        assert config.provider_min_interval_seconds == 0.25
        assert config.provider_max_cooldown_seconds == 120.5
        assert config.proxy_quarantine_seconds == 90.0
        assert config.proxy_exhausted_policy == "fail"
        proxies = config.parsed_proxies()
        assert len(proxies) == 1
        assert proxies[0].label == "proxy-0 (http://proxy1:8080)"

    @pytest.mark.parametrize(
        ("env_key", "env_value"),
        [
            ("CAMPLY_PROVIDER_MAX_CONCURRENCY", "-1"),
            ("CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS", "-0.1"),
            ("CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS", "60.1"),
            ("CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS", "0"),
            ("CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS", "600.1"),
            ("CAMPLY_PROXY_QUARANTINE_SECONDS", "0"),
            ("CAMPLY_PROXY_QUARANTINE_SECONDS", "3600.1"),
            ("CAMPLY_PROXY_EXHAUSTED_POLICY", "direct"),
        ],
    )
    def test_numeric_and_enum_bounds_rejected(
        self, monkeypatch: pytest.MonkeyPatch, env_key: str, env_value: str
    ) -> None:
        """Out-of-range numeric settings and unknown exhausted policies fail validation."""
        monkeypatch.setenv(env_key, env_value)
        with pytest.raises(ValidationError):
            ProviderTransportConfig()

    def test_proxy_urls_trimmed_deduplicated_and_repr_safe(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Comma-separated proxy URLs trim whitespace, drop blanks/dupes, and hide secrets in repr."""
        monkeypatch.setenv(
            "CAMPLY_PROXY_URLS",
            " http://alice:supersecret@proxy1.example:8080 , , "
            "http://alice:supersecret@proxy1.example:8080, "
            "https://proxy2.example ,",
        )
        config = ProviderTransportConfig()
        proxies = config.parsed_proxies()
        assert len(proxies) == 2
        assert proxies[0] == ProxyEndpoint(
            index=0,
            scheme="http",
            host="proxy1.example",
            port=8080,
            label="proxy-0 (http://proxy1.example:8080)",
            _raw_url="http://alice:supersecret@proxy1.example:8080",
        )
        assert proxies[1].index == 1
        assert proxies[1].scheme == "https"
        assert proxies[1].host == "proxy2.example"
        assert proxies[1].port is None
        assert proxies[1].label == "proxy-1 (https://proxy2.example)"

        for rendered in (repr(config), str(config), repr(proxies[0]), str(proxies[0])):
            assert "alice" not in rendered
            assert "supersecret" not in rendered

    def test_proxy_urls_only_whitespace_and_commas_disables_proxies(self) -> None:
        """Whitespace- and comma-only proxy strings resolve cleanly to an empty pool."""
        assert parse_proxy_urls(" ,  , \t ") == ()

    def test_ipv6_proxy_host_bracketed_in_label(self) -> None:
        """IPv6 literal hostnames are bracketed in the credential-free label."""
        proxies = parse_proxy_urls("http://alice:supersecret@[::1]:8080")
        assert len(proxies) == 1
        assert proxies[0].host == "::1"
        assert proxies[0].port == 8080
        assert proxies[0].label == "proxy-0 (http://[::1]:8080)"
        assert "alice" not in repr(proxies[0])
        assert "supersecret" not in repr(proxies[0])

    @pytest.mark.parametrize(
        "raw_url",
        [
            "ftp://alice:supersecret@proxy.example:21",
            "socks4://alice:supersecret@proxy.example:1080",
            "proxy.example:8080",
            "http://alice:supersecret@:8080",
            "http://alice:supersecret@proxy.example:99999",
            "http://alice:supersecret@proxy.example:0",
            "http://alice:supersecret@proxy.example:notaport",
        ],
    )
    def test_invalid_proxy_urls_fail_fast_without_leaking_credentials(
        self, raw_url: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invalid schemes, missing hosts, and invalid ports raise redacted ValueError."""
        monkeypatch.setenv("CAMPLY_PROXY_URLS", raw_url)
        with pytest.raises(ValueError) as excinfo:
            ProviderTransportConfig().parsed_proxies()
        message = str(excinfo.value)
        assert "alice" not in message
        assert "supersecret" not in message

    @pytest.mark.parametrize("scheme", ["socks5", "socks5h"])
    def test_socks5_rejected_without_socksio_and_redacted(
        self, scheme: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SOCKS5 proxy URLs fail fast with a credential-free error when socksio is absent."""
        monkeypatch.setenv(
            "CAMPLY_PROXY_URLS", f"{scheme}://alice:supersecret@proxy.example:1080"
        )
        with (
            patch(
                "camply.providers.transport_config.importlib.util.find_spec",
                return_value=None,
            ),
            pytest.raises(ValueError) as excinfo,
        ):
            ProviderTransportConfig().parsed_proxies()
        message = str(excinfo.value)
        assert "socksio" in message
        assert "alice" not in message
        assert "supersecret" not in message
        assert f"{scheme}://proxy.example:1080" in message

    @pytest.mark.parametrize("scheme", ["socks5", "socks5h"])
    def test_socks5_accepted_when_socksio_installed(self, scheme: str) -> None:
        """SOCKS5 proxy URLs succeed when optional socksio is available."""
        with patch(
            "camply.providers.transport_config.importlib.util.find_spec",
            return_value=object(),
        ):
            proxies = parse_proxy_urls(
                f"{scheme}://alice:supersecret@proxy.example:1080"
            )
        assert len(proxies) == 1
        assert proxies[0].scheme == scheme
        assert proxies[0].label == f"proxy-0 ({scheme}://proxy.example:1080)"


class TestRedactProxyUrl:
    """Tests for redact_proxy_url credential and query/fragment stripping."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (
                "http://alice:supersecret@proxy.example:8080",
                "http://proxy.example:8080",
            ),
            (
                "https://alice:p@ssword@proxy.example:8443?token=secret#frag",
                "https://proxy.example:8443",
            ),
            (
                "http://alice:supersecret@proxy.example:badport",
                "http://proxy.example:badport",
            ),
            ("http://proxy.example:8080", "http://proxy.example:8080"),
            (
                "http://alice:supersecret@[::1]:8080",
                "http://[::1]:8080",
            ),
        ],
    )
    def test_redacts_credentials_query_and_fragment(
        self, raw: str, expected: str
    ) -> None:
        """redact_proxy_url removes userinfo, query strings, and fragments safely."""
        redacted = redact_proxy_url(raw)
        assert redacted == expected
        assert "alice" not in redacted
        assert "supersecret" not in redacted
        assert "token=secret" not in redacted


class TestTransportObservers:
    """Tests for the zero-dependency transport observer registry."""

    def test_observer_receives_events_and_errors_are_isolated(self) -> None:
        """Failing observers must not break event delivery to other observers."""
        received: list[TransportEvent] = []

        def broken_observer(event: TransportEvent) -> None:
            raise RuntimeError("observer boom")

        def healthy_observer(event: TransportEvent) -> None:
            received.append(event)

        register_transport_observer(broken_observer)
        register_transport_observer(healthy_observer)
        try:
            event = TransportEvent(
                kind="cooldown_wait",
                provider="RecreationGovProvider",
                reason="429",
                delay_seconds=2.5,
            )
            emit_transport_event(event)
            assert received == [event]
        finally:
            unregister_transport_observer(broken_observer)
            unregister_transport_observer(healthy_observer)

        # Unregistered observer no longer receives events
        emit_transport_event(
            TransportEvent(
                kind="proxy_selected",
                provider="RecreationGovProvider",
                reason="round_robin",
                proxy_label="proxy-0 (http://proxy1:8080)",
            )
        )
        assert len(received) == 1

    def test_proxy_pool_exhausted_error_attributes_and_message(self) -> None:
        """ProxyPoolExhaustedError records provider, retry_after, and pool_size cleanly."""
        exc = ProxyPoolExhaustedError(
            "RecreationGovProvider", retry_after=12.34, pool_size=2
        )
        assert exc.provider_name == "RecreationGovProvider"
        assert exc.retry_after == 12.34
        assert exc.pool_size == 2
        assert "RecreationGovProvider" in str(exc)
        assert "12.3s" in str(exc)
        assert "Direct egress fallback is disabled" in str(exc)


def _make_response(
    status_code: int, headers: dict[str, str] | None = None
) -> httpx2.Response:
    """Build a synthetic ``httpx2.Response`` for proxy rotation tests."""
    return httpx2.Response(
        status_code=status_code,
        headers=headers or {},
        request=httpx2.Request("GET", "https://example.com/api"),
    )


class _ProxyTestProvider(BaseProvider):
    """Concrete BaseProvider subclass for verifying proxy pool wiring."""

    async def search_upstream(self, query):  # type: ignore[override]
        return []

    async def find_availabilities(self, park_id, start_date, end_date):  # type: ignore[override]
        return []

    async def sync_metadata(self) -> None:
        return None

    async def populate_database(self) -> None:
        return None

    @property
    def provider(self):  # type: ignore[override]
        from camply.db.models import Provider

        return Provider(
            id=201, name="ProxyTestProvider", url="https://proxy-test.example"
        )

    @classmethod
    def get_rec_area_url(cls, rec_area_id: str) -> str:
        return f"https://proxy-test.example/area/{rec_area_id}"

    @classmethod
    def get_campground_url(
        cls, campground_id: str, *, rec_area_id: str | None = None
    ) -> str:
        return f"https://proxy-test.example/camp/{campground_id}"


class TestProxyPoolAndTransportRotation:
    """Tests for opt-in proxy rotation, quarantine scoping, exhaustion, and fail-closed egress."""

    def setup_method(self) -> None:
        """Reset shared provider transport and circuit-breaker state before each test."""
        BaseProvider.reset_transport_state()
        ProviderCircuitBreaker._state.clear()
        ProviderCircuitBreaker._locks.clear()

    def teardown_method(self) -> None:
        """Clean up shared provider transport state after each test."""
        BaseProvider.reset_transport_state()
        ProviderCircuitBreaker._state.clear()
        ProviderCircuitBreaker._locks.clear()

    @pytest.mark.asyncio
    async def test_disabled_by_default_direct_pass_through(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty CAMPLY_PROXY_URLS keeps proxy rotation disabled with direct egress."""
        monkeypatch.delenv("CAMPLY_PROXY_URLS", raising=False)
        provider = _ProxyTestProvider()
        transport = provider.async_client._transport
        assert isinstance(transport, RetryTransport)
        assert transport._proxy_pool is None

        transport._inner = MagicMock(spec=httpx2.AsyncHTTPTransport)
        transport._inner.handle_async_request = AsyncMock(
            return_value=_make_response(200)
        )
        transport._inner.aclose = AsyncMock()

        response = await provider.async_client.get("https://example.com/direct")
        assert response.status_code == 200
        transport._inner.handle_async_request.assert_awaited_once()
        await provider.async_client.aclose()

    @pytest.mark.asyncio
    async def test_round_robin_selection_across_three_healthy_proxies(self) -> None:
        """Healthy proxies are selected in deterministic round-robin order."""
        endpoints = parse_proxy_urls(
            "http://p0.example:8080,http://p1.example:8080,http://p2.example:8080"
        )
        pool = ProxyPool(endpoints, quarantine_seconds=30.0)
        selected = [(await pool.select("ProviderA")).index for _ in range(6)]
        assert selected == [0, 1, 2, 0, 1, 2]
        snap = pool.snapshot("ProviderA")
        assert len(snap) == 3
        assert all(row["healthy"] is True for row in snap)

    @pytest.mark.asyncio
    async def test_provider_scoped_quarantine_on_429_and_403_transparent_retry(
        self,
    ) -> None:
        """HTTP 429 and 403 quarantine only for the affected provider and rotate immediately."""
        endpoints = parse_proxy_urls(
            "http://p0.example:8080,http://p1.example:8080,http://p2.example:8080"
        )
        pool = ProxyPool(
            endpoints,
            quarantine_seconds=30.0,
            max_wait_seconds=60.0,
            exhausted_policy="fail",
        )
        transport = RetryTransport(
            retry_strategy=RetryStrategy(max_retries=2, jitter=False),
            provider_name="ProviderA",
            proxy_pool=pool,
        )
        transport._inner = MagicMock(spec=httpx2.AsyncHTTPTransport)
        transport._inner.handle_async_request = AsyncMock(
            side_effect=AssertionError("Direct transport must never be invoked")
        )
        transport._inner.aclose = AsyncMock()

        p0 = MagicMock(spec=httpx2.AsyncHTTPTransport)
        p1 = MagicMock(spec=httpx2.AsyncHTTPTransport)
        p2 = MagicMock(spec=httpx2.AsyncHTTPTransport)
        p0.handle_async_request = AsyncMock(
            return_value=_make_response(429, headers={"Retry-After": "12"})
        )
        p1.handle_async_request = AsyncMock(return_value=_make_response(403))
        p2.handle_async_request = AsyncMock(return_value=_make_response(200))
        for idx, mock_t in enumerate((p0, p1, p2)):
            mock_t.aclose = AsyncMock()
            transport._proxy_transports[idx] = mock_t

        resp = await transport.handle_async_request(
            httpx2.Request("GET", "https://example.com/api")
        )
        assert resp.status_code == 200
        p0.handle_async_request.assert_awaited_once()
        p1.handle_async_request.assert_awaited_once()
        p2.handle_async_request.assert_awaited_once()
        transport._inner.handle_async_request.assert_not_awaited()

        # p0 and p1 are quarantined for ProviderA, but stay healthy for ProviderB!
        assert pool.entries[0].is_healthy("ProviderA") is False
        assert pool.entries[1].is_healthy("ProviderA") is False
        assert pool.entries[2].is_healthy("ProviderA") is True
        assert pool.entries[0].is_healthy("ProviderB") is True
        assert pool.entries[1].is_healthy("ProviderB") is True
        # p0 honored Retry-After: 12 (not default 30s)
        p0_remaining = pool.entries[0].quarantine_until("ProviderA") - time.monotonic()
        assert 9.0 < p0_remaining <= 12.5

        # Subsequent requests for ProviderA go exclusively to healthy p2
        resp2 = await transport.handle_async_request(
            httpx2.Request("GET", "https://example.com/api2")
        )
        assert resp2.status_code == 200
        assert p0.handle_async_request.await_count == 1
        assert p1.handle_async_request.await_count == 1
        assert p2.handle_async_request.await_count == 2

        await transport.aclose()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exc_factory",
        [
            lambda: httpx2.ProxyError("tunnel rejected"),
            lambda: httpx2.ConnectError("connection refused"),
            lambda: httpx2.TimeoutException("timed out"),
            lambda: httpx2.RemoteProtocolError("bad gateway frame"),
        ],
    )
    async def test_global_quarantine_on_proxy_transport_errors(
        self, exc_factory
    ) -> None:
        """ProxyError, ConnectError, TimeoutException, and RemoteProtocolError quarantine globally."""
        endpoints = parse_proxy_urls("http://p0.example:8080,http://p1.example:8080")
        pool = ProxyPool(endpoints, quarantine_seconds=30.0)
        transport = RetryTransport(
            retry_strategy=RetryStrategy(max_retries=1, jitter=False),
            provider_name="ProviderA",
            proxy_pool=pool,
        )
        transport._inner = MagicMock(spec=httpx2.AsyncHTTPTransport)
        transport._inner.handle_async_request = AsyncMock(
            side_effect=AssertionError("Direct transport must never be invoked")
        )
        transport._inner.aclose = AsyncMock()

        p0 = MagicMock(spec=httpx2.AsyncHTTPTransport)
        p1 = MagicMock(spec=httpx2.AsyncHTTPTransport)
        p0.handle_async_request = AsyncMock(side_effect=exc_factory())
        p1.handle_async_request = AsyncMock(return_value=_make_response(200))
        p0.aclose = AsyncMock()
        p1.aclose = AsyncMock()
        transport._proxy_transports[0] = p0
        transport._proxy_transports[1] = p1

        resp = await transport.handle_async_request(
            httpx2.Request("GET", "https://example.com/api")
        )
        assert resp.status_code == 200
        # p0 is quarantined across ALL providers (both ProviderA and ProviderB)
        assert pool.entries[0].is_healthy("ProviderA") is False
        assert pool.entries[0].is_healthy("ProviderB") is False
        assert pool.entries[1].is_healthy("ProviderB") is True
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_upstream_5xx_retries_without_quarantining_proxy(self) -> None:
        """Upstream HTTP 5xx does not quarantine healthy proxies."""
        endpoints = parse_proxy_urls("http://p0.example:8080,http://p1.example:8080")
        pool = ProxyPool(endpoints, quarantine_seconds=30.0)
        transport = RetryTransport(
            retry_strategy=RetryStrategy(
                max_retries=1, _5xx_base_delay=0.01, jitter=False
            ),
            provider_name="ProviderA",
            proxy_pool=pool,
        )
        p0 = MagicMock(spec=httpx2.AsyncHTTPTransport)
        p1 = MagicMock(spec=httpx2.AsyncHTTPTransport)
        p0.handle_async_request = AsyncMock(return_value=_make_response(502))
        p1.handle_async_request = AsyncMock(return_value=_make_response(200))
        p0.aclose = AsyncMock()
        p1.aclose = AsyncMock()
        transport._proxy_transports[0] = p0
        transport._proxy_transports[1] = p1

        resp = await transport.handle_async_request(
            httpx2.Request("GET", "https://example.com/api")
        )
        assert resp.status_code == 200
        assert pool.entries[0].is_healthy("ProviderA") is True
        assert pool.entries[0].quarantine_count == 0
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_single_proxy_pool_wait_policy_waits_and_retries_fail_closed(
        self,
    ) -> None:
        """Single-proxy pool under wait policy waits for quarantine expiry without direct egress."""
        endpoints = parse_proxy_urls("http://gluetun:8888")
        pool = ProxyPool(
            endpoints,
            quarantine_seconds=0.08,
            max_wait_seconds=1.0,
            exhausted_policy="wait",
        )
        transport = RetryTransport(
            retry_strategy=RetryStrategy(max_retries=1, jitter=False),
            provider_name="ProviderA",
            proxy_pool=pool,
        )
        transport._inner = MagicMock(spec=httpx2.AsyncHTTPTransport)
        transport._inner.handle_async_request = AsyncMock(
            side_effect=AssertionError("Direct transport must never be invoked")
        )
        transport._inner.aclose = AsyncMock()

        p0 = MagicMock(spec=httpx2.AsyncHTTPTransport)
        p0.handle_async_request = AsyncMock(
            side_effect=[_make_response(429), _make_response(200)]
        )
        p0.aclose = AsyncMock()
        transport._proxy_transports[0] = p0

        start = time.monotonic()
        resp = await transport.handle_async_request(
            httpx2.Request("GET", "https://example.com/api")
        )
        elapsed = time.monotonic() - start
        assert resp.status_code == 200
        assert elapsed >= 0.06
        assert p0.handle_async_request.await_count == 2
        transport._inner.handle_async_request.assert_not_awaited()
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_wait_policy_exceeding_max_wait_raises_without_direct_egress_or_breaker_trip(
        self,
    ) -> None:
        """When soonest quarantine exceeds max_wait_seconds, wait policy fails closed cleanly."""
        endpoints = parse_proxy_urls("http://p0.example:8080")
        pool = ProxyPool(
            endpoints,
            quarantine_seconds=30.0,
            max_wait_seconds=5.0,
            exhausted_policy="wait",
        )
        pool.quarantine(0, provider_name="ProviderA", reason="429", duration=30.0)
        cb = ProviderCircuitBreaker("ProviderA", failure_threshold=2)
        transport = RetryTransport(
            retry_strategy=RetryStrategy(max_retries=1, jitter=False),
            circuit_breaker=cb,
            provider_name="ProviderA",
            proxy_pool=pool,
        )
        transport._inner = MagicMock(spec=httpx2.AsyncHTTPTransport)
        transport._inner.handle_async_request = AsyncMock(
            side_effect=AssertionError("Direct transport must never be invoked")
        )
        transport._inner.aclose = AsyncMock()

        with pytest.raises(ProxyPoolExhaustedError) as excinfo:
            await transport.handle_async_request(
                httpx2.Request("GET", "https://example.com/api")
            )
        assert excinfo.value.pool_size == 1
        assert excinfo.value.retry_after is not None and excinfo.value.retry_after > 5.0
        await asyncio.sleep(0)
        assert cb.consecutive_failures == 0
        transport._inner.handle_async_request.assert_not_awaited()
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_fail_policy_raises_immediately_without_tripping_circuit_breaker(
        self,
    ) -> None:
        """Fail policy raises ProxyPoolExhaustedError immediately with zero breaker failures."""
        endpoints = parse_proxy_urls("http://p0.example:8080,http://p1.example:8080")
        pool = ProxyPool(
            endpoints,
            quarantine_seconds=60.0,
            max_wait_seconds=60.0,
            exhausted_policy="fail",
        )
        pool.quarantine(0, provider_name="ProviderA", reason="403")
        pool.quarantine(1, provider_name="ProviderA", reason="429")
        cb = ProviderCircuitBreaker("ProviderA", failure_threshold=2)
        transport = RetryTransport(
            retry_strategy=RetryStrategy(max_retries=2, jitter=False),
            circuit_breaker=cb,
            provider_name="ProviderA",
            proxy_pool=pool,
        )
        transport._inner = MagicMock(spec=httpx2.AsyncHTTPTransport)
        transport._inner.handle_async_request = AsyncMock(
            side_effect=AssertionError("Direct transport must never be invoked")
        )
        transport._inner.aclose = AsyncMock()

        start = time.monotonic()
        with pytest.raises(ProxyPoolExhaustedError) as excinfo:
            await transport.handle_async_request(
                httpx2.Request("GET", "https://example.com/api")
            )
        assert time.monotonic() - start < 0.1
        assert excinfo.value.pool_size == 2
        await asyncio.sleep(0)
        assert cb.consecutive_failures == 0
        transport._inner.handle_async_request.assert_not_awaited()
        await transport.aclose()

    @pytest.mark.asyncio
    async def test_proxy_transport_created_with_trust_env_false_and_closed_on_aclose(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Managed proxy transports disable trust_env and aclose() closes all pools and cb tasks."""
        monkeypatch.setenv(
            "CAMPLY_PROXY_URLS",
            "http://p0.example:8080,http://p1.example:8080",
        )
        created_kwargs: list[dict[str, object]] = []
        created_mocks: list[MagicMock] = []
        real_transport_cls = httpx2.AsyncHTTPTransport

        def fake_transport(**kwargs: object) -> MagicMock:
            created_kwargs.append(kwargs)
            mock_t = MagicMock(spec=real_transport_cls)
            mock_t.handle_async_request = AsyncMock(return_value=_make_response(200))
            mock_t.aclose = AsyncMock()
            created_mocks.append(mock_t)
            return mock_t

        provider = _ProxyTestProvider()
        transport = provider.async_client._transport
        assert isinstance(transport, RetryTransport)
        assert transport._proxy_pool is not None
        transport._inner = MagicMock(spec=httpx2.AsyncHTTPTransport)
        transport._inner.aclose = AsyncMock()

        with patch(
            "camply.providers.base.httpx2.AsyncHTTPTransport",
            side_effect=fake_transport,
        ):
            r1 = await provider.async_client.get("https://example.com/1")
            r2 = await provider.async_client.get("https://example.com/2")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert len(created_kwargs) == 2
        assert created_kwargs[0]["proxy"] == "http://p0.example:8080"
        assert created_kwargs[0]["trust_env"] is False
        assert created_kwargs[1]["proxy"] == "http://p1.example:8080"
        assert created_kwargs[1]["trust_env"] is False

        await provider.async_client.aclose()
        for mock_t in created_mocks:
            mock_t.aclose.assert_awaited_once()
        transport._inner.aclose.assert_awaited_once()
        assert not transport._cb_tasks

    @pytest.mark.asyncio
    async def test_proxy_mode_429_exhaustion_raises_and_403_exhaustion_trips_breaker(
        self,
    ) -> None:
        """Exhausted 429 raises ProviderRateLimitedError; exhausted 403 returns 403 and records 1 failure."""
        endpoints = parse_proxy_urls("http://p0.example:8080,http://p1.example:8080")
        pool = ProxyPool(endpoints, quarantine_seconds=30.0, exhausted_policy="fail")
        cb = ProviderCircuitBreaker("ProviderExhaust", failure_threshold=5)
        transport = RetryTransport(
            retry_strategy=RetryStrategy(max_retries=1, jitter=False),
            circuit_breaker=cb,
            provider_name="ProviderExhaust",
            proxy_pool=pool,
        )
        p0 = MagicMock(spec=httpx2.AsyncHTTPTransport)
        p1 = MagicMock(spec=httpx2.AsyncHTTPTransport)
        p0.handle_async_request = AsyncMock(return_value=_make_response(429))
        p1.handle_async_request = AsyncMock(return_value=_make_response(429))
        p0.aclose = AsyncMock()
        p1.aclose = AsyncMock()
        transport._proxy_transports[0] = p0
        transport._proxy_transports[1] = p1

        with pytest.raises(ProviderRateLimitedError):
            await transport.handle_async_request(
                httpx2.Request("GET", "https://example.com/429")
            )
        await asyncio.sleep(0)
        assert cb.consecutive_failures == 1

        pool.reset()
        p0.handle_async_request = AsyncMock(return_value=_make_response(403))
        p1.handle_async_request = AsyncMock(return_value=_make_response(403))
        resp_403 = await transport.handle_async_request(
            httpx2.Request("GET", "https://example.com/403")
        )
        assert resp_403.status_code == 403
        await asyncio.sleep(0)
        assert cb.consecutive_failures == 2
        await transport.aclose()


class TestCredentialRedactionEndToEnd:
    """End-to-end credential hygiene checks across reprs, logs, validation, and exceptions."""

    def test_scrub_credentials_removes_userinfo_and_tokens(self) -> None:
        """scrub_credentials removes raw URL userinfo and explicit secret tokens."""
        raw = (
            "ProxyError connecting to http://alice:supersecret@proxy.example:8080 "
            "(auth=('alice', 'supersecret'))"
        )
        cleaned = scrub_credentials(raw, ("alice", "supersecret"))
        assert "alice" not in cleaned
        assert "supersecret" not in cleaned
        assert "http://proxy.example:8080" in cleaned

    @pytest.mark.asyncio
    async def test_no_credentials_in_repr_logs_or_reraised_proxy_errors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Credentials never appear in config/pool reprs, structlog events, or re-raised errors."""
        auth_url = "http://alice:supersecret@proxy.example:8080"
        monkeypatch.setenv("CAMPLY_PROXY_URLS", auth_url)
        monkeypatch.setenv("CAMPLY_PROXY_EXHAUSTED_POLICY", "fail")

        config = ProviderTransportConfig()
        endpoints = config.parsed_proxies()
        pool = ProxyPool(
            endpoints,
            quarantine_seconds=30.0,
            max_wait_seconds=60.0,
            exhausted_policy="fail",
        )

        for rendered in (
            repr(config),
            str(config),
            repr(endpoints[0]),
            str(endpoints[0]),
            repr(pool),
            str(pool),
        ):
            assert "alice" not in rendered
            assert "supersecret" not in rendered

        transport = RetryTransport(
            retry_strategy=RetryStrategy(max_retries=0, jitter=False),
            provider_name="SecureProvider",
            proxy_pool=pool,
        )
        p0 = MagicMock(spec=httpx2.AsyncHTTPTransport)
        p0.handle_async_request = AsyncMock(
            side_effect=httpx2.ProxyError(
                f"407 Proxy Authentication Required for {auth_url} (user=alice, pass=supersecret)"
            )
        )
        p0.aclose = AsyncMock()
        transport._proxy_transports[0] = p0

        with structlog.testing.capture_logs() as captured_logs:
            with pytest.raises(httpx2.ProxyError) as proxy_exc:
                await transport.handle_async_request(
                    httpx2.Request("GET", "https://example.com/secret")
                )
            with pytest.raises(ProxyPoolExhaustedError) as exhausted_exc:
                await transport.handle_async_request(
                    httpx2.Request("GET", "https://example.com/secret2")
                )

        assert "alice" not in str(proxy_exc.value)
        assert "supersecret" not in str(proxy_exc.value)
        assert "http://proxy.example:8080" in str(proxy_exc.value)
        assert "alice" not in str(exhausted_exc.value)
        assert "supersecret" not in str(exhausted_exc.value)

        serialized_logs = repr(captured_logs)
        assert "alice" not in serialized_logs
        assert "supersecret" not in serialized_logs
        assert "proxy-0 (http://proxy.example:8080)" in serialized_logs
        await transport.aclose()
