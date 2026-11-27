"""
Provider HTTP transport configuration, proxy URL validation/redaction, and observer hooks.

This module uses only base package dependencies so CLI, standalone, and
distributed worker runtimes share one transport configuration and observability
surface without pulling optional server or monitoring packages into
``camply.providers``.
"""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal
from urllib.parse import quote, unquote, urlsplit

import structlog
from pydantic import Field, PrivateAttr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.getLogger(__name__)

_SUPPORTED_PROXY_SCHEMES: frozenset[str] = frozenset(
    {"http", "https", "socks5", "socks5h"}
)
_SOCKS_SCHEMES: frozenset[str] = frozenset({"socks5", "socks5h"})
_MIN_PORT = 1
_MAX_PORT = 65535
_URL_USERINFO_RE = re.compile(r"([a-zA-Z][a-zA-Z0-9+.-]*://)([^\s/@]+)@")

ProxyExhaustedPolicy = Literal["wait", "fail"]
TransportEventKind = Literal[
    "cooldown_wait",
    "proxy_selected",
    "proxy_quarantined",
    "proxy_exhausted",
]


def redact_proxy_url(raw_url: str) -> str:
    """
    Strip credentials, query strings, and fragments from a proxy URL string.

    Parameters
    ----------
    raw_url : str
        Raw proxy URL or malformed proxy candidate string.

    Returns
    -------
    str
        Credential-free URL string safe for logs and error messages.
    """
    cleaned = raw_url.strip()
    if not cleaned:
        return ""

    # Drop query and fragment up front so token parameters can never survive.
    without_query = re.split(r"[?#]", cleaned, maxsplit=1)[0]

    try:
        parts = urlsplit(without_query)
    except ValueError:
        return _redact_fallback(without_query)

    if parts.netloc:
        hostport = parts.netloc.rsplit("@", 1)[-1]
        prefix = f"{parts.scheme.lower()}://" if parts.scheme else ""
        return f"{prefix}{hostport}{parts.path}"

    return _redact_fallback(without_query)


def _redact_fallback(url_without_query: str) -> str:
    """Defensively strip userinfo segments from malformed URLs."""
    if "://" in url_without_query:
        scheme, rest = url_without_query.split("://", 1)
        authority, sep, tail = rest.partition("/")
        hostport = authority.rsplit("@", 1)[-1]
        return f"{scheme.lower()}://{hostport}{sep}{tail}"

    authority, sep, tail = url_without_query.partition("/")
    hostport = authority.rsplit("@", 1)[-1]
    return f"{hostport}{sep}{tail}"


def scrub_credentials(text: str, secrets: Iterable[str] = ()) -> str:
    """
    Remove URL userinfo and explicit credential tokens from an arbitrary string.

    Parameters
    ----------
    text : str
        Message text (such as an upstream transport exception string).
    secrets : Iterable[str], optional
        Known credential tokens (usernames/passwords) to replace with ``[REDACTED]``.

    Returns
    -------
    str
        Sanitized text containing no configured credentials.
    """
    scrubbed = _URL_USERINFO_RE.sub(r"\1", text)
    candidates: set[str] = set()
    for token in secrets:
        if not token:
            continue
        candidates.add(token)
        unquoted = unquote(token)
        if unquoted:
            candidates.add(unquoted)
        quoted = quote(unquoted, safe="")
        if quoted:
            candidates.add(quoted)

    # Replace longer tokens first so substrings cannot leave partial fragments.
    for token in sorted(candidates, key=len, reverse=True):
        if token in scrubbed:
            scrubbed = scrubbed.replace(token, "[REDACTED]")
    return scrubbed


@dataclass(frozen=True)
class ProxyEndpoint:
    """
    Immutable, credential-safe representation of a validated proxy endpoint.

    Parameters
    ----------
    index : int
        0-based position in the parsed proxy pool.
    scheme : str
        Normalized lowercase URL scheme (``http``, ``https``, ``socks5``, ``socks5h``).
    host : str
        Parsed hostname without IPv6 brackets.
    port : int | None
        Explicit port number if specified.
    label : str
        Credential-free display label (``proxy-{index} ({scheme}://{host}[:{port}])``).
    _raw_url : str
        Private full connection URL used solely to construct proxy transports.
    """

    index: int
    scheme: str
    host: str
    port: int | None
    label: str
    _raw_url: str = field(repr=False)

    @property
    def raw_url(self) -> str:
        """Return the full connection URL for proxy transport initialization only."""
        return self._raw_url

    def credential_tokens(self) -> tuple[str, ...]:
        """Return non-empty username/password tokens for defensive error scrubbing."""
        try:
            parts = urlsplit(self._raw_url)
        except ValueError:
            return ()
        tokens: list[str] = []
        if parts.username:
            tokens.append(parts.username)
        if parts.password:
            tokens.append(parts.password)
        return tuple(tokens)

    def __str__(self) -> str:
        """Return the credential-free endpoint label."""
        return self.label

    def __repr__(self) -> str:
        """Return the credential-free endpoint label."""
        return self.label


def _format_proxy_label(index: int, scheme: str, host: str, port: int | None) -> str:
    """Format a safe ``proxy-{index} ({scheme}://{host}[:{port}])`` label."""
    display_host = f"[{host}]" if ":" in host else host
    host_port = f"{display_host}:{port}" if port is not None else display_host
    return f"proxy-{index} ({scheme}://{host_port})"


def _parse_single_proxy_url(raw_entry: str, *, slot_index: int) -> ProxyEndpoint:
    """Validate and parse one non-empty proxy URL entry without leaking secrets."""
    redacted = redact_proxy_url(raw_entry)
    try:
        parts = urlsplit(raw_entry)
    except ValueError as exc:
        raise ValueError(
            f"Invalid proxy URL at index {slot_index} ({redacted}): malformed URL"
        ) from exc

    scheme = parts.scheme.lower()
    if scheme not in _SUPPORTED_PROXY_SCHEMES:
        supported = ", ".join(sorted(_SUPPORTED_PROXY_SCHEMES))
        raise ValueError(
            f"Invalid proxy URL at index {slot_index} ({redacted}): "
            f"unsupported scheme '{scheme or '<missing>'}' (supported: {supported})"
        )

    host = parts.hostname
    if not host:
        raise ValueError(
            f"Invalid proxy URL at index {slot_index} ({redacted}): missing hostname"
        )

    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError(
            f"Invalid proxy URL at index {slot_index} ({redacted}): invalid port"
        ) from exc

    if port is not None and not (_MIN_PORT <= port <= _MAX_PORT):
        raise ValueError(
            f"Invalid proxy URL at index {slot_index} ({redacted}): "
            f"port must be between {_MIN_PORT} and {_MAX_PORT}"
        )

    if scheme in _SOCKS_SCHEMES and importlib.util.find_spec("socksio") is None:
        raise ValueError(
            f"Proxy URL at index {slot_index} ({redacted}) requires optional "
            f"'socksio' package for {scheme}:// proxies. Install 'socksio' or "
            f"use an http:// or https:// proxy URL."
        )

    label = _format_proxy_label(slot_index, scheme, host, port)
    return ProxyEndpoint(
        index=slot_index,
        scheme=scheme,
        host=host,
        port=port,
        label=label,
        _raw_url=raw_entry,
    )


def parse_proxy_urls(raw_proxy_urls: str) -> tuple[ProxyEndpoint, ...]:
    """
    Parse, validate, and deduplicate a comma-separated ``CAMPLY_PROXY_URLS`` string.

    Parameters
    ----------
    raw_proxy_urls : str
        Comma-separated proxy URL string. Whitespace around entries is trimmed,
        empty segments are skipped, and exact duplicates are removed while
        preserving first-seen order.

    Returns
    -------
    tuple[ProxyEndpoint, ...]
        Validated, credential-safe proxy endpoints (empty tuple when disabled).

    Raises
    ------
    ValueError
        If any entry has an unsupported scheme, missing host, invalid port, or
        uses ``socks5://``/``socks5h://`` without ``socksio`` installed.
    """
    if not raw_proxy_urls or not raw_proxy_urls.strip():
        return ()

    endpoints: list[ProxyEndpoint] = []
    seen: set[str] = set()

    for segment in raw_proxy_urls.split(","):
        cleaned = segment.strip()
        if not cleaned or cleaned in seen:
            continue
        endpoint = _parse_single_proxy_url(cleaned, slot_index=len(endpoints))
        seen.add(cleaned)
        endpoints.append(endpoint)

    return tuple(endpoints)


class ProviderTransportConfig(BaseSettings):
    """
    Environment-driven configuration for provider cooldown, pacing, and proxy rotation.

    All settings use the ``CAMPLY_`` environment variable prefix (case-insensitive).
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CAMPLY_",
        case_sensitive=False,
        hide_input_in_errors=True,
    )

    provider_max_concurrency: int = Field(default=4, ge=0)
    """Maximum concurrent in-flight HTTP requests per provider (0 disables cap)."""

    provider_min_interval_seconds: float = Field(default=0.0, ge=0.0, le=60.0)
    """Optional minimum start spacing in seconds between requests to a provider."""

    provider_max_cooldown_seconds: float = Field(default=60.0, gt=0.0, le=600.0)
    """Maximum single cooldown or all-quarantined wait duration in seconds."""

    proxy_urls: str = Field(default="", repr=False)
    """Comma-separated opt-in BYO proxy URLs (empty disables proxy rotation)."""

    proxy_quarantine_seconds: float = Field(default=60.0, gt=0.0, le=3600.0)
    """Default quarantine duration in seconds for failing or blocked proxies."""

    proxy_exhausted_policy: ProxyExhaustedPolicy = Field(default="wait")
    """Policy when all configured proxies are quarantined (``wait`` or ``fail``)."""

    _parsed_proxies: tuple[ProxyEndpoint, ...] = PrivateAttr(default=())

    @field_validator("proxy_exhausted_policy", mode="before")
    @classmethod
    def _normalize_exhausted_policy(cls, value: Any) -> Any:
        """Normalize exhausted policy string case before Literal validation."""
        if isinstance(value, str):
            return value.strip().lower()
        return value

    def model_post_init(self, __context: Any) -> None:
        """Validate ``proxy_urls`` eagerly without exposing secrets in ValidationError."""
        self._parsed_proxies = parse_proxy_urls(self.proxy_urls)

    def parsed_proxies(self) -> tuple[ProxyEndpoint, ...]:
        """Return validated, deduplicated proxy endpoints for this configuration."""
        return self._parsed_proxies

    def proxy_pool_key(
        self,
    ) -> tuple[tuple[str, ...], float, float, ProxyExhaustedPolicy]:
        """Return a stable process-cache key for the configured proxy pool."""
        return (
            tuple(endpoint.raw_url for endpoint in self._parsed_proxies),
            self.proxy_quarantine_seconds,
            self.provider_max_cooldown_seconds,
            self.proxy_exhausted_policy,
        )


@dataclass(frozen=True)
class TransportEvent:
    """
    Lightweight, credential-free telemetry event emitted by provider transports.

    Parameters
    ----------
    kind : TransportEventKind
        Event discriminator (``cooldown_wait``, ``proxy_selected``,
        ``proxy_quarantined``, or ``proxy_exhausted``).
    provider : str
        Concrete provider class name (e.g., ``RecreationGovProvider``).
    reason : str
        Low-cardinality reason code (e.g., ``429``, ``403``, ``round_robin``).
    proxy_label : str | None, optional
        Credential-free ``ProxyEndpoint.label`` for structured logs only.
    delay_seconds : float, optional
        Wait or quarantine duration in seconds (default ``0.0``).
    """

    kind: TransportEventKind
    provider: str
    reason: str
    proxy_label: str | None = None
    delay_seconds: float = 0.0


TransportObserver = Callable[[TransportEvent], None]

_transport_observers: list[TransportObserver] = []


def register_transport_observer(observer: TransportObserver) -> None:
    """
    Register a callback to receive ``TransportEvent`` notifications.

    Duplicate registrations of the same callable are ignored.
    """
    if observer not in _transport_observers:
        _transport_observers.append(observer)


def unregister_transport_observer(observer: TransportObserver) -> None:
    """Remove a previously registered transport observer if present."""
    try:
        _transport_observers.remove(observer)
    except ValueError:
        pass


def emit_transport_event(event: TransportEvent) -> None:
    """Dispatch *event* to all registered observers, isolating observer errors."""
    for observer in tuple(_transport_observers):
        try:
            observer(event)
        except Exception as exc:
            logger.debug(
                "Transport observer raised an exception",
                observer=getattr(observer, "__name__", type(observer).__name__),
                error=type(exc).__name__,
            )
