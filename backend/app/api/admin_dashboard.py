from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.models import Incident, MatchingJob, MatchingJobStatusEnum, MatchSuggestion, Report, SuggestionStatusEnum
from app.schemas import DashboardStatsResponse, RecentReportResponse

router = APIRouter(prefix="/api/admin/dashboard", tags=["admin-dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    _admin: dict[str, str] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> DashboardStatsResponse:
    total_reports = db.scalar(select(func.count()).select_from(Report)) or 0
    total_incidents = db.scalar(select(func.count()).select_from(Incident)) or 0
    pending_suggestions = db.scalar(
        select(func.count()).select_from(MatchSuggestion).where(MatchSuggestion.status == SuggestionStatusEnum.PENDING)
    ) or 0
    completed_jobs = db.scalar(
        select(func.count()).select_from(MatchingJob).where(MatchingJob.status == MatchingJobStatusEnum.COMPLETED)
    ) or 0
    failed_jobs = db.scalar(
        select(func.count()).select_from(MatchingJob).where(MatchingJob.status == MatchingJobStatusEnum.FAILED)
    ) or 0

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    reports_last_7_days = db.scalar(
        select(func.count()).select_from(Report).where(Report.created_at >= seven_days_ago)
    ) or 0

    return DashboardStatsResponse(
        total_reports=total_reports,
        total_incidents=total_incidents,
        pending_suggestions=pending_suggestions,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        reports_last_7_days=reports_last_7_days,
    )


@router.get("/recent-reports", response_model=list[RecentReportResponse])
def get_recent_reports(
    _admin: dict[str, str] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[RecentReportResponse]:
    stmt = select(Report).order_by(Report.created_at.desc()).limit(5)
    reports = list(db.scalars(stmt).all())
    return [
        RecentReportResponse(
            id=r.id,
            category=r.category,
            description=r.description,
            created_at=r.created_at,
            incident_id=r.incident_id,
            image_path=r.image_path,
        )
        for r in reports
    ]
