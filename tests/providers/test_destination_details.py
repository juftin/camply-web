"""Destination snapshot validation and stable photo selection regressions."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from camply.providers.details import DestinationDetails, DestinationPhoto, public_url


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "https://user:password@example.com/photo.jpg",
        "http://127.0.0.1/photo.jpg",
        "http://127.1/photo.jpg",
        "http://0x7f.0.0.1/photo.jpg",
        "http://[::1]/photo.jpg",
        "https://some-server/photo.jpg",
        "http://localhost/photo.jpg",
    ],
)
def test_reject_unsafe_destination_urls(url: str) -> None:
    """Untrusted schemes, credentials, and local/placeholder hosts are excluded."""
    assert public_url(url) is None
    with pytest.raises(ValidationError):
        DestinationPhoto(url=url)


def test_photos_are_deduplicated_sorted_and_bounded() -> None:
    """Primary photos survive stable URL ordering, duplicates, and the cap."""
    photos = [
        DestinationPhoto(url=f"https://photos.example.com/{n:02}.jpg")
        for n in range(20)
    ]
    primary = DestinationPhoto(url=photos[-1].url, is_primary=True, caption="A lake")
    snapshot = DestinationDetails(
        source_url="https://parks.example.com/park",
        fetched_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        photos=[*reversed(photos), primary],
    )
    assert len(snapshot.photos) == 12
    assert snapshot.photos[0] == primary
    assert len({photo.url for photo in snapshot.photos}) == 12


def test_invalid_dimensions_and_naive_freshness_are_rejected() -> None:
    """Snapshots never claim invalid dimensions or ambiguous refresh time."""
    with pytest.raises(ValidationError):
        DestinationPhoto(url="https://photos.example.com/photo.jpg", width=0)
    with pytest.raises(ValidationError):
        DestinationDetails(
            source_url="https://parks.example.com/park", fetched_at=datetime(2030, 1, 1)
        )
