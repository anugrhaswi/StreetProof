"""phase3 matching jobs suggestions embedding

Revision ID: a1b2c3d4e5f6
Revises: 941a55399f28
Create Date: 2026-11-24 23:09:26.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "941a55399f28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


matching_job_status_enum = sa.Enum(
    "PENDING", "PROCESSING", "COMPLETED", "FAILED", name="matching_job_status_enum"
)
suggestion_status_enum = sa.Enum(
    "PENDING", "REVIEWED", "DISMISSED", name="suggestion_status_enum"
)


def upgrade() -> None:
    op.add_column("reports", sa.Column("embedding", sa.JSON(), nullable=True))

    op.create_table(
        "matching_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("report_id", sa.String(length=36), nullable=False),
        sa.Column("status", matching_job_status_enum, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_matching_jobs_report_id"), "matching_jobs", ["report_id"], unique=False)
    op.create_index(op.f("ix_matching_jobs_status"), "matching_jobs", ["status"], unique=False)

    op.create_table(
        "match_suggestions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("report_id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=36), nullable=False),
        sa.Column("matched_report_id", sa.String(length=36), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("status", suggestion_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matched_report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "incident_id", name="uq_match_suggestion_report_incident"),
    )
    op.create_index(op.f("ix_match_suggestions_incident_id"), "match_suggestions", ["incident_id"], unique=False)
    op.create_index(op.f("ix_match_suggestions_report_id"), "match_suggestions", ["report_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_match_suggestions_report_id"), table_name="match_suggestions")
    op.drop_index(op.f("ix_match_suggestions_incident_id"), table_name="match_suggestions")
    op.drop_table("match_suggestions")

    op.drop_index(op.f("ix_matching_jobs_status"), table_name="matching_jobs")
    op.drop_index(op.f("ix_matching_jobs_report_id"), table_name="matching_jobs")
    op.drop_table("matching_jobs")

    op.drop_column("reports", "embedding")

    suggestion_status_enum.drop(op.get_bind(), checkfirst=True)
    matching_job_status_enum.drop(op.get_bind(), checkfirst=True)