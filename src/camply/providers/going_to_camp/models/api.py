"""Parse GoingToCamp resource and map availability responses into worker DTOs.

Attributes
----------
AVAILABLE_STATUS : int
    GoingToCamp ``Availability.Available`` status code (bookable online).
MAP_LINK_OPEN_STATUSES : frozenset[int]
    Child loop-map statuses (``Available = 0``, ``PartiallyAvailable = 7``) worth traversing.
_SPECIFIC_RESOURCE_MODEL : int
    GoingToCamp ``ResourceModel.Specific`` for concrete reservable sites/cabins.
_CABIN_KEYWORDS : tuple[str, ...]
    Keywords identifying roofed lodging inventory.
_RV_KEYWORDS : tuple[str, ...]
    Keywords identifying RV/trailer/camper equipment.
_TENT_KEYWORDS : tuple[str, ...]
    Keywords identifying tent/walk-in/boat-in camping inventory.
_ELECTRIC_ATTRIBUTES : frozenset[str]
    Lowercase attribute names that describe electrical hookups or outlets.
_NON_ELECTRIC_MARKERS : tuple[str, ...]
    Negative markers that negate electrical hookup indications.
_ACCESSIBLE_ATTRIBUTES : frozenset[str]
    Lowercase attribute names that directly indicate ADA/barrier-free accessibility.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from camply.providers.dto import CampsiteDTO, CampsiteType
from camply.providers.going_to_camp.models.metadata import (
    BookingCategory,
    LocalizedText,
    ResourceCategory,
    ResourceLocation,
    preferred_localized,
    resolve_overnight_categories,
)

AVAILABLE_STATUS = 0
MAP_LINK_OPEN_STATUSES = frozenset({0, 7})
_SPECIFIC_RESOURCE_MODEL = 0

_CABIN_KEYWORDS = (
    "cabin",
    "yurt",
    "adirondack",
    "teepee",
    "tepee",
    "house",
    "vacation",
    "cottage",
    "lodge",
    "lodging",
    "otentik",
    "oasis",
    "ôasis",
    "microcube",
    "elc",
    "retreat",
)
_RV_KEYWORDS = (
    "rv",
    "trailer",
    "motorhome",
    "camper",
    "fifth wheel",
    "5th wheel",
    "van",
)
_TENT_KEYWORDS = (
    "tent",
    "backpack",
    "hiker",
    "walk-in",
    "walk in",
    "boat in",
    "boat-in",
)
_ELECTRIC_ATTRIBUTES = frozenset(
    {"service type", "electrical service", "electrical outlets"}
)
_NON_ELECTRIC_MARKERS = (
    "not available",
    "no hook-up",
    "no hookup",
    "non-electric",
    "nonelectric",
    "no electric",
    "unpowered",
    "unelectrified",
    "none",
)
_ACCESSIBLE_ATTRIBUTES = frozenset(
    {
        "ada accessible",
        "ada only",
        "accessible",
        "accessibility",
        "barrier-free",
        "barrier free",
        "wheelchair accessible",
    }
)


def _localized_label(entries: list[LocalizedText] | None) -> str:
    """Extract a stripped display label from localized text entries."""
    loc = preferred_localized(entries)
    if loc is None:
        return ""
    for candidate in (
        loc.displayName,
        loc.value,
        loc.name,
        loc.fullName,
        loc.shortName,
    ):
        if candidate is not None and candidate.strip():
            return candidate.strip()
    return ""


class EquipmentSubCategory(BaseModel):
    """Describe one equipment sub-category (e.g. Small Tent, RV/Trailer up to 35ft)."""

    subEquipmentCategoryId: int
    localizedValues: list[LocalizedText] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Return the sub-equipment display name."""
        return _localized_label(self.localizedValues)


class EquipmentCategory(BaseModel):
    """Group sub-equipment categories under a GoingToCamp equipment category."""

    equipmentCategoryId: int
    localizedValues: list[LocalizedText] = Field(default_factory=list)
    subEquipmentCategories: list[EquipmentSubCategory] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Return the top-level equipment category display name."""
        return _localized_label(self.localizedValues)


class AttributeEnumValue(BaseModel):
    """Map an integer enum code on a filterable attribute to its display text."""

    enumValue: int
    localizedValues: list[LocalizedText] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Return the localized enum value label."""
        return _localized_label(self.localizedValues)


class AttributeDefinition(BaseModel):
    """Define a filterable site attribute and its optional enumerated values."""

    attributeDefinitionId: int
    localizedValues: list[LocalizedText] = Field(default_factory=list)
    values: list[AttributeEnumValue] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Return the attribute definition display name."""
        return _localized_label(self.localizedValues)


class DefinedAttribute(BaseModel):
    """Hold scalar or multi-enum attribute values assigned to a resource."""

    attributeDefinitionId: int
    value: str | int | float | bool | None = None
    values: list[int] = Field(default_factory=list)


class AllowedEquipment(BaseModel):
    """Identify one permitted equipment / sub-equipment pair on a resource."""

    equipmentCategoryId: int
    subEquipmentCategoryId: int | None = None
    maxLength: float | int | None = None


@dataclass(slots=True)
class CatalogFilters:
    """Per-instance lookup tables built from GoingToCamp catalog endpoints."""

    resource_locations: dict[int, ResourceLocation]
    booking_categories: dict[int, BookingCategory]
    resource_categories: dict[int, ResourceCategory]
    equipment_names: dict[tuple[int, int | None], str]
    attributes: dict[int, AttributeDefinition]

    @classmethod
    def build(
        cls,
        *,
        resource_locations: list[ResourceLocation],
        booking_categories: list[BookingCategory],
        resource_categories: list[ResourceCategory],
        equipment_categories: list[EquipmentCategory],
        attributes: list[AttributeDefinition],
    ) -> "CatalogFilters":
        """Index catalog definitions and resolve active overnight categories."""
        eligible_booking, eligible_resources = resolve_overnight_categories(
            booking_categories, resource_categories
        )
        equipment_names: dict[tuple[int, int | None], str] = {}
        for category in equipment_categories:
            if category.display_name:
                equipment_names[(category.equipmentCategoryId, None)] = (
                    category.display_name
                )
            for sub in category.subEquipmentCategories:
                label = sub.display_name or category.display_name
                if label:
                    equipment_names[
                        (category.equipmentCategoryId, sub.subEquipmentCategoryId)
                    ] = label
        return cls(
            resource_locations={
                loc.resourceLocationId: loc for loc in resource_locations
            },
            booking_categories=eligible_booking,
            resource_categories=eligible_resources,
            equipment_names=equipment_names,
            attributes={attr.attributeDefinitionId: attr for attr in attributes},
        )


def _flatten_strings(value: Any) -> list[str]:
    """Normalize scalar or list attribute values into lowercase strings."""
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip().lower()
    return [text] if text else []


def _numeric_gt_zero(value: Any) -> bool:
    """Return True when a scalar attribute represents a positive number."""
    if isinstance(value, bool) or value is None:
        return False
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def _is_electric_from_attributes(decoded_attributes: dict[str, Any]) -> bool:
    """Determine electrical hookups conservatively from electrical attributes."""
    for raw_name, raw_val in decoded_attributes.items():
        attr_name = raw_name.strip().lower()
        if attr_name not in _ELECTRIC_ATTRIBUTES:
            continue
        if attr_name == "electrical outlets" and _numeric_gt_zero(raw_val):
            return True
        for text in _flatten_strings(raw_val):
            if text in ("no", "false", "0") or any(
                neg in text for neg in _NON_ELECTRIC_MARKERS
            ):
                continue
            if attr_name == "service type" and (
                "electric" in text or "(e/" in text or "/e/" in text or "/e)" in text
            ):
                return True
            if attr_name == "electrical service" and (
                "amp" in text or "electric" in text or text == "yes"
            ):
                return True
    return False


def _is_accessible_from_attributes(decoded_attributes: dict[str, Any]) -> bool:
    """Check dedicated accessibility attributes without matching adjacent restrooms."""
    for raw_name, raw_val in decoded_attributes.items():
        if raw_name.strip().lower() not in _ACCESSIBLE_ATTRIBUTES:
            continue
        if raw_val is True:
            return True
        if any(
            text in ("yes", "true", "accessible", "ada")
            for text in _flatten_strings(raw_val)
        ):
            return True
    return False


def _classify_campsite_type(
    *,
    category_names: list[str],
    equipment_names: list[str],
    decoded_attributes: dict[str, Any],
) -> CampsiteType:
    """Classify a GoingToCamp resource into ``CABIN``, ``RV``, ``TENT``, or ``OTHER``."""
    combined_categories = " ".join(category_names).lower()
    if any(word in combined_categories for word in _CABIN_KEYWORDS):
        return CampsiteType.CABIN

    equipment_lower = [name.lower() for name in equipment_names]
    max_rvs = next(
        (
            val
            for key, val in decoded_attributes.items()
            if key.strip().lower() == "max rvs"
        ),
        None,
    )
    if _numeric_gt_zero(max_rvs) or any(
        word in eq for eq in equipment_lower for word in _RV_KEYWORDS
    ):
        return CampsiteType.RV

    service_texts = [
        text
        for key, val in decoded_attributes.items()
        if key.strip().lower() == "service type"
        for text in _flatten_strings(val)
    ]
    tent_haystacks = [*equipment_lower, combined_categories, *service_texts]
    if any(word in hay for hay in tent_haystacks for word in _TENT_KEYWORDS):
        return CampsiteType.TENT
    return CampsiteType.OTHER


class Resource(BaseModel):
    """One GoingToCamp site or lodging unit returned for a resource location."""

    resourceId: int | None = None
    resourceLocationId: int | None = None
    resourceCategoryId: int | None = None
    resourceModel: int | None = None
    minCapacity: int | None = None
    maxCapacity: int | None = None
    maxStay: int | None = None
    localizedValues: list[LocalizedText] = Field(default_factory=list)
    allowedEquipment: list[AllowedEquipment] = Field(default_factory=list)
    definedAttributes: list[DefinedAttribute] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Return the localized site label or fall back to ``resourceId``."""
        loc = preferred_localized(self.localizedValues)
        if loc is not None:
            for candidate in (loc.name, loc.shortName, loc.fullName):
                if candidate is not None and candidate.strip():
                    return candidate.strip()
        return str(self.resourceId or "")

    def is_eligible(self, filters: CatalogFilters) -> bool:
        """Return True for specific overnight resources without zero-capacity blocks."""
        return (
            self.resourceId is not None
            and self.resourceModel == _SPECIFIC_RESOURCE_MODEL
            and self.resourceCategoryId in filters.resource_categories
            and self.maxCapacity != 0
        )

    def _decode_attributes(self, filters: CatalogFilters) -> dict[str, Any]:
        """Translate ``definedAttributes`` IDs and enum codes into readable values."""
        decoded: dict[str, Any] = {}
        for item in self.definedAttributes:
            definition = filters.attributes.get(item.attributeDefinitionId)
            if definition is None or not definition.display_name:
                continue
            if item.values:
                enum_lookup = {
                    ev.enumValue: ev.display_name for ev in definition.values
                }
                labels = [
                    enum_lookup[code] for code in item.values if enum_lookup.get(code)
                ]
                if len(labels) == 1:
                    decoded[definition.display_name] = labels[0]
                elif len(labels) > 1:
                    decoded[definition.display_name] = labels
            elif item.value is not None:
                decoded[definition.display_name] = item.value
        return decoded

    def _decode_equipment(self, filters: CatalogFilters) -> list[str]:
        """Resolve unique permitted equipment names across all categories."""
        names: set[str] = set()
        for allowed in self.allowedEquipment:
            label = filters.equipment_names.get(
                (allowed.equipmentCategoryId, allowed.subEquipmentCategoryId)
            ) or filters.equipment_names.get((allowed.equipmentCategoryId, None))
            if label:
                names.add(label)
        return sorted(names)

    def to_dto(
        self,
        *,
        filters: CatalogFilters,
        available_dates: set[date],
        booking_category_names: list[str] | None = None,
    ) -> CampsiteDTO | None:
        """Convert an eligible resource with available nights into ``CampsiteDTO``."""
        if not self.is_eligible(filters) or not available_dates:
            return None
        assert self.resourceId is not None
        assert self.resourceCategoryId is not None
        category_name = filters.resource_categories[
            self.resourceCategoryId
        ].display_name
        booking_names = sorted(set(booking_category_names or []))
        equipment = self._decode_equipment(filters)
        decoded_attributes = self._decode_attributes(filters)
        return CampsiteDTO(
            campsite_id=str(self.resourceId),
            campsite_name=self.display_name,
            campsite_type=_classify_campsite_type(
                category_names=[category_name, *booking_names],
                equipment_names=equipment,
                decoded_attributes=decoded_attributes,
            ),
            capacity=self.maxCapacity or 0,
            available_dates=sorted(available_dates),
            is_electric=_is_electric_from_attributes(decoded_attributes),
            is_accessible=_is_accessible_from_attributes(decoded_attributes),
            metadata={
                "resource_category_id": self.resourceCategoryId,
                "resource_category": category_name,
                "booking_categories": booking_names,
                "permitted_equipment": equipment,
                "min_capacity": self.minCapacity,
                "max_stay": self.maxStay,
                "attributes": decoded_attributes,
            },
        )


class DailyAvailability(BaseModel):
    """One daily availability status entry returned by ``/api/availability/map``."""

    availability: int | None = None
    remainingQuota: int | None = None


class MapAvailabilityResponse(BaseModel):
    """Per-resource daily statuses and linked loop-map summary statuses."""

    mapId: int | None = None
    resourceAvailabilities: dict[str, list[DailyAvailability]] = Field(
        default_factory=dict
    )
    mapLinkAvailabilities: dict[str, list[int]] = Field(default_factory=dict)
