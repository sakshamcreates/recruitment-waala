import math
from datetime import timedelta
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as QueryParameter
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from . import schema
from .contracts import (
    CATEGORIES,
    Attribution,
    Opportunity,
    Page,
    PublicChange,
    Query,
    https_origin,
    now,
)
from .database import get_session
from .ingestion.policy import in_scope
from .models import Change, Details, Job, Observation, Organisation, Publication, Source
from .pagination import after, decode, encode

router = APIRouter(prefix="/api/v1", tags=["catalogue"])
Database = Annotated[Session, Depends(get_session)]
expiry = func.least(Job.expires_at, Details.application_closes_at)
fields = Details.category_fields
facets = {
    "state": fields["state"].astext,
    "qualification": fields["qualification"].astext,
    "organisation": Organisation.name,
    "experience": fields["experience"].astext,
    "type": func.coalesce(fields["employment"].astext, fields["compensation"].astext),
    "mode": fields["mode"].astext,
    "duration": fields["duration"].astext,
}


def visible(*, listing=False):
    polling = schema.source_polling
    statement = (
        select(
            Job, Details, Organisation, Publication, Observation, Source, polling.c.configuration
        )
        .join(Details, Details.job_id == Job.id)
        .join(Organisation, Organisation.id == Job.organisation_id)
        .join(Publication, Publication.job_id == Job.id)
        .join(
            Observation,
            (Observation.id == Publication.source_item_id) & (Observation.job_id == Job.id),
        )
        .join(
            Source,
            (Source.id == Observation.source_id) & (Source.organisation_id == Organisation.id),
        )
        .outerjoin(polling, polling.c.source_id == Source.id)
        .where(
            or_(polling.c.source_id.is_(None), Observation.observed_at >= Source.approved_at),
            Job.category.in_(CATEGORIES),
            Job.published_at <= func.statement_timestamp(),
            Publication.review_state == "approved",
            Publication.verified_at.is_not(None),
            Publication.is_demo.is_(False),
            Source.enabled.is_(True),
            Source.approved_at <= func.statement_timestamp(),
            func.length(func.trim(Source.permission_reference)) > 0,
            Job.official_url == Observation.source_url,
        )
    )
    if listing:
        return statement.where(
            Job.status == "published", or_(expiry.is_(None), expiry > func.statement_timestamp())
        )
    return statement.where(Job.status.in_(("published", "expired", "withdrawn")))


def approved_url(value: str | None, reference: str) -> str | None:
    try:
        if value and https_origin(value) == https_origin(reference):
            return value
    except ValueError:
        pass
    return None


def source_links(notice, application, endpoint, config):
    if config is None:
        official = approved_url(notice, endpoint)
        return official, approved_url(application, official) if official else None
    official = notice if in_scope(notice, config.get("notice_prefixes", [])) else None
    apply = (
        application
        if official and in_scope(application, config.get("application_prefixes", []))
        else None
    )
    return official, apply


def project(row) -> Opportunity:
    job, detail, organisation, publication, observation, source, config = row
    status = job.status
    if status == "published" and any(
        date and date <= now() for date in (job.expires_at, detail.application_closes_at)
    ):
        status = "expired"
    official, application = source_links(
        job.official_url, detail.apply_url, source.endpoint_url, config
    )
    return Opportunity(
        id=job.id,
        title=job.title,
        organisation=organisation.name,
        description=detail.description,
        location=detail.location,
        status=status,
        published_at=job.published_at,
        deadline=detail.application_closes_at,
        apply_url=application if status == "published" else None,
        details={**detail.category_fields, "category": job.category},
        provenance=Attribution(
            source=source.slug,
            official_url=official,
            observed_at=observation.observed_at,
            verified_at=publication.verified_at,
        ),
    )


@router.get("/opportunities", response_model=Page)
def opportunities(query: Annotated[Query, QueryParameter()], db: Database):
    base = visible(listing=True)
    if query.category:
        base = base.where(Job.category == query.category)
    statement = base
    for key, expression in facets.items():
        if value := getattr(query, key):
            statement = statement.where(expression == value)
    for token in query.q.split():
        # Literal substring matching supports partial titles and punctuation in reference numbers.
        haystack = func.concat_ws(
            " ",
            Job.title,
            Organisation.name,
            Details.description,
            Details.location,
            fields["reference"].astext,
            fields["stage"].astext,
            cast(fields["skills"], String),
            *facets.values(),
        )
        statement = statement.where(haystack.icontains(token, autoescape=True))
    if query.deadline:
        cutoff = now().astimezone(ZoneInfo("Asia/Kolkata"))
        cutoff += timedelta(days=7 if query.deadline == "week" else 30)
        statement = statement.where(
            Details.application_closes_at > func.statement_timestamp(),
            Details.application_closes_at <= cutoff,
        )
    ids = statement.with_only_columns(Job.id).subquery()
    total = db.scalar(select(func.count()).select_from(ids)) or 0
    position = decode(query)
    page = position.page if position else min(query.page, max(1, math.ceil(total / query.limit)))
    ordering = {
        "newest": [Job.published_at.desc()],
        "title": [func.lower(Job.title)],
        "deadline": [Details.application_closes_at.asc().nulls_last(), Job.published_at.desc()],
    }
    statement = statement.add_columns(func.lower(Job.title)).order_by(*ordering[query.sort], Job.id)
    if position:
        statement = statement.where(after(position, query.sort))
    else:
        statement = statement.offset((page - 1) * query.limit)
    rows = db.execute(statement.limit(query.limit + 1)).all()
    items = [project(row[:-1]) for row in rows[: query.limit]]
    next_cursor = None
    if len(rows) > query.limit and page < 10000:
        job, details, *_, normalized_title = rows[query.limit - 1]
        next_cursor = encode(
            query,
            page + 1,
            job.id,
            job.published_at,
            normalized_title,
            details.application_closes_at,
        )
    # One bounded round trip for facets, independent of the results page.
    values = {}
    projection = base.with_only_columns(
        *(column.label(key) for key, column in facets.items())
    ).subquery()
    for key in facets:
        column = projection.c[key]
        values[key] = (
            select(column.label("value"))
            .where(column.is_not(None))
            .distinct()
            .order_by(column)
            .limit(100)
            .subquery()
        )
    grouped = (
        db.execute(
            select(
                *(
                    select(func.array_agg(values[key].c.value)).scalar_subquery().label(key)
                    for key in facets
                )
            )
        )
        .mappings()
        .one()
    )
    values = {key: value or [] for key, value in grouped.items()}
    return Page(
        items=items,
        total=total,
        page=page,
        limit=query.limit,
        facets=values,
        next_cursor=next_cursor,
    )


@router.get("/categories")
def categories() -> tuple[str, ...]:
    return CATEGORIES


@router.get("/organisations")
def organisations(
    db: Database,
    limit: int = QueryParameter(20, ge=1, le=100),
    page: int = QueryParameter(1, ge=1, le=10000),
):
    rows = db.execute(
        visible(listing=True)
        .with_only_columns(Organisation.id, Organisation.name, Organisation.slug)
        .distinct()
        .order_by(Organisation.name, Organisation.id)
        .limit(limit)
        .offset((page - 1) * limit)
    )
    return [dict(row._mapping) for row in rows]


@router.get("/opportunities/{job_id}", response_model=Opportunity)
def detail(job_id: UUID, db: Database):
    row = db.execute(visible().where(Job.id == job_id)).one_or_none()
    if not row:
        raise HTTPException(404, "Opportunity unavailable.")
    return project(row)


@router.get("/changes", response_model=list[PublicChange])
@router.get("/opportunities/{job_id}/history", response_model=list[PublicChange])
def history(
    db: Database, job_id: UUID | None = None, limit: int = QueryParameter(20, ge=1, le=100)
):
    candidates = visible().with_only_columns(Job.id)
    if job_id:
        candidates = candidates.where(Job.id == job_id)
        if db.scalar(candidates) is None:
            raise HTTPException(404, "Opportunity unavailable.")
    rows = db.scalars(
        select(Change)
        .where(
            Change.job_id.in_(candidates),
            Change.event_type.in_(("publish", "withdraw", "correction")),
        )
        .order_by(Change.recorded_at.desc(), Change.id)
        .limit(limit)
    )
    return [
        PublicChange(
            id=row.id, job_id=row.job_id, event_type=row.event_type, recorded_at=row.recorded_at
        )
        for row in rows
    ]
