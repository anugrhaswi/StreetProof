from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class CategoryEnum(str, Enum):
    POTHOLE = "pothole"
    STREETLIGHT = "streetlight"
    GARBAGE = "garbage"
    GRAFFITI = "graffiti"
    SIDEWALK = "sidewalk"
    SIGNAGE = "signage"
    DRAINAGE = "drainage"
    OTHER = "other"


class StatusEnum(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class IncidentBase(BaseModel):
    title: str
    description: str
    category: CategoryEnum
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    status: StatusEnum


class IncidentResponse(IncidentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    merged_into_incident_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ReportBase(BaseModel):
    description: str = Field(min_length=10, max_length=5000)
    category: CategoryEnum
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ReportResponse(ReportBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    image_path: str
    sha256_hash: str | None = None
    phash: str
    phash_size: int | None = None
    created_at: datetime
    incident_id: str
    incident: IncidentResponse | None = None


class IncidentDetailResponse(IncidentResponse):
    reports: list[ReportResponse] = []


class AdminIncidentListItem(IncidentResponse):
    report_count: int = 0


class AdminIncidentStatusUpdateRequest(BaseModel):
    status: StatusEnum


class IncidentMapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    category: CategoryEnum
    latitude: float
    longitude: float
    status: StatusEnum
    report_count: int
    created_at: datetime


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    total_pages: int


class MatchingJobStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SuggestionStatusEnum(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    REJECTED = "rejected"
    AUTO_MERGED = "auto_merged"
    SUPERSEDED = "superseded"


class MergeExecutionStatusEnum(str, Enum):
    PENDING = "pending"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ActorTypeEnum(str, Enum):
    ADMIN = "admin"
    SYSTEM = "system"


class MatchSuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    report_id: str
    incident_id: str
    matched_report_id: str
    similarity_score: float
    status: SuggestionStatusEnum
    created_at: datetime
    incident_title: str | None = None
    incident_category: CategoryEnum | None = None
    incident_status: StatusEnum | None = None
    incident_latitude: float | None = None
    incident_longitude: float | None = None
    matched_report_description: str | None = None
    # Phase D1 multisignal evidence
    sha256_match: bool | None = None
    phash_hamming_distance: int | None = None
    phash_similarity: float | None = None
    text_similarity: float | None = None
    geo_distance_meters: float | None = None
    category_match: bool | None = None
    candidate_classification: str | None = None


class MatchingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    report_id: str
    status: MatchingJobStatusEnum
    error_message: str | None = None
    attempts: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    suggestions: list[MatchSuggestionResponse] = []


class PublicMatchingStatusResponse(BaseModel):
    status: MatchingJobStatusEnum
    suggestion_count: int
    error_message: str | None = None


class AIHealthResponse(BaseModel):
    status: str
    model_name: str
    error: str | None = None


class DashboardStatsResponse(BaseModel):
    total_reports: int
    total_incidents: int
    open_incidents: int
    closed_incidents: int
    merged_incidents: int
    pending_suggestions: int
    pending_jobs: int
    completed_jobs: int
    failed_jobs: int
    reports_last_7_days: int


class RecentReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: CategoryEnum
    description: str
    created_at: datetime
    incident_id: str | None = None
    image_path: str | None = None


class AdminReportListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    description: str
    category: CategoryEnum
    latitude: float
    longitude: float
    image_path: str
    sha256_hash: str | None = None
    phash: str
    phash_size: int | None = None
    created_at: datetime
    incident_id: str
    incident_status: StatusEnum | None = None
    matching_job_status: MatchingJobStatusEnum | None = None


class AdminReportDetailResponse(AdminReportListItem):
    incident: IncidentResponse | None = None
    matching_job: MatchingJobResponse | None = None
    match_suggestions: list[MatchSuggestionResponse] = []


class AdminReportDeleteResponse(BaseModel):
    deleted: bool
    report_id: str
    incident_deleted: bool
    image_deleted: bool


class MergeEventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_incident_id: str | None
    target_incident_id: str
    report_id: str
    matched_report_id: str | None
    action: str
    actor: str
    candidate_classification: str
    heuristic_score: float | None = None
    created_at: datetime
    reversed_at: datetime | None = None


class MergeEventDetailResponse(MergeEventListItem):
    transferred_report_ids: list[str]
    target_incident_report_ids_before: list[str]
    source_incident_status_before: str
    target_incident_status_before: str
    sha256_match: bool | None = None
    phash_hamming_distance: int | None = None
    phash_similarity: float | None = None
    text_similarity: float | None = None
    geo_distance_meters: float | None = None
    category_match: bool | None = None
    policy_snapshot: dict
    reversal_merge_event_id: str | None = None
    merge_execution_status: str | None = None
    merge_execution_error: str | None = None


class AdminMatchReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    description: str
    category: CategoryEnum
    latitude: float
    longitude: float
    image_path: str
    created_at: datetime
    incident_id: str
    incident_status: StatusEnum | None = None


class AdminMatchSuggestionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    report_id: str
    incident_id: str
    matched_report_id: str
    similarity_score: float
    status: SuggestionStatusEnum
    candidate_classification: str | None = None
    created_at: datetime
    sha256_match: bool | None = None
    phash_hamming_distance: int | None = None
    phash_similarity: float | None = None
    text_similarity: float | None = None
    geo_distance_meters: float | None = None
    category_match: bool | None = None
    report: AdminMatchReport
    matched_report: AdminMatchReport
    incident_title: str | None = None


class AdminMatchSuggestionDetailResponse(AdminMatchSuggestionListItem):
    merge_event_id: str | None = None
    merge_execution_status: str | None = None
    merge_execution_error: str | None = None
    reversible: bool = False


class AcceptMatchResponse(BaseModel):
    suggestion_id: str
    status: SuggestionStatusEnum
    merge_event_id: str


class RejectMatchRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class RejectMatchResponse(BaseModel):
    suggestion_id: str
    status: SuggestionStatusEnum
