"""
Tests for Pydantic schema validation in the backend package.
"""

import pytest
from pydantic import ValidationError

from camply.server.models.campgrounds import Campground


class TestCampgroundSchema:
    """Tests for the Campground Pydantic model."""

    def test_full_campground(self) -> None:
        """
        A campground with all fields populated should be valid.
        """
        cg = Campground(
            id="full_id",
            provider_id=1,
            recreation_area_id="rec_1",
            name="Full Campground",
            description="A nice campground",
            country="US",
            state="CO",
            longitude=-105.0,
            latitude=40.0,
            reservable=True,
            enabled=True,
        )
        assert cg.id == "full_id"
        assert cg.provider_id == 1
        assert cg.recreation_area_id == "rec_1"
        assert cg.name == "Full Campground"
        assert cg.description == "A nice campground"
        assert cg.country == "US"
        assert cg.state == "CO"
        assert cg.longitude == -105.0
        assert cg.latitude == 40.0
        assert cg.reservable is True
        assert cg.enabled is True
        assert cg.url is not None

    def test_campground_default_reservable(self) -> None:
        """
        reservable defaults to True.
        """
        cg = Campground(
            id="test",
            provider_id=1,
            recreation_area_id=None,
            name="Test",
            description=None,
            country=None,
            state=None,
            longitude=None,
            latitude=None,
        )
        assert cg.reservable is True

    def test_campground_default_enabled(self) -> None:
        """
        enabled defaults to True.
        """
        cg = Campground(
            id="test",
            provider_id=1,
            recreation_area_id=None,
            name="Test",
            description=None,
            country=None,
            state=None,
            longitude=None,
            latitude=None,
        )
        assert cg.enabled is True

    def test_campground_missing_required_id(self) -> None:
        """
        Campground without id should raise ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            Campground(  # type: ignore[call-arg]
                provider_id=1,
                recreation_area_id=None,
                name="No ID",
                description=None,
                country=None,
                state=None,
                longitude=None,
                latitude=None,
            )
        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "id" in field_names

    def test_campground_missing_required_name(self) -> None:
        """
        Campground without name should raise ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            Campground(  # type: ignore[call-arg]
                id="test",
                provider_id=1,
                recreation_area_id=None,
                description=None,
                country=None,
                state=None,
                longitude=None,
                latitude=None,
            )
        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "name" in field_names

    def test_campground_invalid_provider_id_type(self) -> None:
        """
        Provider_id must be an int; Pydantic v2 coerces str to int.
        """
        cg = Campground(
            id="test",
            provider_id="1",  # type: ignore[arg-type]
            recreation_area_id=None,
            name="Coerced",
            description=None,
            country=None,
            state=None,
            longitude=None,
            latitude=None,
        )
        assert cg.provider_id == 1

    def test_campground_recreation_area_id_none(self) -> None:
        """
        recreation_area_id can be explicitly set to None.
        """
        cg = Campground(
            id="test",
            provider_id=1,
            recreation_area_id=None,
            name="Test",
            description=None,
            country=None,
            state=None,
            longitude=None,
            latitude=None,
        )
        assert cg.recreation_area_id is None

    def test_campground_description_none(self) -> None:
        """
        description can be explicitly set to None.
        """
        cg = Campground(
            id="test",
            provider_id=1,
            recreation_area_id=None,
            name="Test",
            description=None,
            country=None,
            state=None,
            longitude=None,
            latitude=None,
        )
        assert cg.description is None

    def test_campground_invalid_id_type(self) -> None:
        """
        id must be a string; passing an int should raise ValidationError.
        """
        with pytest.raises(ValidationError) as exc_info:
            Campground(
                id=123,  # type: ignore[arg-type]
                provider_id=1,
                recreation_area_id=None,
                name="Invalid",
                description=None,
                country=None,
                state=None,
                longitude=None,
                latitude=None,
            )
        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "id" in field_names


class TestScanResponseDatetime:
    """Tests for UtcDateTime serialization in ScanResponse."""

    def test_naive_datetime_serialized_with_utc_z(self) -> None:
        """
        Naive datetimes from SQLAlchemy are converted to UTC aware datetimes
        and serialized with the 'Z' suffix to avoid client-side timezone mismatch.
        """
        import datetime
        import json
        import uuid

        from camply.server.schemas import ScanResponse

        naive_dt = datetime.datetime(2026, 10, 14, 3, 54, 33)
        scan = ScanResponse(
            id=uuid.uuid4(),
            provider_id=1,
            campground_id="123",
            start_date=datetime.date(2026, 11, 1),
            end_date=datetime.date(2026, 11, 3),
            is_active=True,
            min_stay_length=1,
            require_electric=False,
            last_checked_at=naive_dt,
            created_at=naive_dt,
        )

        assert scan.last_checked_at is not None
        assert scan.last_checked_at.tzinfo == datetime.timezone.utc
        assert scan.created_at.tzinfo == datetime.timezone.utc

        data = json.loads(scan.model_dump_json())
        assert data["last_checked_at"] == "2026-10-14T03:54:33Z"
        assert data["created_at"] == "2026-10-14T03:54:33Z"

    def test_aware_datetime_serialized_with_utc_z(self) -> None:
        """
        Aware datetimes are preserved and serialized with the 'Z' suffix.
        """
        import datetime
        import json
        import uuid

        from camply.server.schemas import ScanResponse

        aware_dt = datetime.datetime(
            2026, 10, 14, 3, 54, 33, tzinfo=datetime.timezone.utc
        )
        scan = ScanResponse(
            id=uuid.uuid4(),
            provider_id=1,
            campground_id="123",
            start_date=datetime.date(2026, 11, 1),
            end_date=datetime.date(2026, 11, 3),
            is_active=True,
            min_stay_length=1,
            require_electric=False,
            last_checked_at=aware_dt,
            created_at=aware_dt,
        )

        data = json.loads(scan.model_dump_json())
        assert data["last_checked_at"] == "2026-10-14T03:54:33Z"
        assert data["created_at"] == "2026-10-14T03:54:33Z"

    def test_none_last_checked_at_remains_none(self) -> None:
        """
        Optional last_checked_at can be None and serializes to null in JSON.
        """
        import datetime
        import json
        import uuid

        from camply.server.schemas import ScanResponse

        created_dt = datetime.datetime(2026, 10, 14, 3, 54, 33)
        scan = ScanResponse(
            id=uuid.uuid4(),
            provider_id=1,
            campground_id="123",
            start_date=datetime.date(2026, 11, 1),
            end_date=datetime.date(2026, 11, 3),
            is_active=True,
            min_stay_length=1,
            require_electric=False,
            last_checked_at=None,
            created_at=created_dt,
        )

        assert scan.last_checked_at is None
        data = json.loads(scan.model_dump_json())
        assert data["last_checked_at"] is None
