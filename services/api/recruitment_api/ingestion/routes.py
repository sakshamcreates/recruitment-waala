from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from .. import schema
from ..admin import audit, evidence, internal_operator, locked, save, state
from ..catalogue import Database
from ..contracts import Draft, DraftState, Input, Short, now
from ..models import Details, Organisation
from .policy import PollConfig, SourceInput
from .runner import approved, items, metrics, polling, queue, runs, sources

router = APIRouter(
    prefix="/api/v1/admin/ingestion", tags=["ingestion"], dependencies=[Depends(internal_operator)]
)
Limit = Annotated[int, Query(ge=1, le=100)]


class Enable(Input):
    enabled: bool


class Review(Input):
    action: Literal["accept", "reject"]
    version: int | None = None
    reason: Short


@router.post("/sources", status_code=201)
def register(payload: SourceInput, db: Database):
    try:
        with db.begin():
            if db.get(Organisation, payload.organisation_id) is None:
                raise HTTPException(422, "Unknown source organisation.")
            config = payload.config
            kind = {
                "greenhouse": "approved_api",
                "lever": "approved_api",
                "json": "authorised_feed",
                "government_html": "official_page",
                "government_pdf": "official_page",
            }[config.adapter]
            source_id = db.scalar(
                insert(sources)
                .values(
                    slug=payload.slug,
                    organisation_id=payload.organisation_id,
                    endpoint_url=payload.endpoint_url,
                    adapter_kind=kind,
                    enabled=payload.enabled,
                    approved_at=now(),
                    permission_reference=config.approval_reference,
                )
                .returning(sources.c.id)
            )
            db.execute(
                insert(polling).values(
                    source_id=source_id,
                    configuration=config.model_dump(mode="json"),
                    next_poll_at=now(),
                )
            )
    except IntegrityError:
        raise HTTPException(409, "Source slug or configuration conflict.") from None
    return {"id": source_id, "enabled": payload.enabled}


@router.patch("/sources/{source_id}")
def enable(source_id: UUID, payload: Enable, db: Database):
    with db.begin():
        source = (
            db.execute(
                select(sources).join(polling).where(sources.c.id == source_id).with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if not source:
            raise HTTPException(404, "Configured source unavailable.")
        if payload.enabled and (
            not source["approved_at"]
            or source["approved_at"] > now()
            or not (source["permission_reference"] or "").strip()
        ):
            raise HTTPException(409, "Record source approval before enabling polling.")
        db.execute(update(sources).where(sources.c.id == source_id).values(enabled=payload.enabled))
        return {"id": source_id, "enabled": payload.enabled}


@router.put("/sources/{source_id}/config")
def replace_config(source_id: UUID, payload: PollConfig, db: Database):
    with db.begin():
        source = (
            db.execute(
                select(sources, polling.c.configuration)
                .join(polling)
                .where(sources.c.id == source_id)
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if not source:
            raise HTTPException(404, "Configured source unavailable.")
        if source["enabled"] or source["configuration"]["adapter"] != payload.adapter:
            raise HTTPException(409, "Disable the source and retain its adapter to reconfigure it.")
        try:
            payload.validate_endpoint(source["endpoint_url"])
        except ValueError:
            raise HTTPException(422, "Configuration excludes the existing endpoint.") from None
        db.execute(
            update(sources)
            .where(sources.c.id == source_id)
            .values(
                approved_at=now(),
                permission_reference=payload.approval_reference,
            )
        )
        db.execute(
            update(polling)
            .where(polling.c.source_id == source_id)
            .values(
                configuration=payload.model_dump(mode="json"),
                next_poll_at=now(),
                last_success_at=None,
                last_failure_at=None,
                consecutive_failures=0,
            )
        )
        return {"id": source_id, "enabled": False}


@router.get("/sources")
def health(db: Database, limit: Limit = 50):
    rows = db.execute(
        select(
            sources.c.id,
            sources.c.slug,
            sources.c.enabled,
            sources.c.approved_at,
            sources.c.organisation_id,
            sources.c.endpoint_url,
            polling,
        )
        .join(polling, polling.c.source_id == sources.c.id)
        .order_by(sources.c.slug)
        .limit(limit)
    ).mappings()
    return [
        {
            **dict(row),
            "health": "disabled"
            if not row["enabled"]
            else "degraded"
            if row["consecutive_failures"]
            else "healthy"
            if row["last_success_at"]
            else "pending",
        }
        for row in rows
    ]


@router.get("/runs")
def recent_runs(db: Database, source_id: UUID | None = None, limit: Limit = 50):
    statement = (
        select(runs, metrics.c.counts, (runs.c.finished_at - runs.c.started_at).label("duration"))
        .join(metrics, metrics.c.run_id == runs.c.id, isouter=True)
        .where(runs.c.run_key.startswith("poll:"))
    )
    if source_id:
        statement = statement.where(runs.c.source_id == source_id)
    return [
        dict(row)
        for row in db.execute(
            statement.order_by(runs.c.started_at.desc(), runs.c.id).limit(limit)
        ).mappings()
    ]


@router.get("/candidates")
def candidates(db: Database, source_id: UUID | None = None, limit: Limit = 50):
    statement = (
        select(
            queue,
            items.c.job_id,
            items.c.source_id,
            items.c.source_url,
            items.c.observed_at,
            schema.publication.c.version,
        )
        .join(items, items.c.id == queue.c.item_id)
        .outerjoin(schema.publication, schema.publication.c.job_id == items.c.job_id)
        .where(queue.c.state.in_(("pending_review", "withdrawal_review", "validation_failed")))
    )
    if source_id:
        statement = statement.where(items.c.source_id == source_id)
    return [
        dict(row)
        for row in db.execute(
            statement.order_by(items.c.observed_at.desc(), items.c.id).limit(limit)
        ).mappings()
    ]


@router.post("/candidates/{item_id}/review")
def review(item_id: UUID, payload: Review, db: Database) -> DraftState | dict[str, str]:
    with db.begin():
        candidate = (
            db.execute(
                select(
                    queue,
                    items.c.job_id,
                    items.c.source_id,
                    items.c.external_key,
                    items.c.observed_at,
                )
                .join(items, items.c.id == queue.c.item_id)
                .where(queue.c.item_id == item_id)
            )
            .mappings()
            .one_or_none()
        )
        if not candidate:
            raise HTTPException(404, "Candidate unavailable.")
        if candidate["job_id"] and payload.version is not None:
            job, publication = locked(db, candidate["job_id"], payload.version)
        elif payload.action == "reject" and not candidate["job_id"]:
            job = publication = None
        else:
            raise HTTPException(422, "Provide the associated opportunity version.")
        current = db.scalar(
            select(queue.c.state).where(queue.c.item_id == item_id).with_for_update()
        )
        if current not in {"pending_review", "withdrawal_review", "validation_failed"}:
            raise HTTPException(409, "Candidate was already reviewed.")
        if payload.action == "reject":
            db.execute(update(queue).where(queue.c.item_id == item_id).values(state="rejected"))
            if job:
                publication.version += 1
                audit(
                    db,
                    job.id,
                    "ingestion_rejected",
                    after={"reason": payload.reason},
                    source_item_id=item_id,
                )
                return state(job, publication)
            return {"state": "rejected"}

        valid_source = db.scalar(
            select(sources.c.id)
            .where(
                sources.c.id == candidate["source_id"],
                *approved(),
                sources.c.approved_at <= candidate["observed_at"],
            )
            .with_for_update(read=True)
        )
        if not valid_source:
            raise HTTPException(409, "Candidate source approval is unavailable.")
        latest = db.scalar(
            select(items.c.id)
            .where(
                items.c.source_id == candidate["source_id"],
                items.c.external_key == candidate["external_key"],
            )
            .order_by(items.c.observed_at.desc(), items.c.id.desc())
            .limit(1)
        )
        if latest != item_id or current == "validation_failed":
            raise HTTPException(409, "Use the latest valid observation.")
        if current == "withdrawal_review":
            if (
                db.scalar(select(items.c.source_id).where(items.c.id == publication.source_item_id))
                != candidate["source_id"]
            ):
                raise HTTPException(409, "Withdrawal requires evidence from the published source.")
            if job.status != "published":
                raise HTTPException(409, "Only published opportunities can be withdrawn.")
            job.status = "withdrawn"
            event, decision = "withdraw", "withdraw"
        else:
            if job.status not in {"draft", "published"}:
                raise HTTPException(409, "Opportunity is unavailable for correction.")
            draft = Draft.model_validate(candidate["payload"])
            if (
                draft.organisation_id,
                draft.details.category,
                draft.cycle_key,
                draft.opportunity_key,
            ) != (job.organisation_id, job.category, job.cycle_key, job.opportunity_key):
                raise HTTPException(409, "Canonical identity changed.")
            save(db, draft, job, db.get(Details, job.id))
            evidence(db, job, item_id)
            publication.review_state = "approved"
            publication.source_item_id = item_id
            publication.verified_at = now()
            event, decision = ("correction" if job.status == "published" else "approve"), "approve"
        publication.version += 1
        db.execute(update(queue).where(queue.c.item_id == item_id).values(state="accepted"))
        db.execute(
            insert(schema.moderation_reviews).values(
                job_id=job.id,
                source_item_id=item_id,
                decision=decision,
                reason=payload.reason,
            )
        )
        audit(db, job.id, event, after={"reason": payload.reason}, source_item_id=item_id)
        db.execute(update(schema.jobs).where(schema.jobs.c.id == job.id).values(updated_at=now()))
        return state(job, publication)
