from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .. import schema
from ..contracts import now
from .himalayas_policy import employer_slug


def employer_id(db, provenance):
    organisations = schema.organisations
    slug = employer_slug(provenance["company_slug"])
    organisation_id = db.scalar(
        pg_insert(organisations)
        .values(slug=slug, name=provenance["company_name"])
        .on_conflict_do_nothing(index_elements=[organisations.c.slug])
        .returning(organisations.c.id)
    )
    return organisation_id or db.scalar(
        select(organisations.c.id).where(organisations.c.slug == slug)
    )


def status_batch(db, source_id, limit):
    runs, metrics = schema.ingestion_runs, schema.ingestion_run_metrics
    publication, items, jobs = schema.publication, schema.source_items, schema.jobs
    cursor = db.scalar(
        select(metrics.c.counts["status_cursor"].astext)
        .join(runs, runs.c.id == metrics.c.run_id)
        .where(runs.c.source_id == source_id, metrics.c.counts.has_key("status_cursor"))
        .order_by(runs.c.started_at.desc(), runs.c.id.desc())
        .limit(1)
    )
    candidates = (
        select(jobs.c.id, jobs.c.official_url)
        .join(publication, publication.c.job_id == jobs.c.id)
        .join(items, items.c.id == publication.c.source_item_id)
        .where(items.c.source_id == source_id, jobs.c.status == "published")
        .order_by(jobs.c.id)
        .limit(limit)
    )
    rows = db.execute(candidates.where(jobs.c.id > UUID(cursor)) if cursor else candidates).all()
    if not rows and cursor:
        rows = db.execute(candidates).all()
    return rows


def withdraw_confirmed(db, source_id, job_id, guid, reason):
    """Withdraw only the current published record owned by this provider."""
    publication, items, jobs = schema.publication, schema.source_items, schema.jobs
    published = db.execute(
        select(jobs.c.id, publication.c.source_item_id)
        .join(publication, publication.c.job_id == jobs.c.id)
        .join(items, items.c.id == publication.c.source_item_id)
        .where(
            jobs.c.id == job_id,
            jobs.c.status == "published",
            jobs.c.official_url == guid,
            items.c.source_id == source_id,
        )
        .with_for_update(of=[jobs, publication])
    ).one_or_none()
    if not published:
        return False
    db.execute(update(jobs).where(jobs.c.id == job_id).values(status="withdrawn", updated_at=now()))
    db.execute(
        update(publication)
        .where(publication.c.job_id == job_id)
        .values(version=publication.c.version + 1)
    )
    db.execute(
        insert(schema.change_events).values(
            job_id=job_id,
            source_item_id=published.source_item_id,
            event_type="withdraw",
            before_values={"status": "published"},
            after_values={
                "status": "withdrawn",
                "reason": reason,
                "provider_endpoint": "job_status",
            },
        )
    )
    return True
