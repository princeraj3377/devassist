"""Create the DevAssist review and audit schema.

Revision ID: 0001
Revises: None
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def common_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "repositories",
        *common_columns(),
        sa.Column("github_repo_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column("installation_id", sa.BigInteger(), nullable=True),
        sa.Column("token_ref", sa.String(256), nullable=True),
        sa.Column("webhook_secret_ref", sa.String(256), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.UniqueConstraint("github_repo_id"),
    )
    op.create_table(
        "pull_requests",
        *common_columns(),
        sa.Column("repository_id", sa.Uuid(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("author", sa.String(256), nullable=False),
        sa.Column("head_sha", sa.String(64), nullable=False),
        sa.Column("base_branch", sa.String(256), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.UniqueConstraint("repository_id", "number"),
    )
    op.create_table(
        "review_runs",
        *common_columns(),
        sa.Column("pull_request_id", sa.Uuid(), sa.ForeignKey("pull_requests.id"), nullable=False),
        sa.Column("head_sha", sa.String(64), nullable=False),
        sa.Column(
            "status",
            sa.Enum("queued", "running", "completed", "failed", name="review_status"),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("trigger_delivery_id", sa.String(256), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.String(256), nullable=True),
        sa.Column("token_usage", postgresql.JSONB(), nullable=True),
        sa.Column(
            "verdict",
            sa.Enum("approve", "comment", "request_changes", name="review_verdict"),
            nullable=True,
        ),
        sa.UniqueConstraint("trigger_delivery_id"),
    )
    op.create_table(
        "findings",
        *common_columns(),
        sa.Column("review_run_id", sa.Uuid(), sa.ForeignKey("review_runs.id"), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("line", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "bug", "security", "code_smell", "documentation", "testing", name="finding_category"
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("critical", "high", "medium", "low", "info", name="finding_severity"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.Enum("static", "llm", name="finding_source"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("posted_to_github", sa.Boolean(), server_default="false", nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        sa.CheckConstraint("line IS NULL OR line > 0", name="positive_line"),
    )
    op.create_table(
        "audit_events",
        *common_columns(),
        sa.Column("review_run_id", sa.Uuid(), sa.ForeignKey("review_runs.id"), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    indexes = {
        "repositories": ["full_name", "is_active"],
        "pull_requests": ["repository_id", "state"],
        "review_runs": ["pull_request_id", "head_sha", "status", "started_at"],
        "findings": ["review_run_id", "category", "severity"],
        "audit_events": ["review_run_id", "event_type", "timestamp"],
    }
    for table, columns in indexes.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table in ("audit_events", "findings", "review_runs", "pull_requests", "repositories"):
        op.drop_table(table)
    for name in (
        "finding_source",
        "finding_severity",
        "finding_category",
        "review_verdict",
        "review_status",
    ):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=False)
