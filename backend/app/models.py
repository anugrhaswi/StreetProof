import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="incident", cascade="all, delete-orphan"
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


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    admin_username: Mapped[str] = mapped_column(String(150), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
