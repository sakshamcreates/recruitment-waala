from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import DeclarativeBase, Mapped

from . import schema


class Base(DeclarativeBase):
    metadata = schema.metadata


class Organisation(Base):
    __table__ = schema.organisations
    id: Mapped[UUID]
    slug: Mapped[str]
    name: Mapped[str]


class Job(Base):
    __table__ = schema.jobs
    id: Mapped[UUID]
    organisation_id: Mapped[UUID]
    category: Mapped[str]
    title: Mapped[str]
    status: Mapped[str]
    cycle_key: Mapped[str]
    opportunity_key: Mapped[str]
    official_url: Mapped[str | None]
    published_at: Mapped[datetime | None]
    expires_at: Mapped[datetime | None]


class Details(Base):
    __table__ = schema.job_details
    job_id: Mapped[UUID]
    description: Mapped[str | None]
    location: Mapped[str | None]
    apply_url: Mapped[str | None]
    application_closes_at: Mapped[datetime | None]
    category_fields: Mapped[dict]


class Publication(Base):
    __table__ = schema.publication
    job_id: Mapped[UUID]
    review_state: Mapped[str]
    version: Mapped[int]
    source_item_id: Mapped[UUID | None]
    verified_at: Mapped[datetime | None]
    is_demo: Mapped[bool]


class Source(Base):
    __table__ = schema.source_registry
    id: Mapped[UUID]
    slug: Mapped[str]
    organisation_id: Mapped[UUID | None]
    endpoint_url: Mapped[str]
    enabled: Mapped[bool]
    approved_at: Mapped[datetime | None]
    permission_reference: Mapped[str | None]


class Observation(Base):
    __table__ = schema.source_items
    id: Mapped[UUID]
    source_id: Mapped[UUID]
    external_key: Mapped[str]
    job_id: Mapped[UUID | None]
    source_url: Mapped[str]
    observed_at: Mapped[datetime]


class Change(Base):
    __table__ = schema.change_events
    id: Mapped[UUID]
    job_id: Mapped[UUID]
    event_type: Mapped[str]
    recorded_at: Mapped[datetime]
