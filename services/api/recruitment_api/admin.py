import hashlib
from secrets import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from . import schema
from .catalogue import Database, source_links
from .contracts import Draft, DraftState, DraftUpdate, Transition, now
from .ingestion.himalayas_policy import employer_slug, identity
from .models import Details, Job, Observation, Organisation, Publication, Source
from .settings import setting


def internal_operator(authorization: Annotated[str | None, Header()] = None):
    if (
        setting("RW_ENV") not in {"development", "infrastructure"}
        or setting("RW_ADMIN_ENABLED") != "true"
    ):
        raise HTTPException(404, "Route unavailable.")
    keys = [
        key
        for name in ("RW_ADMIN_TOKEN", "RW_ADMIN_PREVIOUS_TOKEN")
        if (key := setting(name)) and len(key) >= 32 and key.isascii()
    ]
    scheme, _, token = (authorization or "").partition(" ")
    digest = hashlib.sha256(token.encode()).digest()
    matches = [compare_digest(digest, hashlib.sha256(key.encode()).digest()) for key in keys]
    if scheme.lower() != "bearer" or len(token) > 512 or not any(matches):
        raise HTTPException(
            401, "Internal credential required.", headers={"WWW-Authenticate": "Bearer"}
        )


router = APIRouter(
    prefix="/api/v1/admin/opportunities",
    tags=["editorial"],
    dependencies=[Depends(internal_operator)],
)


def state(job, publication):
    return DraftState(
        id=job.id,
        status=job.status,
        version=publication.version,
        review_state=publication.review_state,
    )


def audit(db, job_id, event, before=None, after=None, source_item_id=None):
    db.execute(
        insert(schema.change_events).values(
            job_id=job_id,
            event_type=event,
            before_values=before,
            after_values=after,
            source_item_id=source_item_id,
        )
    )


def save(db, draft, job, details):
    if db.get(Organisation, draft.organisation_id) is None:
        raise HTTPException(422, "Unknown organisation.")
    for name in (
        "organisation_id",
        "title",
        "cycle_key",
        "opportunity_key",
        "official_url",
        "expires_at",
    ):
        setattr(job, name, getattr(draft, name))
    job.category = draft.details.category
    details.description = draft.description
    details.location = draft.location
    details.apply_url = draft.apply_url
    details.application_closes_at = draft.deadline
    details.category_fields = draft.details.model_dump(mode="json", exclude={"category"})


def flush(db):
    try:
        db.flush()
    except IntegrityError:
        raise HTTPException(409, "Canonical identity or database constraint conflict.") from None


@router.post("", status_code=201)
def create(draft: Draft, db: Database) -> DraftState:
    with db.begin():
        job, details = Job(status="draft"), Details()
        save(db, draft, job, details)
        db.add(job)
        flush(db)
        details.job_id = job.id
        publication = Publication(job_id=job.id)
        db.add_all([details, publication])
        flush(db)
        audit(db, job.id, "create", after=draft.model_dump(mode="json"))
        return state(job, publication)


def locked(db, job_id, version):
    job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
    publication = db.get(Publication, job_id)
    if not job or not publication or publication.is_demo:
        raise HTTPException(404, "Editorial record unavailable.")
    if publication.version != version:
        raise HTTPException(409, "Editorial version conflict.")
    return job, publication


@router.put("/{job_id}")
def edit(job_id: UUID, draft: DraftUpdate, db: Database) -> DraftState:
    with db.begin():
        job, publication = locked(db, job_id, draft.version)
        if job.status != "draft" or publication.review_state not in {"draft", "rejected"}:
            raise HTTPException(409, "Only editable drafts can be updated.")
        details = db.get(Details, job_id)
        before = Draft(
            organisation_id=job.organisation_id,
            cycle_key=job.cycle_key,
            opportunity_key=job.opportunity_key,
            title=job.title,
            details={**details.category_fields, "category": job.category},
            description=details.description,
            location=details.location,
            official_url=job.official_url,
            apply_url=details.apply_url,
            deadline=details.application_closes_at,
            expires_at=job.expires_at,
        ).model_dump(mode="json")
        save(db, draft, job, details)
        publication.review_state = "draft"
        publication.version += 1
        publication.source_item_id = None
        publication.verified_at = None
        flush(db)
        audit(db, job_id, "edit", before, draft.model_dump(mode="json", exclude={"version"}))
        db.execute(update(Job).where(Job.id == job_id).values(updated_at=now()))
        return state(job, publication)


def evidence(db, job, source_item_id):
    row = db.execute(
        select(Observation, Source)
        .join(Source, Source.id == Observation.source_id)
        .where(
            Observation.id == source_item_id,
            Observation.job_id == job.id,
            Source.enabled.is_(True),
            Source.approved_at <= now(),
            Source.permission_reference.is_not(None),
        )
        .with_for_update(read=True)
    ).one_or_none()
    if row is None:
        raise HTTPException(422, "An approved observation tied to this draft is required.")
    observation, source = row
    details = db.get(Details, job.id)
    polling = schema.source_polling
    config = db.scalar(select(polling.c.configuration).where(polling.c.source_id == source.id))
    candidate = schema.ingestion_candidates
    record = (
        db.execute(select(candidate).where(candidate.c.item_id == observation.id))
        .mappings()
        .one_or_none()
    )
    candidate_state = record["state"] if record else None
    if config and config.get("adapter") == "himalayas":
        company = identity(observation.source_url)
        organisation = db.get(Organisation, job.organisation_id)
        stored = record["payload"] if record else None
        if (
            source.slug != "himalayas"
            or not company
            or not organisation
            or organisation.slug != employer_slug(company[0])
            or job.category != "corporate_job"
            or job.cycle_key
            != f"himalayas:{hashlib.sha256(observation.source_url.encode()).hexdigest()}"
            or not record
            or record["provenance"].get("india_eligible") is not True
            or not stored
            or not details.apply_url
            or details.apply_url != stored.get("apply_url")
        ):
            raise HTTPException(
                422, "Himalayas authorisation requires exact eligible API evidence."
            )
    elif source.organisation_id != job.organisation_id:
        raise HTTPException(422, "Source organisation does not match the opportunity.")
    if candidate_state is not None:
        latest = db.scalar(
            select(Observation.id)
            .where(
                Observation.source_id == source.id,
                Observation.external_key == observation.external_key,
            )
            .order_by(Observation.observed_at.desc(), Observation.id.desc())
            .limit(1)
        )
        if latest != observation.id:
            raise HTTPException(409, "Use the latest ingestion observation.")
    official, application = source_links(
        job.official_url, details.apply_url, source.endpoint_url, config
    )
    if (
        not (source.permission_reference or "").strip()
        or observation.source_url != job.official_url
        or not official
        or (details.apply_url and not application)
        or (config is not None and observation.observed_at < source.approved_at)
        or candidate_state in {"validation_failed", "withdrawal_review", "rejected"}
        or observation.observed_at > now()
    ):
        raise HTTPException(422, "Links and dates must match approved source evidence.")


@router.post("/{job_id}/transitions")
def transition(job_id: UUID, payload: Transition, db: Database) -> DraftState:
    return perform_transition(job_id, payload, db)


def perform_transition(
    job_id: UUID, payload: Transition, db, *, scheduled: bool = False
) -> DraftState:
    allowed = {
        "submit": ("draft", "draft"),
        "approve": ("draft", "submitted"),
        "reject": ("draft", "submitted"),
        "publish": ("draft", "approved"),
        "withdraw": ("published", "approved"),
    }
    with db.begin():
        job, publication = locked(db, job_id, payload.version)
        action = payload.action
        if scheduled and (action != "publish" or job.category != "corporate_job"):
            raise HTTPException(409, "Scheduled release requires an approved corporate draft.")
        if (job.status, publication.review_state) != allowed[action]:
            raise HTTPException(409, "Transition unavailable for this state.")
        if payload.source_item_id is not None and action != "approve":
            raise HTTPException(422, "Evidence can only be assigned at approval.")
        before = {"status": job.status, "review_state": publication.review_state}
        if action == "submit":
            publication.review_state = "submitted"
        elif action == "approve":
            evidence(db, job, payload.source_item_id)
            publication.source_item_id = payload.source_item_id
            publication.verified_at = now()
            publication.review_state = "approved"
            db.execute(
                update(schema.ingestion_candidates)
                .where(schema.ingestion_candidates.c.item_id == payload.source_item_id)
                .values(state="accepted")
            )
        elif action == "reject":
            publication.review_state = "rejected"
        elif action == "publish":
            evidence(db, job, publication.source_item_id)
            details = db.get(Details, job_id)
            if scheduled:
                item = schema.source_items
                polling = schema.source_polling
                candidate = schema.ingestion_candidates
                config = db.scalar(
                    select(polling.c.configuration)
                    .join(item, item.c.source_id == polling.c.source_id)
                    .join(candidate, candidate.c.item_id == item.c.id)
                    .where(item.c.id == publication.source_item_id, candidate.c.state == "accepted")
                )
                if (
                    not config
                    or config.get("publication_policy") != "release_reviewed_ats"
                    or config.get("adapter") not in {"greenhouse", "lever"}
                    or not publication.verified_at
                    or not details.apply_url
                ):
                    raise HTTPException(409, "Scheduled release policy is not satisfied.")
            if any(
                date and date <= now() for date in (job.expires_at, details.application_closes_at)
            ):
                raise HTTPException(409, "Opportunity is already expired.")
            job.status, job.published_at = "published", now()
        else:
            job.status = "withdrawn"
        if action in {"approve", "reject", "withdraw"}:
            db.execute(
                insert(schema.moderation_reviews).values(
                    job_id=job_id,
                    source_item_id=publication.source_item_id,
                    decision=action,
                    reason=payload.reason,
                )
            )
        publication.version += 1
        result = state(job, publication)
        audit(
            db,
            job_id,
            action,
            before,
            {**result.model_dump(mode="json"), "reason": payload.reason},
            publication.source_item_id,
        )
        db.execute(update(Job).where(Job.id == job_id).values(updated_at=now()))
        return result
