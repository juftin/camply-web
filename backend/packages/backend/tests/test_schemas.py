"""
Tests for Pydantic schema validation in the backend package.
"""

import pytest
from pydantic import ValidationError

from backend.models.campgrounds import Campground


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
