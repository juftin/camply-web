"""
Provider Error Types
"""


class ProviderError(Exception):
    """
    Base exception for all provider-related errors.
    """


class ProviderRateLimitedError(ProviderError):
    """
    Raised when a provider returns a 429 Too Many Requests after all retries are exhausted.
    """


class CircuitBreakerOpenError(ProviderError):
    """
    Raised when a circuit breaker is open and requests are short-circuited.
    """

    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name
        super().__init__(
            f"Circuit breaker is OPEN for provider '{provider_name}'. "
            f"Requests are temporarily blocked."
        )


class ProxyPoolExhaustedError(ProviderError):
    """
    Raised when all configured proxies are quarantined and no request can be sent.

    Direct egress fallback is intentionally disabled when ``CAMPLY_PROXY_URLS`` is
    configured, so requests fail closed instead of leaking the host IP address.

    Parameters
    ----------
    provider_name : str
        Concrete provider class name whose proxy pool is exhausted.
    retry_after : float | None, optional
        Seconds until the soonest quarantined proxy becomes healthy again.
    pool_size : int, optional
        Total number of configured proxies in the pool.
    """

    def __init__(
        self,
        provider_name: str,
        retry_after: float | None = None,
        pool_size: int = 0,
    ) -> None:
        self.provider_name = provider_name
        self.retry_after = retry_after
        self.pool_size = pool_size
        wait_suffix = (
            f" Next proxy available in {retry_after:.1f}s."
            if retry_after is not None
            else ""
        )
        super().__init__(
            f"All {pool_size} configured proxies are quarantined for provider "
            f"'{provider_name}'.{wait_suffix} Direct egress fallback is disabled."
        )
