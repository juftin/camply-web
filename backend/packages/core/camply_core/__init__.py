"""
Core domain models, search engine, and booking providers for camply.
"""

from camply_core.availability import (
    AvailabilitySnapshot,
    diff_new_openings,
    identify_new_campsites,
)
from camply_core.errors import (
    CamplyError,
    CircuitBreakerOpenError,
    NotificationError,
    ProviderError,
    ProviderRateLimitedError,
    ProviderResponseError,
)
from camply_core.matching import (
    calculate_consecutive_runs,
    find_qualifying_stays,
    longest_consecutive_nights,
    matches_filters,
)
from camply_core.models import (
    CampsiteDTO,
    CampsiteType,
    NotificationDTO,
    ProviderDescriptor,
    SearchFilters,
    SearchWindow,
    StayWindow,
)
from camply_core.notifications import PushoverClient
from camply_core.providers import (
    BaseProviderClient,
    RecreationGovClient,
)
from camply_core.transport import (
    ProviderCircuitBreaker,
    RetryStrategy,
    RetryTransport,
)

__version__ = "0.1.0"

__all__ = [
    "AvailabilitySnapshot",
    "BaseProviderClient",
    "CamplyError",
    "CampsiteDTO",
    "CampsiteType",
    "CircuitBreakerOpenError",
    "NotificationDTO",
    "NotificationError",
    "ProviderCircuitBreaker",
    "ProviderDescriptor",
    "ProviderError",
    "ProviderRateLimitedError",
    "ProviderResponseError",
    "PushoverClient",
    "RecreationGovClient",
    "RetryStrategy",
    "RetryTransport",
    "SearchFilters",
    "SearchWindow",
    "StayWindow",
    "calculate_consecutive_runs",
    "diff_new_openings",
    "find_qualifying_stays",
    "identify_new_campsites",
    "longest_consecutive_nights",
    "matches_filters",
]
