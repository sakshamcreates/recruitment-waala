"""Opaque continuation positions for public catalogue queries."""

import base64
import binascii
import hashlib
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from pydantic import AwareDatetime, BaseModel, ValidationError
from sqlalchemy import and_, or_

from .contracts import Query
from .models import Details, Job


class Position(BaseModel):
    fingerprint: str
    id: UUID
    published_at: AwareDatetime
    title: str
    deadline: AwareDatetime | None
    page: int


def fingerprint(query: Query) -> str:
    payload = query.model_dump_json(exclude={"page", "cursor"})
    return hashlib.sha256(payload.encode()).hexdigest()


def decode(query: Query) -> Position | None:
    if not query.cursor:
        return None
    try:
        payload = base64.b64decode(query.cursor, altchars=b"-_", validate=True)
        position = Position.model_validate_json(payload)
        if position.fingerprint != fingerprint(query) or not 2 <= position.page <= 10000:
            raise ValueError
        if query.page != 1:
            raise ValueError
        return position
    except (ValueError, ValidationError, binascii.Error):
        raise HTTPException(422, "Invalid continuation for this catalogue query.") from None


def after(position: Position, sort: str):
    older = or_(
        Job.published_at < position.published_at,
        and_(Job.published_at == position.published_at, Job.id > position.id),
    )
    if sort == "title":
        from sqlalchemy import func

        title = func.lower(Job.title)
        return or_(title > position.title, and_(title == position.title, Job.id > position.id))
    if sort == "deadline":
        deadline = Details.application_closes_at
        if position.deadline is None:
            return and_(deadline.is_(None), older)
        return or_(
            deadline > position.deadline,
            deadline.is_(None),
            and_(deadline == position.deadline, older),
        )
    return older


def encode(
    query: Query,
    page: int,
    job_id: UUID,
    published_at: datetime,
    normalized_title: str,
    deadline: datetime | None,
) -> str:
    position = Position(
        fingerprint=fingerprint(query),
        id=job_id,
        published_at=published_at,
        title=normalized_title,
        deadline=deadline,
        page=page,
    )
    return base64.urlsafe_b64encode(position.model_dump_json().encode()).decode()
