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
