import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CategoryEnum(str, enum.Enum):
    POTHOLE = "pothole"
    STREETLIGHT = "streetlight"
    GARBAGE = "garbage"
    GRAFFITI = "graffiti"
    SIDEWALK = "sidewalk"
    SIGNAGE = "signage"
    DRAINAGE = "drainage"
    OTHER = "other"


class StatusEnum(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class MatchingJobStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SuggestionStatusEnum(str, enum.Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    REJECTED = "rejected"
    AUTO_MERGED = "auto_merged"
    SUPERSEDED = "superseded"


class MergeExecutionStatusEnum(str, enum.Enum):
    PENDING = "pending"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ActorTypeEnum(str, enum.Enum):
    ADMIN = "admin"
    SYSTEM = "system"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[CategoryEnum] = mapped_column(Enum(CategoryEnum, name="category_enum"), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[StatusEnum] = mapped_column(
        Enum(StatusEnum, name="status_enum"), nullable=False, default=StatusEnum.OPEN
    )
    merged_into_incident_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="incident", cascade="all, delete-orphan"
    )
    merged_into: Mapped["Incident | None"] = relationship(
        "Incident", remote_side="Incident.id", foreign_keys=[merged_into_incident_id]
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[CategoryEnum] = mapped_column(Enum(CategoryEnum, name="category_enum"), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    phash: Mapped[str] = mapped_column(String(64), nullable=False)
    phash_size: Mapped[int | None] = mapped_column(Integer, nullable=True, default=8)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    incident: Mapped["Incident"] = relationship("Incident", back_populates="reports")
    matching_jobs: Mapped[list["MatchingJob"]] = relationship(
        "MatchingJob", back_populates="report", cascade="all, delete-orphan"
    )
    match_suggestions: Mapped[list["MatchSuggestion"]] = relationship(
        "MatchSuggestion",
        foreign_keys="MatchSuggestion.report_id",
        back_populates="report",
        cascade="all, delete-orphan",
    )


class MatchingJob(Base):
    __tablename__ = "matching_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[MatchingJobStatusEnum] = mapped_column(
        Enum(MatchingJobStatusEnum, name="matching_job_status_enum"),
        nullable=False,
        default=MatchingJobStatusEnum.PENDING,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    report: Mapped["Report"] = relationship("Report", foreign_keys=[report_id], back_populates="matching_jobs")


class MatchSuggestion(Base):
    __tablename__ = "match_suggestions"
    __table_args__ = (
        UniqueConstraint("report_id", "incident_id", name="uq_match_suggestion_report_incident"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matched_report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[SuggestionStatusEnum] = mapped_column(
        Enum(SuggestionStatusEnum, name="suggestion_status_enum"),
        nullable=False,
        default=SuggestionStatusEnum.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Phase D1: multisignal evidence (nullable for backward compatibility)
    sha256_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    phash_hamming_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phash_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    category_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    candidate_classification: Mapped[str | None] = mapped_column(String(32), nullable=True)

    report: Mapped["Report"] = relationship("Report", foreign_keys=[report_id], back_populates="match_suggestions")
    incident: Mapped["Incident"] = relationship("Incident")
    matched_report: Mapped["Report"] = relationship("Report", foreign_keys=[matched_report_id])


class MergeEvent(Base):
    __tablename__ = "merge_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_incident_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matched_report_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # AUTOMATIC_INCIDENT_MERGE | MERGE_REVERSAL
    actor: Mapped[str] = mapped_column(String(150), nullable=False)  # "system" or admin username

    # Pre-merge state snapshot for conservative reversal validation
    transferred_report_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    target_incident_report_ids_before: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_incident_status_before: Mapped[str] = mapped_column(String(16), nullable=False)
    target_incident_status_before: Mapped[str] = mapped_column(String(16), nullable=False)

    # Evidence snapshot
    sha256_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    phash_hamming_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phash_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    category_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    candidate_classification: Mapped[str] = mapped_column(String(32), nullable=False)
    heuristic_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Immutable policy snapshot (no secrets)
    policy_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_merge_event_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("merge_events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    source_incident: Mapped["Incident | None"] = relationship("Incident", foreign_keys=[source_incident_id])
    target_incident: Mapped["Incident"] = relationship("Incident", foreign_keys=[target_incident_id])
    report: Mapped["Report"] = relationship("Report", foreign_keys=[report_id])
    matched_report: Mapped["Report | None"] = relationship("Report", foreign_keys=[matched_report_id])
    reversal_event: Mapped["MergeEvent | None"] = relationship(
        "MergeEvent", remote_side="MergeEvent.id", foreign_keys=[reversal_merge_event_id]
    )


class MergeExecution(Base):
    __tablename__ = "merge_executions"
    __table_args__ = (
        UniqueConstraint("match_suggestion_id", name="uq_merge_execution_suggestion"),
        UniqueConstraint("idempotency_key", name="uq_merge_execution_idempotency_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    match_suggestion_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("match_suggestions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    merge_event_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("merge_events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[MergeExecutionStatusEnum] = mapped_column(
        Enum(MergeExecutionStatusEnum, name="merge_execution_status_enum"),
        nullable=False,
        default=MergeExecutionStatusEnum.PENDING,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    match_suggestion: Mapped["MatchSuggestion"] = relationship("MatchSuggestion")
    merge_event: Mapped["MergeEvent | None"] = relationship("MergeEvent")


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    __table_args__ = (
        CheckConstraint(
            "(actor_type = 'ADMIN' AND admin_username IS NOT NULL AND system_actor IS NULL) OR "
            "(actor_type = 'SYSTEM' AND admin_username IS NULL AND system_actor IS NOT NULL)",
            name="ck_admin_audit_logs_actor_consistency",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_type: Mapped[ActorTypeEnum] = mapped_column(
        Enum(ActorTypeEnum, name="actor_type_enum"), nullable=False, default=ActorTypeEnum.ADMIN
    )
    admin_username: Mapped[str | None] = mapped_column(String(150), nullable=True)
    system_actor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    merge_event_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("merge_events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    merge_event: Mapped["MergeEvent | None"] = relationship("MergeEvent")
