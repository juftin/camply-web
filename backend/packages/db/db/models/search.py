"""
Search
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import Any, Self

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    Float,
    Integer,
    String,
    and_,
    case,
    false,
    func,
    literal_column,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import ColumnElement

from db.models.base import Base

MILES_PER_LATITUDE_DEGREE: float = 69.0
"""Approximate miles per degree of latitude for bounding box calculation."""

MAX_FACET_STATES: int = 50
"""Maximum number of unique states returned in search facet aggregations."""

PG_WORD_SIMILARITY_THRESHOLD: str = "0.5"
"""Transaction-local typo threshold, allowing a single missing letter in short names."""

MIN_FUZZY_TOKEN_LENGTH: int = 4
"""Require four characters before allowing typo matches."""


def _search_vector(cls: type[Search]) -> Any:
    """Build the weighted native search vector, matching the PostgreSQL GIN index.

    The simple dictionary preserves proper names and short state codes instead
    of stemming them or dropping stop words. Literal constants ensure the
    expression matches the index even when PostgreSQL uses a generic plan.
    """
    config: ColumnElement[str] = literal_column("'simple'::regconfig")
    empty: ColumnElement[str] = literal_column("''")
    vectors = [
        func.setweight(
            func.to_tsvector(config, func.coalesce(column, empty)),
            literal_column(f"'{weight}'"),
        )
        for column, weight in (
            (cls.campground_name, "A"),
            (cls.recreation_area_name, "B"),
            (cls.city, "C"),
            (cls.state, "D"),
        )
    ]
    vector: ColumnElement[Any] = vectors[0]
    for part in vectors[1:]:
        vector = vector.op("||")(part)
    return vector


def _name_match_score(cls: type[Search], term: str) -> Any:
    """Prioritize the displayed name over a match inherited from its parent park."""
    name = func.lower(func.coalesce(cls.campground_name, cls.recreation_area_name))
    return case(
        (name == term, 1000),
        (name.startswith(term, autoescape=True), 500),
        (name.contains(term, autoescape=True), 250),
        (func.lower(cls.recreation_area_name) == term, 100),
        else_=0,
    )


def _build_attribute_filters(
    cls: type[Search],
    *,
    provider_ids: Sequence[int] | None = None,
    entity_types: Sequence[str] | None = None,
    state: str | None = None,
    has_electric: bool | None = None,
    pets_allowed: bool | None = None,
    min_rv_length: int | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_miles: float | None = None,
) -> list[Any]:
    """
    Build attribute-based filter clauses for search queries.

    Parameters
    ----------
    cls : type[Search]
        The Search model class.
    provider_ids : Sequence[int] | None
        Optional provider IDs to filter by.
    entity_types : Sequence[str] | None
        Optional entity types to filter by.
    state : str | None
        Optional state abbreviation to match.
    has_electric : bool | None
        Whether campsites must have electric hookups.
    pets_allowed : bool | None
        Whether pets must be allowed.
    min_rv_length : int | None
        Minimum accommodated RV length in feet.
    lat : float | None
        Center latitude for radius search.
    lng : float | None
        Center longitude for radius search.
    radius_miles : float | None
        Radius in miles for bounding box search.

    Returns
    -------
    list[Any]
        SQLAlchemy filter expressions.
    """
    filters: list[Any] = []
    if provider_ids:
        filters.append(cls.provider_id.in_(list(provider_ids)))
    if entity_types:
        filters.append(cls.entity_type.in_(list(entity_types)))
    if state:
        filters.append(func.upper(cls.state) == state.strip().upper())
    if has_electric is not None:
        filters.append(cls.has_electric.is_(has_electric))
    if pets_allowed is not None:
        filters.append(cls.pets_allowed.is_(pets_allowed))
    if min_rv_length is not None and min_rv_length > 0:
        filters.append(cls.max_rv_length >= min_rv_length)
    if (
        lat is not None
        and lng is not None
        and radius_miles is not None
        and radius_miles > 0
    ):
        delta_lat = radius_miles / MILES_PER_LATITUDE_DEGREE
        cos_lat = max(0.1, abs(math.cos(math.radians(lat))))
        delta_lng = radius_miles / (MILES_PER_LATITUDE_DEGREE * cos_lat)
        filters.append(cls.latitude.between(lat - delta_lat, lat + delta_lat))
        filters.append(cls.longitude.between(lng - delta_lng, lng + delta_lng))
    return filters


def _build_sqlite_text_search(
    cls: type[Search],
    term_cleaned: str,
) -> tuple[Any, Any]:
    """
    Build portable SQLite text match filter and ranking score expression.

    Parameters
    ----------
    cls : type[Search]
        The Search model class.
    term_cleaned : str
        The cleaned, lowercased search string.

    Returns
    -------
    tuple[Any, Any]
        A tuple of (text_filter_expression, total_score_expression).
    """
    tokens = re.findall(r"[^\W_]+", term_cleaned)
    if not tokens:
        return false(), None
    text_filter = and_(
        *[
            or_(
                *[
                    func.lower(column).contains(token, autoescape=True)
                    for column in (
                        cls.recreation_area_name,
                        cls.campground_name,
                        cls.city,
                        cls.state,
                    )
                ]
            )
            for token in tokens
        ]
    )
    return text_filter, _name_match_score(cls=cls, term=term_cleaned)


def _build_postgres_text_search(
    cls: type[Search],
    term_cleaned: str,
) -> tuple[Any, Any]:
    """
    Build indexed native full-text and per-token typo matching with weighted ranking.

    Every token must match, including tokens spread across names and locations.
    Trigram operators use the existing name indexes and the city index; numeric
    similarity predicates would scan rows instead. Full-text prefix matching
    supports live typing while the simple dictionary preserves proper names.

    Parameters
    ----------
    cls : type[Search]
        The Search model class.
    term_cleaned : str
        The cleaned, lowercased search string.

    Returns
    -------
    tuple[Any, Any]
        A tuple of (text_filter_expression, total_score_expression).
    """
    tokens = re.findall(r"[^\W_]+", term_cleaned)
    if not tokens:
        return false(), None

    config: ColumnElement[str] = literal_column("'simple'::regconfig")
    vector = _search_vector(cls=cls)
    token_filters = []
    fuzzy_scores = []
    for token in tokens:
        prefix_query = func.to_tsquery(config, f"{token}:*")
        matches = [vector.bool_op("@@")(prefix_query)]
        if len(token) >= MIN_FUZZY_TOKEN_LENGTH:
            for column in (cls.campground_name, cls.recreation_area_name, cls.city):
                # %> is the indexable commutator of word_similarity's <% operator.
                matches.append(column.bool_op("%>")(token))
                fuzzy_scores.append(func.word_similarity(token, column))
        token_filters.append(or_(*matches))

    query = func.to_tsquery(config, " & ".join(f"{token}:*" for token in tokens))
    rank = func.ts_rank_cd(vector, query, 32) * 100
    fuzzy_rank = func.greatest(*fuzzy_scores) * 10 if fuzzy_scores else 0
    score = (_name_match_score(cls=cls, term=term_cleaned) + rank + fuzzy_rank).label(
        "total_score"
    )
    return and_(*token_filters), score


def _build_text_search(
    cls: type[Search],
    term: str,
    *,
    dialect_name: str = "sqlite",
) -> tuple[Any | None, Any | None]:
    """
    Build text match filter and ranking score expression for a search term.

    Parameters
    ----------
    cls : type[Search]
        The Search model class.
    term : str
        The raw search string.
    dialect_name : str
        The active database dialect name ('sqlite' or 'postgresql').

    Returns
    -------
    tuple[Any | None, Any | None]
        A tuple of (text_filter_expression, total_score_expression).
    """
    term_cleaned = " ".join(term.lower().split())
    if not term_cleaned:
        return None, None

    if dialect_name == "postgresql":
        return _build_postgres_text_search(cls=cls, term_cleaned=term_cleaned)
    return _build_sqlite_text_search(cls=cls, term_cleaned=term_cleaned)


async def build_search_filters(
    cls: type[Search],
    session: AsyncSession,
    term: str = "",
    *,
    provider_ids: Sequence[int] | None = None,
    entity_types: Sequence[str] | None = None,
    state: str | None = None,
    has_electric: bool | None = None,
    pets_allowed: bool | None = None,
    min_rv_length: int | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_miles: float | None = None,
    dialect_name: str | None = None,
) -> tuple[list[Any], Any | None]:
    """Share exact attribute and dialect-specific text matching with map queries."""
    filters = _build_attribute_filters(
        cls=cls,
        provider_ids=provider_ids,
        entity_types=entity_types,
        state=state,
        has_electric=has_electric,
        pets_allowed=pets_allowed,
        min_rv_length=min_rv_length,
        lat=lat,
        lng=lng,
        radius_miles=radius_miles,
    )

    bind = session.bind or session.get_bind()
    active_dialect = dialect_name or (bind.dialect.name if bind else "sqlite")

    if active_dialect == "postgresql" and term.strip():
        await session.execute(
            select(
                func.set_config(
                    "pg_trgm.word_similarity_threshold",
                    PG_WORD_SIMILARITY_THRESHOLD,
                    True,
                )
            )
        )

    text_filter, total_score = _build_text_search(
        cls=cls,
        term=term,
        dialect_name=active_dialect,
    )
    if text_filter is not None:
        filters.append(text_filter)
    return filters, total_score


async def _compute_facets(
    cls: type[Search],
    session: AsyncSession,
    filters: list[Any],
) -> dict[str, dict[str, int]]:
    """
    Compute facet aggregations for providers, states, and entity types.

    Parameters
    ----------
    cls : type[Search]
        The Search model class.
    session : AsyncSession
        Active database session.
    filters : list[Any]
        Applied filter expressions.

    Returns
    -------
    dict[str, dict[str, int]]
        Aggregated facet counts by category.
    """
    prov_stmt = select(cls.provider_name, func.count(cls.id))
    if filters:
        prov_stmt = prov_stmt.where(and_(*filters))
    prov_stmt = prov_stmt.group_by(cls.provider_name)
    prov_res = (await session.execute(prov_stmt)).all()
    facets_prov = {row[0]: row[1] for row in prov_res if row[0]}

    state_stmt = select(cls.state, func.count(cls.id))
    if filters:
        state_stmt = state_stmt.where(and_(*filters))
    state_stmt = (
        state_stmt.where(cls.state.isnot(None))
        .group_by(cls.state)
        .order_by(func.count(cls.id).desc())
        .limit(MAX_FACET_STATES)
    )
    state_res = (await session.execute(state_stmt)).all()
    facets_state = {row[0]: row[1] for row in state_res if row[0]}

    ent_stmt = select(cls.entity_type, func.count(cls.id))
    if filters:
        ent_stmt = ent_stmt.where(and_(*filters))
    ent_stmt = ent_stmt.group_by(cls.entity_type)
    ent_res = (await session.execute(ent_stmt)).all()
    facets_ent = {row[0]: row[1] for row in ent_res if row[0]}

    return {
        "providers": facets_prov,
        "states": facets_state,
        "entity_types": facets_ent,
    }


def _apply_ordering(
    cls: type[Search],
    stmt: Any,
    sort_by: str,
    total_score: Any | None,
) -> Any:
    """
    Apply sorting order to the search query.

    Parameters
    ----------
    cls : type[Search]
        The Search model class.
    stmt : Any
        The SQLAlchemy select statement.
    sort_by : str
        Sorting strategy identifier.
    total_score : Any | None
        Optional relevance score expression.

    Returns
    -------
    Any
        The ordered SQLAlchemy statement.
    """
    if sort_by == "name_asc":
        return stmt.order_by(
            func.lower(
                func.coalesce(cls.campground_name, cls.recreation_area_name)
            ).asc(),
            cls.id,
        )
    if sort_by == "name_desc":
        return stmt.order_by(
            func.lower(
                func.coalesce(cls.campground_name, cls.recreation_area_name)
            ).desc(),
            cls.id,
        )
    if total_score is not None:
        return stmt.order_by(
            total_score.desc(),
            func.lower(func.coalesce(cls.campground_name, cls.recreation_area_name)),
            cls.id,
        )
    return stmt.order_by(
        cls.provider_name,
        func.lower(func.coalesce(cls.campground_name, cls.recreation_area_name)).asc(),
        cls.id,
    )


class Search(Base):
    """
    Search Model for recreation areas and campgrounds.
    """

    __tablename__ = "search"

    id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(128),
        index=True,
    )
    provider_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    provider_name: Mapped[str] = mapped_column(
        String(128),
    )
    recreation_area_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    recreation_area_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    campground_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    campground_name: Mapped[str | None] = mapped_column(
        String(128),
        index=True,
        nullable=True,
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    state: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    country: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    reservable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    campsite_types: Mapped[list[str] | None] = mapped_column(
        ARRAY(String).with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    has_electric: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    has_water: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    has_sewer: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    pets_allowed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    ada_accessible: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    max_rv_length: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    @classmethod
    async def search(
        cls,
        session: AsyncSession,
        term: str = "",
        *,
        provider_ids: Sequence[int] | None = None,
        entity_types: Sequence[str] | None = None,
        state: str | None = None,
        has_electric: bool | None = None,
        pets_allowed: bool | None = None,
        min_rv_length: int | None = None,
        lat: float | None = None,
        lng: float | None = None,
        radius_miles: float | None = None,
        limit: int = 25,
        offset: int = 0,
        sort_by: str = "relevance",
        dialect_name: str | None = None,
        include_metadata: bool = True,
    ) -> tuple[list[Self], int, dict[str, Any]]:
        """
        Execute composable multi-criteria search with total count and facet aggregations.

        Parameters
        ----------
        session : AsyncSession
            Active database session.
        term : str
            Search query string.
        provider_ids : Sequence[int] | None
            Filter by provider IDs.
        entity_types : Sequence[str] | None
            Filter by entity types (e.g. RecreationArea, Campground).
        state : str | None
            Filter by state abbreviation.
        has_electric : bool | None
            Filter by electric hookup availability.
        pets_allowed : bool | None
            Filter by pet allowance.
        min_rv_length : int | None
            Filter by minimum RV length accommodation.
        lat : float | None
            Center latitude for geographic distance search.
        lng : float | None
            Center longitude for geographic distance search.
        radius_miles : float | None
            Bounding radius in miles.
        limit : int
            Maximum number of results to return.
        offset : int
            Result offset for pagination.
        sort_by : str
            Sorting strategy ('relevance', 'name_asc', 'name_desc').
        dialect_name : str | None
            Optional database dialect name override ('postgresql' or 'sqlite').
        include_metadata : bool
            Compute totals and facets; disable for autocomplete requests.

        Returns
        -------
        tuple[list[Self], int, dict[str, Any]]
            A tuple of (result_rows, total_matching_count, facet_dictionary).
        """
        filters, total_score = await build_search_filters(
            cls=cls,
            session=session,
            term=term,
            provider_ids=provider_ids,
            entity_types=entity_types,
            state=state,
            has_electric=has_electric,
            pets_allowed=pets_allowed,
            min_rv_length=min_rv_length,
            lat=lat,
            lng=lng,
            radius_miles=radius_miles,
            dialect_name=dialect_name,
        )

        total_count = 0
        facets: dict[str, Any] = {}
        if include_metadata:
            count_stmt = select(func.count(cls.id))
            if filters:
                count_stmt = count_stmt.where(and_(*filters))
            total_count = (await session.execute(count_stmt)).scalar() or 0
            facets = await _compute_facets(cls=cls, session=session, filters=filters)

        stmt = select(cls, total_score) if total_score is not None else select(cls)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = _apply_ordering(
            cls=cls,
            stmt=stmt,
            sort_by=sort_by,
            total_score=total_score,
        )
        stmt = stmt.offset(offset).limit(limit)

        res = await session.execute(stmt)
        if total_score is not None:
            rows = [r[0] for r in res.all()]
        else:
            rows = list(res.scalars().all())

        return rows, total_count, facets

    @classmethod
    async def algorithm(
        cls,
        session: AsyncSession,
        term: str = "",
        *,
        limit: int = 25,
        offset: int = 0,
        provider_ids: Sequence[int] | None = None,
        entity_types: Sequence[str] | None = None,
        state: str | None = None,
        has_electric: bool | None = None,
        pets_allowed: bool | None = None,
        min_rv_length: int | None = None,
        lat: float | None = None,
        lng: float | None = None,
        radius_miles: float | None = None,
        sort_by: str = "relevance",
        dialect_name: str | None = None,
    ) -> list[Self]:
        """
        Search the Search table given a search term and optional filters.
        """
        rows, _, _ = await cls.search(
            session=session,
            term=term,
            provider_ids=provider_ids,
            entity_types=entity_types,
            state=state,
            has_electric=has_electric,
            pets_allowed=pets_allowed,
            min_rv_length=min_rv_length,
            lat=lat,
            lng=lng,
            radius_miles=radius_miles,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            dialect_name=dialect_name,
            include_metadata=False,
        )
        return rows
