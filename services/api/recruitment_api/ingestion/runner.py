import json
import random
from datetime import timedelta
from uuid import UUID, uuid4

from billiard.exceptions import SoftTimeLimitExceeded
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .. import schema
from ..contracts import now
from ..database import engine
from .adapters import ADAPTERS, Discovery, digest
from .himalayas import HimalayasAdapter
from .himalayas_storage import employer_id, status_batch, withdraw_confirmed
from .policy import PollConfig
from .transport import FetchError, SafeTransport

sources, polling = schema.source_registry, schema.source_polling
runs, metrics = schema.ingestion_runs, schema.ingestion_run_metrics
items, queue = schema.source_items, schema.ingestion_candidates
jobs = schema.jobs


def approved():
    return (
        sources.c.enabled.is_(True),
        sources.c.approved_at <= func.statement_timestamp(),
        func.length(func.trim(sources.c.permission_reference)) > 0,
        sources.c.organisation_id.is_not(None),
    )


def source_query():
    return select(sources, polling).join(polling, polling.c.source_id == sources.c.id)


def due_sources(limit=50):
    with Session(engine()) as db:
        return list(
            db.scalars(
                select(sources.c.id)
                .join(polling, polling.c.source_id == sources.c.id)
                .where(*approved(), polling.c.next_poll_at <= func.statement_timestamp())
                .order_by(
                    polling.c.configuration["priority"].as_integer().desc(),
                    polling.c.next_poll_at,
                    sources.c.id,
                )
                .limit(limit)
            )
        )


def attach_job(db, draft):
    identity = dict(
        organisation_id=draft.organisation_id,
        cycle_key=draft.cycle_key,
        opportunity_key=draft.opportunity_key,
        category=draft.details.category,
    )
    job_id = db.scalar(
        pg_insert(jobs)
        .values(
            **identity,
            title=draft.title,
            official_url=draft.official_url,
            expires_at=draft.expires_at,
        )
        .on_conflict_do_nothing(index_elements=[jobs.c[key] for key in identity])
        .returning(jobs.c.id)
    )
    if job_id:
        db.execute(
            insert(schema.job_details).values(
                job_id=job_id,
                description=draft.description,
                location=draft.location,
                apply_url=draft.apply_url,
                application_closes_at=draft.deadline,
                category_fields=draft.details.model_dump(mode="json", exclude={"category"}),
            )
        )
        db.execute(insert(schema.publication).values(job_id=job_id, review_state="submitted"))
        return job_id, True
    match = [jobs.c[key] == value for key, value in identity.items()]
    return db.scalar(select(jobs.c.id).where(*match)), False


def capture(db, source_id, run_id, discoveries, config, approved_at):
    counts = dict(
        discovered=len(discoveries),
        created=0,
        updated=0,
        duplicate=0,
        pending_review=0,
        parser_failures=0,
        http_failures=0,
        rate_limited=0,
    )
    observations = (
        select(
            items.c.external_key,
            items.c.job_id,
            items.c.source_url,
            items.c.content_sha256,
            queue.c.payload,
            queue.c.provenance,
            func.row_number()
            .over(
                partition_by=items.c.external_key,
                order_by=(items.c.observed_at.desc(), items.c.id.desc()),
            )
            .label("position"),
        )
        .join(queue, queue.c.item_id == items.c.id)
        .where(items.c.source_id == source_id, items.c.observed_at >= approved_at)
        .subquery()
    )
    previous = {
        row.external_key: row
        for row in db.execute(select(observations).where(observations.c.position == 1))
    }
    seen = set()
    invalid = any(item.draft is None for item in discoveries)
    repeated_identity = False

    def observe(key, item, *, missing=False):
        draft = item.draft
        if draft and config.adapter == "himalayas":
            draft = draft.model_copy(update={"organisation_id": employer_id(db, item.provenance)})
        payload = draft.model_dump(mode="json") if draft else None
        closed = missing or item.closed
        prior = previous.get(key)
        state = (
            "withdrawal_review" if closed else "pending_review" if draft else "validation_failed"
        )
        fingerprint = [payload, closed]
        if config.adapter == "himalayas":
            fingerprint.append(
                {
                    key: value
                    for key, value in item.provenance.items()
                    if key != "provider_updated_at"
                }
            )
        signature = digest(json.dumps(fingerprint, sort_keys=True))
        if prior and signature == prior.content_sha256:
            counts["duplicate"] += 1
            counts["parser_failures"] += state == "validation_failed"
            return
        job_id = prior.job_id if missing and prior else None
        created = False
        if draft and not closed:
            job_id, created = attach_job(db, draft)
        if draft and closed:
            job_id = db.scalar(
                select(jobs.c.id).where(
                    jobs.c.organisation_id == draft.organisation_id,
                    jobs.c.category == draft.details.category,
                    jobs.c.cycle_key == draft.cycle_key,
                    jobs.c.opportunity_key == draft.opportunity_key,
                )
            )
        item_id = db.scalar(
            insert(items)
            .values(
                source_id=source_id,
                run_id=run_id,
                job_id=job_id,
                external_key=key,
                source_url=item.notice_url,
                content_sha256=signature,
            )
            .returning(items.c.id)
        )
        provenance = {**item.provenance, "closed": closed}
        db.execute(
            insert(queue).values(
                item_id=item_id, state=state, payload=payload, provenance=provenance
            )
        )
        if prior or job_id:
            before = prior.payload if prior else None
            changes = (
                {
                    field: {
                        "before": (before or {}).get(field),
                        "after": (payload or {}).get(field),
                    }
                    for field in (before or {}).keys() | (payload or {}).keys()
                    if (before or {}).get(field) != (payload or {}).get(field)
                }
                if not closed
                else {"availability": {"before": "observed", "after": "unconfirmed"}}
            )
            if job_id and (created or changes or not prior):
                db.execute(
                    insert(schema.change_events).values(
                        job_id=job_id,
                        source_item_id=item_id,
                        event_type="ingestion_detected",
                        before_values={"fields": {k: v["before"] for k, v in changes.items()}},
                        after_values={
                            "fields": {k: v["after"] for k, v in changes.items()},
                            "verification": "pending_review",
                        },
                    )
                )
        counts["created"] += created
        counts["updated"] += bool(job_id and not created)
        counts["pending_review"] += state != "validation_failed"
        counts["parser_failures"] += state == "validation_failed"

    for item in discoveries:
        cycle = item.draft.cycle_key if item.draft else "invalid"
        key = f"{item.external_id}:{digest(cycle)}"
        if key in seen:
            repeated_identity = True
            counts["duplicate"] += 1
            continue
        seen.add(key)
        observe(key, item)
    if config.complete_snapshot and not invalid and not repeated_identity:
        # Absence from a full snapshot is evidence for review only.
        for key, prior in previous.items():
            if key not in seen and prior.job_id and not prior.provenance.get("closed"):
                observe(
                    key,
                    Discovery(
                        key, prior.source_url, None, {"method": config.adapter, "reason": "missing"}
                    ),
                    missing=True,
                )
    return counts


def run_source(source_id: UUID, transport_factory=SafeTransport):
    lock_key = int.from_bytes(source_id.bytes[:8], "big", signed=True)
    with engine().connect() as connection:
        acquired = connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_key})
        connection.commit()
        if not acquired:
            return {"state": "locked"}
        try:
            with Session(bind=connection) as db:
                with db.begin():
                    source = (
                        db.execute(
                            source_query().where(
                                sources.c.id == source_id,
                                *approved(),
                                polling.c.next_poll_at <= func.statement_timestamp(),
                            )
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if not source:
                        return {"state": "not_due_or_disabled"}
                    config = PollConfig.model_validate(source["configuration"])
                    config.validate_endpoint(source["endpoint_url"])
                    db.execute(
                        update(runs)
                        .where(
                            runs.c.source_id == source_id,
                            runs.c.status == "running",
                            runs.c.run_key.startswith("poll:"),
                        )
                        .values(status="failed", finished_at=now(), error_code="interrupted")
                    )
                    run_id = db.scalar(
                        insert(runs)
                        .values(
                            source_id=source_id,
                            run_key=f"poll:{uuid4()}",
                        )
                        .returning(runs.c.id)
                    )
                    # A lost process will leave a bounded lease before another poll.
                    db.execute(
                        update(polling)
                        .where(polling.c.source_id == source_id)
                        .values(next_poll_at=now() + timedelta(seconds=150))
                    )
                failure = None
                try:
                    adapter_class = (
                        HimalayasAdapter
                        if config.adapter == "himalayas"
                        else (ADAPTERS[config.adapter])
                    )
                    adapter = adapter_class(
                        config, source["endpoint_url"], source["organisation_id"]
                    )
                    transport = transport_factory(config)
                    checks, closed = [], {}
                    if isinstance(adapter, HimalayasAdapter):
                        with db.begin():
                            checks = status_batch(db, source_id, config.himalayas_status_checks)
                        discoveries, closed = adapter.discover(
                            transport, status_guids=[row.official_url for row in checks]
                        )
                    else:
                        discoveries = adapter.discover(transport)
                    with db.begin():
                        current = (
                            db.execute(
                                source_query()
                                .where(
                                    sources.c.id == source_id,
                                    *approved(),
                                )
                                .with_for_update()
                            )
                            .mappings()
                            .one_or_none()
                        )
                        config_changed = not current or any(
                            current[key] != source[key]
                            for key in (
                                "configuration",
                                "endpoint_url",
                                "organisation_id",
                                "approved_at",
                                "permission_reference",
                            )
                        )
                        if config_changed:
                            raise FetchError("source_changed")
                        result = capture(
                            db, source_id, run_id, discoveries, config, source["approved_at"]
                        )
                        if isinstance(adapter, HimalayasAdapter):
                            result.update(adapter.counts)
                            result["status_cursor"] = str(checks[-1].id) if checks else None
                            result["status_withdrawn"] = sum(
                                withdraw_confirmed(
                                    db,
                                    source_id,
                                    row.id,
                                    row.official_url,
                                    closed[row.official_url],
                                )
                                for row in checks
                                if row.official_url in closed
                            )
                        finished = now()
                        partial = result["parser_failures"] > 0
                        db.execute(
                            update(runs)
                            .where(runs.c.id == run_id)
                            .values(
                                status="partial" if partial else "succeeded",
                                finished_at=finished,
                                error_code="invalid_record" if partial else None,
                            )
                        )
                        health = {
                            "next_poll_at": finished
                            + timedelta(seconds=config.interval_seconds + random.randint(0, 30))
                        }
                        if partial:
                            health.update(
                                last_failure_at=finished,
                                consecutive_failures=polling.c.consecutive_failures + 1,
                            )
                        else:
                            health.update(last_success_at=finished, consecutive_failures=0)
                        db.execute(
                            update(polling).where(polling.c.source_id == source_id).values(**health)
                        )
                        db.execute(insert(metrics).values(run_id=run_id, counts=result))
                    return {"state": "partial" if partial else "succeeded", **result}
                except SoftTimeLimitExceeded:
                    failure = FetchError("timeout", retry=True)
                except FetchError as exc:
                    failure = exc
                except Exception:
                    failure = FetchError("internal_error")
                with db.begin():
                    delay = min(3600, 30 * 2 ** min(source["consecutive_failures"], 7))
                    delay = max(
                        failure.retry_after,
                        delay + random.randint(0, 15),
                        0 if failure.retry else config.interval_seconds,
                    )
                    finished = now()
                    db.execute(
                        update(runs)
                        .where(runs.c.id == run_id)
                        .values(
                            status="failed",
                            finished_at=finished,
                            error_code=failure.code,
                        )
                    )
                    db.execute(
                        update(polling)
                        .where(polling.c.source_id == source_id)
                        .values(
                            last_failure_at=finished,
                            next_poll_at=finished + timedelta(seconds=delay),
                            consecutive_failures=polling.c.consecutive_failures + 1,
                        )
                    )
                    db.execute(
                        insert(metrics).values(
                            run_id=run_id,
                            counts={
                                "http_failures": int(
                                    failure.code.startswith("http_")
                                    or failure.code in {"timeout", "network_error"}
                                ),
                                "rate_limited": int(failure.code == "http_429"),
                                "parser_failures": int(
                                    failure.code in {"parse_failed", "invalid_feed_shape"}
                                ),
                            },
                        )
                    )
                failure.retry_after = delay
                raise failure
        finally:
            if connection.in_transaction():
                connection.rollback()
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": lock_key})
            connection.commit()
