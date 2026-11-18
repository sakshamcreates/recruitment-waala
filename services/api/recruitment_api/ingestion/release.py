"""Scheduled release of already reviewed records from an explicitly opted-in ATS."""

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import schema
from ..admin import perform_transition
from ..contracts import Transition, now
from ..database import engine
from .runner import approved, items, jobs, polling, queue, sources


def release_reviewed(limit=50):
    publication = schema.publication
    details = schema.job_details
    later = items.alias("later")
    latest = (
        ~select(later.c.id)
        .where(
            later.c.source_id == items.c.source_id,
            later.c.external_key == items.c.external_key,
            or_(
                later.c.observed_at > items.c.observed_at,
                (later.c.observed_at == items.c.observed_at) & (later.c.id > items.c.id),
            ),
        )
        .exists()
    )
    statement = (
        select(jobs.c.id, publication.c.version)
        .join(publication, publication.c.job_id == jobs.c.id)
        .join(details, details.c.job_id == jobs.c.id)
        .join(items, items.c.id == publication.c.source_item_id)
        .join(queue, queue.c.item_id == items.c.id)
        .join(sources, sources.c.id == items.c.source_id)
        .join(polling, polling.c.source_id == sources.c.id)
        .where(
            *approved(),
            latest,
            queue.c.state == "accepted",
            jobs.c.status == "draft",
            jobs.c.category == "corporate_job",
            publication.c.review_state == "approved",
            publication.c.is_demo.is_(False),
            publication.c.verified_at.is_not(None),
            details.c.apply_url.is_not(None),
            items.c.observed_at >= sources.c.approved_at,
            polling.c.configuration["publication_policy"].astext == "release_reviewed_ats",
            or_(jobs.c.expires_at.is_(None), jobs.c.expires_at > now()),
            or_(details.c.application_closes_at.is_(None), details.c.application_closes_at > now()),
        )
        .order_by(publication.c.verified_at, jobs.c.id)
        .limit(limit)
    )
    with Session(engine()) as db:
        entries = db.execute(statement).all()
        db.rollback()
        count = 0
        for job_id, version in entries:
            try:
                perform_transition(
                    job_id,
                    Transition(
                        version=version,
                        action="publish",
                        reason="Scheduled release of manually verified ATS observation",
                    ),
                    db,
                    scheduled=True,
                )
                count += 1
            except HTTPException as error:
                if error.status_code not in {404, 409, 422}:
                    raise
        return count
