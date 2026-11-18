"""Track explicit editorial evidence and review state."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    op.create_table(
        "publication",
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id"), primary_key=True),
        sa.Column("review_state", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_item_id", sa.Uuid(), sa.ForeignKey("source_items.id")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint(
            "review_state IN ('draft','submitted','approved','rejected')",
            name=op.f("ck_publication_review_state"),
        ),
        sa.CheckConstraint(
            "verified_at IS NULL OR (source_item_id IS NOT NULL AND NOT is_demo)",
            name=op.f("ck_publication_verification_evidence"),
        ),
    )


def downgrade():
    op.drop_table("publication")
