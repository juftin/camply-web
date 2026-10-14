"""
Search
"""

from __future__ import annotations

import math
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
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base

MIN_SEARCH_TOKEN_LENGTH: int = 2
"""Minimum character length for query tokens in full-text search matching."""

MILES_PER_LATITUDE_DEGREE: float = 69.0
"""Approximate miles per degree of latitude for bounding box calculation."""

MAX_FACET_STATES: int = 50
"""Maximum number of unique states returned in search facet aggregations."""

PG_TRGM_SIMILARITY_THRESHOLD: float = 0.3
"""Similarity threshold for pg_trgm fuzzy matching."""

PG_TRGM_SCORE_MULTIPLIER: float = 100.0
"""Score multiplier for pg_trgm similarity values."""

EXACT_MATCH_SCORE: int = 100
"""Score awarded for an exact string match."""

PREFIX_MATCH_SCORE: int = 75
"""Score awarded for a prefix string match."""

SUBSTRING_MATCH_SCORE: int = 50
"""Score awarded for a substring string match."""

CITY_MATCH_SCORE: int = 30
"""Score awarded for a city substring match."""

FALLBACK_MATCH_SCORE: int = 10
"""Fallback match score awarded when a match condition is met."""

RECAREA_ENTITY_SCORE: int = 100
"""Bonus score awarded to RecreationArea entities."""

CAMPGROUND_ENTITY_SCORE: int = 50
"""Bonus score awarded to Campground entities."""


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
    if has_electric is True:
        filters.append(cls.has_electric.is_(True))
    if pets_allowed is True:
        filters.append(cls.pets_allowed.is_(True))
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
    exact = term_cleaned
    prefix = f"{term_cleaned}%"
    substring = f"%{term_cleaned}%"

    tokens = [t for t in term_cleaned.split() if len(t) >= MIN_SEARCH_TOKEN_LENGTH]
    if not tokens:
        tokens = [term_cleaned]

    def _token_cond(tok: str) -> Any:
        tok_sub = f"%{tok}%"
        return or_(
            func.lower(cls.recreation_area_name).like(tok_sub),
            func.lower(cls.campground_name).like(tok_sub),
            func.lower(cls.city).like(tok_sub),
            func.lower(cls.state).like(tok_sub),
        )

    text_filter = (
        and_(*[_token_cond(tok) for tok in tokens])
        if len(tokens) > 1
        else _token_cond(tokens[0])
    )

    match_score = case(
        (func.lower(cls.recreation_area_name) == exact, EXACT_MATCH_SCORE),
        (func.lower(cls.campground_name) == exact, EXACT_MATCH_SCORE),
        (func.lower(cls.recreation_area_name).like(prefix), PREFIX_MATCH_SCORE),
        (func.lower(cls.campground_name).like(prefix), PREFIX_MATCH_SCORE),
        (func.lower(cls.recreation_area_name).like(substring), SUBSTRING_MATCH_SCORE),
        (func.lower(cls.campground_name).like(substring), SUBSTRING_MATCH_SCORE),
        (func.lower(cls.city).like(substring), CITY_MATCH_SCORE),
        else_=FALLBACK_MATCH_SCORE,
        value=None,
    ).label("match_score")

    entity_score = case(
        (cls.entity_type == "RecreationArea", RECAREA_ENTITY_SCORE),
        (cls.entity_type == "Campground", CAMPGROUND_ENTITY_SCORE),
        else_=0,
    ).label("entity_score")

    total_score = (entity_score + match_score).label("total_score")
    return text_filter, total_score


def _build_postgres_text_search(
    cls: type[Search],
    term_cleaned: str,
) -> tuple[Any, Any]:
    """
    Build PostgreSQL pg_trgm text match filter and ranking score expression.

    Combines standard substring matching with trigram similarity thresholding
    to provide fuzzy typo tolerance and ranking.

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
    exact = term_cleaned
    prefix = f"{term_cleaned}%"
    substring = f"%{term_cleaned}%"

    tokens = [t for t in term_cleaned.split() if len(t) >= MIN_SEARCH_TOKEN_LENGTH]
    if not tokens:
        tokens = [term_cleaned]

    def _token_cond(tok: str) -> Any:
        tok_sub = f"%{tok}%"
        return or_(
            func.lower(cls.recreation_area_name).like(tok_sub),
            func.lower(cls.campground_name).like(tok_sub),
            func.lower(cls.city).like(tok_sub),
            func.lower(cls.state).like(tok_sub),
        )

    token_filter = (
        and_(*[_token_cond(tok) for tok in tokens])
        if len(tokens) > 1
        else _token_cond(tokens[0])
    )

    fuzzy_cond = or_(
        func.similarity(
            func.lower(func.coalesce(cls.campground_name, "")),
            term_cleaned,
        )
        >= PG_TRGM_SIMILARITY_THRESHOLD,
        func.similarity(
            func.lower(func.coalesce(cls.recreation_area_name, "")),
            term_cleaned,
        )
        >= PG_TRGM_SIMILARITY_THRESHOLD,
        func.word_similarity(
            term_cleaned,
            func.lower(func.coalesce(cls.campground_name, "")),
        )
        >= PG_TRGM_SIMILARITY_THRESHOLD,
        func.word_similarity(
            term_cleaned,
            func.lower(func.coalesce(cls.recreation_area_name, "")),
        )
        >= PG_TRGM_SIMILARITY_THRESHOLD,
    )

    text_filter = or_(token_filter, fuzzy_cond)

    case_score = case(
        (func.lower(cls.recreation_area_name) == exact, EXACT_MATCH_SCORE),
        (func.lower(cls.campground_name) == exact, EXACT_MATCH_SCORE),
        (func.lower(cls.recreation_area_name).like(prefix), PREFIX_MATCH_SCORE),
        (func.lower(cls.campground_name).like(prefix), PREFIX_MATCH_SCORE),
        (func.lower(cls.recreation_area_name).like(substring), SUBSTRING_MATCH_SCORE),
        (func.lower(cls.campground_name).like(substring), SUBSTRING_MATCH_SCORE),
        (func.lower(cls.city).like(substring), CITY_MATCH_SCORE),
        else_=FALLBACK_MATCH_SCORE,
        value=None,
    )

    trgm_score = (
        func.greatest(
            func.similarity(
                func.lower(func.coalesce(cls.campground_name, "")),
                term_cleaned,
            ),
            func.similarity(
                func.lower(func.coalesce(cls.recreation_area_name, "")),
                term_cleaned,
            ),
            func.word_similarity(
                term_cleaned,
                func.lower(func.coalesce(cls.campground_name, "")),
            ),
            func.word_similarity(
                term_cleaned,
                func.lower(func.coalesce(cls.recreation_area_name, "")),
            ),
        )
        * PG_TRGM_SCORE_MULTIPLIER
    )

    match_score = func.greatest(case_score, trgm_score).label("match_score")

    entity_score = case(
        (cls.entity_type == "RecreationArea", RECAREA_ENTITY_SCORE),
        (cls.entity_type == "Campground", CAMPGROUND_ENTITY_SCORE),
        else_=0,
    ).label("entity_score")

    total_score = (entity_score + match_score).label("total_score")
    return text_filter, total_score


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
    term_cleaned = term.strip().lower()
    if not term_cleaned:
        return None, None

    if dialect_name == "postgresql":
        return _build_postgres_text_search(cls=cls, term_cleaned=term_cleaned)
    return _build_sqlite_text_search(cls=cls, term_cleaned=term_cleaned)


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
            func.coalesce(cls.campground_name, cls.recreation_area_name).asc()
        )
    if sort_by == "name_desc":
        return stmt.order_by(
            func.coalesce(cls.campground_name, cls.recreation_area_name).desc()
        )
    if total_score is not None:
        return stmt.order_by(total_score.desc(), cls.provider_name)
    return stmt.order_by(
        cls.provider_name,
        func.coalesce(cls.campground_name, cls.recreation_area_name).asc(),
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

        Returns
        -------
        tuple[list[Self], int, dict[str, Any]]
            A tuple of (result_rows, total_matching_count, facet_dictionary).
        """
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

        text_filter, total_score = _build_text_search(
            cls=cls,
            term=term,
            dialect_name=active_dialect,
        )
        if text_filter is not None:
            filters.append(text_filter)

        count_stmt = select(func.count(cls.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total_count = (await session.execute(count_stmt)).scalar() or 0

        facets = await _compute_facets(
            cls=cls,
            session=session,
            filters=filters,
        )

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
        )
        return rows
