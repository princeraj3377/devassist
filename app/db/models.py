import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ReviewStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Category(enum.StrEnum):
    bug = "bug"
    security = "security"
    code_smell = "code_smell"
    documentation = "documentation"
    testing = "testing"


class Severity(enum.StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class FindingSource(enum.StrEnum):
    static = "static"
    llm = "llm"


class Verdict(enum.StrEnum):
    approve = "approve"
    comment = "comment"
    request_changes = "request_changes"


class Repository(TimestampMixin, Base):
    __tablename__ = "repositories"

    github_repo_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    full_name: Mapped[str] = mapped_column(String(256), index=True)
    installation_id: Mapped[int | None] = mapped_column(BigInteger)
    token_ref: Mapped[str | None] = mapped_column(String(256))
    webhook_secret_ref: Mapped[str] = mapped_column(String(256))
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", index=True)


class PullRequest(TimestampMixin, Base):
    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repository_id", "number"),)

    repository_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repositories.id"), index=True)
    number: Mapped[int]
    title: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(String(256))
    head_sha: Mapped[str] = mapped_column(String(64))
    base_branch: Mapped[str] = mapped_column(String(256))
    state: Mapped[str] = mapped_column(String(32), index=True)


class ReviewRun(TimestampMixin, Base):
    __tablename__ = "review_runs"

    pull_request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pull_requests.id"), index=True)
    head_sha: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        default=ReviewStatus.queued,
        server_default="queued",
        index=True,
    )
    trigger_delivery_id: Mapped[str] = mapped_column(String(256), unique=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    llm_model: Mapped[str | None] = mapped_column(String(256))
    token_usage: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    verdict: Mapped[Verdict | None] = mapped_column(Enum(Verdict, name="review_verdict"))


class Finding(TimestampMixin, Base):
    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint("line IS NULL OR line > 0", name="positive_line"),
    )

    review_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("review_runs.id"), index=True)
    file_path: Mapped[str] = mapped_column(Text)
    line: Mapped[int | None]
    category: Mapped[Category] = mapped_column(Enum(Category, name="finding_category"), index=True)
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="finding_severity"), index=True)
    confidence: Mapped[float]
    source: Mapped[FindingSource] = mapped_column(Enum(FindingSource, name="finding_source"))
    title: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text)
    posted_to_github: Mapped[bool] = mapped_column(default=False, server_default="false")


class AuditEvent(TimestampMixin, Base):
    __tablename__ = "audit_events"

    review_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("review_runs.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
