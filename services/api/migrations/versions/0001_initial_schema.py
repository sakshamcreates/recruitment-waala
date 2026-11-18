"""initial schema"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organisations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("official_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organisations")),
        sa.UniqueConstraint("slug", name=op.f("uq_organisations_slug")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("identity_issuer", sa.Text(), nullable=False),
        sa.Column("identity_subject", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="member", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('member','moderator','admin')", name=op.f("ck_users_role")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint(
            "identity_issuer",
            "identity_subject",
            name=op.f("uq_users_identity_issuer_identity_subject"),
        ),
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cadence", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("cadence IN ('daily','weekly')", name=op.f("ck_alerts_cadence")),
        sa.CheckConstraint(
            "jsonb_typeof(filters) = 'object'", name=op.f("ck_alerts_filters_object")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_alerts_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
    )
    op.create_index(op.f("ix_alerts_user_id"), "alerts", ["user_id"], unique=False)
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("parent_job_id", sa.Uuid(), nullable=True),
        sa.Column("cycle_key", sa.String(length=200), nullable=False),
        sa.Column("opportunity_key", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("official_url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('government_job','corporate_job','internship','admit_card',"
            "'result','answer_key','syllabus','career_update')",
            name=op.f("ck_jobs_category"),
        ),
        sa.CheckConstraint(
            "status <> 'published' OR (published_at IS NOT NULL AND official_url IS NOT NULL)",
            name=op.f("ck_jobs_publication_fields"),
        ),
        sa.CheckConstraint(
            "status IN ('draft','published','expired','withdrawn')", name=op.f("ck_jobs_status")
        ),
        sa.CheckConstraint(
            "parent_job_id IS NULL OR parent_job_id <> id", name=op.f("ck_jobs_parent_not_self")
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name=op.f("fk_jobs_organisation_id_organisations"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_job_id", "organisation_id", "cycle_key"],
            ["jobs.id", "jobs.organisation_id", "jobs.cycle_key"],
            name="fk_jobs_parent_cycle",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        sa.UniqueConstraint(
            "id", "organisation_id", "cycle_key", name=op.f("uq_jobs_id_organisation_id_cycle_key")
        ),
        sa.UniqueConstraint(
            "organisation_id",
            "cycle_key",
            "category",
            "opportunity_key",
            name=op.f("uq_jobs_organisation_id_cycle_key_category_opportunity_key"),
        ),
    )
    op.create_index(
        "ix_jobs_discovery", "jobs", ["status", "category", "published_at", "id"], unique=False
    )
    op.create_index(
        "ix_jobs_expiry",
        "jobs",
        ["expires_at"],
        unique=False,
        postgresql_where=sa.text("status = 'published'"),
    )
    op.create_index(op.f("ix_jobs_parent_job_id"), "jobs", ["parent_job_id"], unique=False)
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("locale", sa.String(length=32), server_default="en-IN", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_profiles_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_profiles")),
    )
    op.create_table(
        "source_registry",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=True),
        sa.Column("adapter_kind", sa.String(length=32), nullable=False),
        sa.Column("endpoint_url", sa.Text(), nullable=False),
        sa.Column("permission_reference", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "adapter_kind IN ('approved_api','authorised_feed','official_page')",
            name=op.f("ck_source_registry_adapter_kind"),
        ),
        sa.CheckConstraint(
            "NOT enabled OR (approved_at IS NOT NULL AND permission_reference IS NOT NULL)",
            name=op.f("ck_source_registry_approval_required"),
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            name=op.f("fk_source_registry_organisation_id_organisations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_registry")),
        sa.UniqueConstraint("slug", name=op.f("uq_source_registry_slug")),
    )
    op.create_index(
        op.f("ix_source_registry_organisation_id"),
        "source_registry",
        ["organisation_id"],
        unique=False,
    )
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("run_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="running", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.CheckConstraint(
            "status IN ('running','succeeded','failed','partial')",
            name=op.f("ck_ingestion_runs_status"),
        ),
        sa.CheckConstraint("finished_at >= started_at", name=op.f("ck_ingestion_runs_time_order")),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["source_registry.id"],
            name=op.f("fk_ingestion_runs_source_id_source_registry"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_runs")),
        sa.UniqueConstraint("id", "source_id", name=op.f("uq_ingestion_runs_id_source_id")),
        sa.UniqueConstraint(
            "source_id", "run_key", name=op.f("uq_ingestion_runs_source_id_run_key")
        ),
    )
    op.create_table(
        "job_details",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("apply_url", sa.Text(), nullable=True),
        sa.Column("application_opens_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("application_closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "category_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "jsonb_typeof(category_fields) = 'object'",
            name=op.f("ck_job_details_category_fields_object"),
        ),
        sa.CheckConstraint(
            "application_closes_at >= application_opens_at",
            name=op.f("ck_job_details_application_window"),
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_job_details_job_id_jobs"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("job_id", name=op.f("pk_job_details")),
    )
    op.create_table(
        "saved_jobs",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name=op.f("fk_saved_jobs_job_id_jobs")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_saved_jobs_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "job_id", name=op.f("pk_saved_jobs")),
    )
    op.create_index(op.f("ix_saved_jobs_job_id"), "saved_jobs", ["job_id"], unique=False)
    op.create_table(
        "source_items",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("external_key", sa.String(length=300), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("snapshot_reference", sa.Text(), nullable=True),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'", name=op.f("ck_source_items_sha256")
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name=op.f("fk_source_items_job_id_jobs")),
        sa.ForeignKeyConstraint(
            ["run_id", "source_id"],
            ["ingestion_runs.id", "ingestion_runs.source_id"],
            name=op.f("fk_source_items_run_id_ingestion_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["source_registry.id"],
            name=op.f("fk_source_items_source_id_source_registry"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_items")),
        sa.UniqueConstraint(
            "run_id",
            "external_key",
            "content_sha256",
            name=op.f("uq_source_items_run_id_external_key_content_sha256"),
        ),
    )
    op.create_index(
        "ix_source_items_identity",
        "source_items",
        ["source_id", "external_key", "observed_at"],
        unique=False,
    )
    op.create_index(op.f("ix_source_items_job_id"), "source_items", ["job_id"], unique=False)
    op.create_index(op.f("ix_source_items_run_id"), "source_items", ["run_id"], unique=False)
    op.create_table(
        "change_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("source_item_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("before_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_change_events_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name=op.f("fk_change_events_job_id_jobs")),
        sa.ForeignKeyConstraint(
            ["source_item_id"],
            ["source_items.id"],
            name=op.f("fk_change_events_source_item_id_source_items"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_change_events")),
    )
    op.create_index(
        op.f("ix_change_events_actor_user_id"), "change_events", ["actor_user_id"], unique=False
    )
    op.create_index(
        op.f("ix_change_events_source_item_id"), "change_events", ["source_item_id"], unique=False
    )
    op.create_index(
        "ix_change_events_timeline", "change_events", ["job_id", "recorded_at", "id"], unique=False
    )
    op.create_table(
        "moderation_reviews",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("source_item_id", sa.Uuid(), nullable=True),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=True),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision IN ('approve','reject','request_changes','withdraw')",
            name=op.f("ck_moderation_reviews_decision"),
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_moderation_reviews_job_id_jobs")
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_user_id"],
            ["users.id"],
            name=op.f("fk_moderation_reviews_reviewer_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_item_id"],
            ["source_items.id"],
            name=op.f("fk_moderation_reviews_source_item_id_source_items"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_moderation_reviews")),
    )
    op.create_index(
        op.f("ix_moderation_reviews_job_id"), "moderation_reviews", ["job_id"], unique=False
    )
    op.create_index(
        op.f("ix_moderation_reviews_reviewer_user_id"),
        "moderation_reviews",
        ["reviewer_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_moderation_reviews_source_item_id"),
        "moderation_reviews",
        ["source_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_moderation_reviews_source_item_id"), table_name="moderation_reviews")
    op.drop_index(op.f("ix_moderation_reviews_reviewer_user_id"), table_name="moderation_reviews")
    op.drop_index(op.f("ix_moderation_reviews_job_id"), table_name="moderation_reviews")
    op.drop_table("moderation_reviews")
    op.drop_index("ix_change_events_timeline", table_name="change_events")
    op.drop_index(op.f("ix_change_events_source_item_id"), table_name="change_events")
    op.drop_index(op.f("ix_change_events_actor_user_id"), table_name="change_events")
    op.drop_table("change_events")
    op.drop_index(op.f("ix_source_items_run_id"), table_name="source_items")
    op.drop_index(op.f("ix_source_items_job_id"), table_name="source_items")
    op.drop_index("ix_source_items_identity", table_name="source_items")
    op.drop_table("source_items")
    op.drop_index(op.f("ix_saved_jobs_job_id"), table_name="saved_jobs")
    op.drop_table("saved_jobs")
    op.drop_table("job_details")
    op.drop_table("ingestion_runs")
    op.drop_index(op.f("ix_source_registry_organisation_id"), table_name="source_registry")
    op.drop_table("source_registry")
    op.drop_table("profiles")
    op.drop_index(op.f("ix_jobs_parent_job_id"), table_name="jobs")
    op.drop_index(
        "ix_jobs_expiry", table_name="jobs", postgresql_where=sa.text("status = 'published'")
    )
    op.drop_index("ix_jobs_discovery", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index(op.f("ix_alerts_user_id"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_table("users")
    op.drop_table("organisations")
