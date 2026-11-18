from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


def id_column() -> Column:
    return Column("id", Uuid, primary_key=True, server_default=func.gen_random_uuid())


def timestamp(name: str) -> Column:
    return Column(name, DateTime(timezone=True), nullable=False, server_default=func.now())


organisations = Table(
    "organisations",
    metadata,
    id_column(),
    Column("slug", String(160), nullable=False, unique=True),
    Column("name", Text, nullable=False),
    Column("official_url", Text),
    timestamp("created_at"),
)

jobs = Table(
    "jobs",
    metadata,
    id_column(),
    Column("organisation_id", Uuid, ForeignKey("organisations.id"), nullable=False),
    Column("parent_job_id", Uuid, index=True),
    Column("cycle_key", String(200), nullable=False),
    Column("opportunity_key", String(200), nullable=False),
    Column("category", String(32), nullable=False),
    Column("title", Text, nullable=False),
    Column("status", String(20), nullable=False, server_default="draft"),
    Column("official_url", Text),
    Column("published_at", DateTime(timezone=True)),
    Column("expires_at", DateTime(timezone=True)),
    timestamp("created_at"),
    timestamp("updated_at"),
    UniqueConstraint("organisation_id", "cycle_key", "category", "opportunity_key"),
    UniqueConstraint("id", "organisation_id", "cycle_key"),
    ForeignKeyConstraint(
        ["parent_job_id", "organisation_id", "cycle_key"],
        ["jobs.id", "jobs.organisation_id", "jobs.cycle_key"],
        name="fk_jobs_parent_cycle",
    ),
    CheckConstraint("parent_job_id IS NULL OR parent_job_id <> id", name="parent_not_self"),
    CheckConstraint(
        "category IN ('government_job','corporate_job','internship','admit_card',"
        "'result','answer_key','syllabus','career_update')",
        name="category",
    ),
    CheckConstraint("status IN ('draft','published','expired','withdrawn')", name="status"),
    CheckConstraint(
        "status <> 'published' OR (published_at IS NOT NULL AND official_url IS NOT NULL)",
        name="publication_fields",
    ),
    Index("ix_jobs_discovery", "status", "category", "published_at", "id"),
    Index("ix_jobs_expiry", "expires_at", postgresql_where=text("status = 'published'")),
)

job_details = Table(
    "job_details",
    metadata,
    Column("job_id", Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("description", Text),
    Column("location", Text),
    Column("apply_url", Text),
    Column("application_opens_at", DateTime(timezone=True)),
    Column("application_closes_at", DateTime(timezone=True)),
    Column("category_fields", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    CheckConstraint("jsonb_typeof(category_fields) = 'object'", name="category_fields_object"),
    CheckConstraint("application_closes_at >= application_opens_at", name="application_window"),
)

source_registry = Table(
    "source_registry",
    metadata,
    id_column(),
    Column("slug", String(160), nullable=False, unique=True),
    Column("organisation_id", Uuid, ForeignKey("organisations.id"), index=True),
    Column("adapter_kind", String(32), nullable=False),
    Column("endpoint_url", Text, nullable=False),
    Column("permission_reference", Text),
    Column("approved_at", DateTime(timezone=True)),
    Column("enabled", Boolean, nullable=False, server_default=false()),
    timestamp("created_at"),
    CheckConstraint(
        "adapter_kind IN ('approved_api','authorised_feed','official_page')", name="adapter_kind"
    ),
    CheckConstraint(
        "NOT enabled OR (approved_at IS NOT NULL AND permission_reference IS NOT NULL)",
        name="approval_required",
    ),
)

ingestion_runs = Table(
    "ingestion_runs",
    metadata,
    id_column(),
    Column("source_id", Uuid, ForeignKey("source_registry.id"), nullable=False),
    Column("run_key", String(200), nullable=False),
    Column("status", String(20), nullable=False, server_default="running"),
    timestamp("started_at"),
    Column("finished_at", DateTime(timezone=True)),
    Column("error_code", String(100)),
    UniqueConstraint("source_id", "run_key"),
    UniqueConstraint("id", "source_id"),
    CheckConstraint("status IN ('running','succeeded','failed','partial')", name="status"),
    CheckConstraint("finished_at >= started_at", name="time_order"),
)

source_items = Table(
    "source_items",
    metadata,
    id_column(),
    Column("source_id", Uuid, ForeignKey("source_registry.id"), nullable=False),
    Column("run_id", Uuid, nullable=False, index=True),
    Column("job_id", Uuid, ForeignKey("jobs.id"), index=True),
    Column("external_key", String(300), nullable=False),
    Column("content_sha256", String(64), nullable=False),
    Column("source_url", Text, nullable=False),
    Column("snapshot_reference", Text),
    timestamp("observed_at"),
    ForeignKeyConstraint(
        ["run_id", "source_id"], ["ingestion_runs.id", "ingestion_runs.source_id"]
    ),
    UniqueConstraint("run_id", "external_key", "content_sha256"),
    Index("ix_source_items_identity", "source_id", "external_key", "observed_at"),
    CheckConstraint("content_sha256 ~ '^[0-9a-f]{64}$'", name="sha256"),
)

publication = Table(
    "publication",
    metadata,
    Column("job_id", Uuid, ForeignKey("jobs.id"), primary_key=True),
    Column("review_state", String(16), nullable=False, server_default="draft"),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("source_item_id", Uuid, ForeignKey("source_items.id")),
    Column("verified_at", DateTime(timezone=True)),
    Column("is_demo", Boolean, nullable=False, server_default=false()),
    CheckConstraint(
        "review_state IN ('draft','submitted','approved','rejected')", name="review_state"
    ),
    CheckConstraint(
        "verified_at IS NULL OR (source_item_id IS NOT NULL AND NOT is_demo)",
        name="verification_evidence",
    ),
)

users = Table(
    "users",
    metadata,
    id_column(),
    Column("identity_issuer", Text, nullable=False),
    Column("identity_subject", Text, nullable=False),
    Column("role", String(20), nullable=False, server_default="member"),
    timestamp("created_at"),
    UniqueConstraint("identity_issuer", "identity_subject"),
    CheckConstraint("role IN ('member','moderator','admin')", name="role"),
)

profiles = Table(
    "profiles",
    metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("display_name", String(120)),
    Column("locale", String(32), nullable=False, server_default="en-IN"),
    timestamp("updated_at"),
)

saved_jobs = Table(
    "saved_jobs",
    metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("job_id", Uuid, ForeignKey("jobs.id"), primary_key=True, index=True),
    timestamp("created_at"),
)

alerts = Table(
    "alerts",
    metadata,
    id_column(),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("filters", JSONB, nullable=False),
    Column("cadence", String(16), nullable=False),
    Column("enabled", Boolean, nullable=False, server_default=false()),
    timestamp("created_at"),
    CheckConstraint("jsonb_typeof(filters) = 'object'", name="filters_object"),
    CheckConstraint("cadence IN ('daily','weekly')", name="cadence"),
)

change_events = Table(
    "change_events",
    metadata,
    id_column(),
    Column("job_id", Uuid, ForeignKey("jobs.id"), nullable=False),
    Column("source_item_id", Uuid, ForeignKey("source_items.id"), index=True),
    Column("actor_user_id", Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True),
    Column("event_type", String(48), nullable=False),
    Column("before_values", JSONB),
    Column("after_values", JSONB),
    timestamp("recorded_at"),
    Index("ix_change_events_timeline", "job_id", "recorded_at", "id"),
)

moderation_reviews = Table(
    "moderation_reviews",
    metadata,
    id_column(),
    Column("job_id", Uuid, ForeignKey("jobs.id"), nullable=False, index=True),
    Column("source_item_id", Uuid, ForeignKey("source_items.id"), index=True),
    Column("reviewer_user_id", Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True),
    Column("decision", String(24), nullable=False),
    Column("reason", Text, nullable=False),
    timestamp("reviewed_at"),
    CheckConstraint(
        "decision IN ('approve','reject','request_changes','withdraw')", name="decision"
    ),
)


source_polling = Table(
    "source_polling",
    metadata,
    Column("source_id", Uuid, ForeignKey("source_registry.id"), primary_key=True),
    Column("configuration", JSONB, nullable=False),
    Column("next_poll_at", DateTime(timezone=True), nullable=False, index=True),
    Column("last_success_at", DateTime(timezone=True)),
    Column("last_failure_at", DateTime(timezone=True)),
    Column("consecutive_failures", Integer, nullable=False, server_default="0"),
)

ingestion_candidates = Table(
    "ingestion_candidates",
    metadata,
    Column("item_id", Uuid, ForeignKey("source_items.id"), primary_key=True),
    Column("state", String(24), nullable=False, index=True),
    Column("payload", JSONB),
    Column("provenance", JSONB, nullable=False),
    CheckConstraint(
        "state IN ('pending_review','validation_failed','withdrawal_review','accepted','rejected')",
        name="state",
    ),
)

ingestion_run_metrics = Table(
    "ingestion_run_metrics",
    metadata,
    Column("run_id", Uuid, ForeignKey("ingestion_runs.id"), primary_key=True),
    Column("counts", JSONB, nullable=False),
)
