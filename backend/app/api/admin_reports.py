import logging
import math
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_admin, require_csrf
from app.config import settings
from app.database import get_db
from app.models import (
    ActorTypeEnum,
    AdminAuditLog,
    Incident,
    MatchingJob,
    MatchSuggestion,
    Report,
    StatusEnum,
)
from app.schemas import (
    AdminReportDeleteResponse,
    AdminReportDetailResponse,
    AdminReportListItem,
    CategoryEnum,
    MatchingJobResponse,
    MatchSuggestionResponse,
    PaginatedResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/reports", tags=["admin-reports"])


def _safe_delete_image(relative_path: str | None) -> bool:
    if not relative_path:
        return False
    try:
        upload_dir = Path(settings.upload_dir).resolve()
        filename = Path(relative_path).name
        if not filename:
            return False
        target = (upload_dir / filename).resolve()
        if not target.is_relative_to(upload_dir):
            logger.warning("Blocked image deletion outside upload dir: %s", relative_path)
            return False
        if not target.exists():
            logger.warning("Image file missing during delete: %s", target)
            return False
        target.unlink()
        return True
    except Exception:
        logger.warning("Failed to delete image file: %s", relative_path, exc_info=True)
        return False


def _to_list_item(report: Report) -> AdminReportListItem:
    latest_job = max(report.matching_jobs, key=lambda j: j.created_at) if report.matching_jobs else None
    return AdminReportListItem(
        id=report.id,
        description=report.description,
        category=report.category,
        latitude=report.latitude,
        longitude=report.longitude,
        image_path=report.image_path,
        sha256_hash=report.sha256_hash,
        phash=report.phash,
        phash_size=report.phash_size,
        created_at=report.created_at,
        incident_id=report.incident_id,
        incident_status=report.incident.status if report.incident else None,
        matching_job_status=latest_job.status if latest_job else None,
    )


@router.get("", response_model=PaginatedResponse[AdminReportListItem])
def list_admin_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    category: CategoryEnum | None = Query(None),
    status: StatusEnum | None = Query(None),
    _admin: dict[str, str] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PaginatedResponse[AdminReportListItem]:
    base = select(Report).outerjoin(Incident, Report.incident_id == Incident.id)
    if search:
        term = search.strip()
        if term:
            like = f"%{term}%"
            prefix = f"{term}%"
            base = base.where(or_(Report.id.ilike(prefix), Report.description.ilike(like)))
    if category:
        base = base.where(Report.category == category)
    if status:
        base = base.where(Incident.status == status)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = db.scalar(count_stmt) or 0
    total_pages = max(1, math.ceil(total / page_size)) if total else 1
    if page > total_pages and total > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page out of range.")

    stmt = (
        base.options(selectinload(Report.incident), selectinload(Report.matching_jobs))
        .order_by(Report.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    reports = list(db.scalars(stmt).all())
    return PaginatedResponse[AdminReportListItem](
        items=[_to_list_item(r) for r in reports],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{report_id}", response_model=AdminReportDetailResponse)
def get_admin_report(
    report_id: str,
    _admin: dict[str, str] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminReportDetailResponse:
    stmt = (
        select(Report)
        .options(
            selectinload(Report.incident),
            selectinload(Report.matching_jobs),
            selectinload(Report.match_suggestions).selectinload(MatchSuggestion.incident),
            selectinload(Report.match_suggestions).selectinload(MatchSuggestion.matched_report),
        )
        .where(Report.id == report_id)
    )
    report = db.scalar(stmt)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    latest_job = max(report.matching_jobs, key=lambda j: j.created_at) if report.matching_jobs else None
    suggestions = sorted(report.match_suggestions, key=lambda s: s.similarity_score, reverse=True)
    suggestion_responses = []
    for s in suggestions:
        suggestion_responses.append(
            MatchSuggestionResponse(
                id=s.id,
                report_id=s.report_id,
                incident_id=s.incident_id,
                matched_report_id=s.matched_report_id,
                similarity_score=s.similarity_score,
                status=s.status,
                created_at=s.created_at,
                incident_title=s.incident.title if s.incident else None,
                incident_category=s.incident.category if s.incident else None,
                incident_status=s.incident.status if s.incident else None,
                incident_latitude=s.incident.latitude if s.incident else None,
                incident_longitude=s.incident.longitude if s.incident else None,
                matched_report_description=s.matched_report.description if s.matched_report else None,
                sha256_match=s.sha256_match,
                phash_hamming_distance=s.phash_hamming_distance,
                phash_similarity=s.phash_similarity,
                text_similarity=s.text_similarity,
                geo_distance_meters=s.geo_distance_meters,
                category_match=s.category_match,
                candidate_classification=s.candidate_classification,
            )
        )

    job_response = None
    if latest_job:
        job_response = MatchingJobResponse(
            id=latest_job.id,
            report_id=latest_job.report_id,
            status=latest_job.status,
            error_message=latest_job.error_message,
            attempts=latest_job.attempts,
            created_at=latest_job.created_at,
            updated_at=latest_job.updated_at,
            completed_at=latest_job.completed_at,
            suggestions=suggestion_responses,
        )

    return AdminReportDetailResponse(
        id=report.id,
        description=report.description,
        category=report.category,
        latitude=report.latitude,
        longitude=report.longitude,
        image_path=report.image_path,
        sha256_hash=report.sha256_hash,
        phash=report.phash,
        phash_size=report.phash_size,
        created_at=report.created_at,
        incident_id=report.incident_id,
        incident_status=report.incident.status if report.incident else None,
        matching_job_status=latest_job.status if latest_job else None,
        incident=report.incident,
        matching_job=job_response,
        match_suggestions=suggestion_responses,
    )


@router.delete("/{report_id}", response_model=AdminReportDeleteResponse)
def delete_admin_report(
    report_id: str,
    _admin: dict[str, str] = Depends(get_current_admin),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> AdminReportDeleteResponse:
    report = db.scalar(
        select(Report)
        .options(
            selectinload(Report.incident),
            selectinload(Report.matching_jobs),
            selectinload(Report.match_suggestions),
        )
        .where(Report.id == report_id)
    )
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    incident = report.incident
    incident_id = report.incident_id
    image_path = report.image_path
    latest_job = max(report.matching_jobs, key=lambda j: j.created_at) if report.matching_jobs else None

    audit = AdminAuditLog(
        actor_type=ActorTypeEnum.ADMIN,
        admin_username=_admin["username"],
        system_actor=None,
        action="REPORT_DELETED",
        target_type="report",
        target_id=report.id,
        metadata_json={
            "incident_id": incident_id,
            "category": report.category.value,
            "description_preview": report.description[:200],
            "image_path": image_path,
            "matching_job_status": latest_job.status.value if latest_job else None,
            "suggestion_count": len(report.match_suggestions),
        },
    )

    try:
        # Delete report first; DB cascades handle matching_jobs and match_suggestions FKs.
        db.delete(report)
        db.flush()

        incident_deleted = False
        if incident_id:
            remaining = db.scalar(
                select(func.count()).select_from(Report).where(Report.incident_id == incident_id)
            ) or 0
            # Preserve incident if other reports remain or if it is merged/preserved.
            if remaining == 0 and incident is not None and incident.status != StatusEnum.MERGED:
                # Ensure no other dependent suggestions reference this incident (defensive).
                incident_suggestion_refs = db.scalar(
                    select(func.count()).select_from(MatchSuggestion).where(MatchSuggestion.incident_id == incident_id)
                ) or 0
                if incident_suggestion_refs == 0:
                    db.delete(incident)
                    incident_deleted = True

        db.add(audit)
        db.commit()
    except Exception:
        db.rollback()
        raise

    image_deleted = _safe_delete_image(image_path)
    return AdminReportDeleteResponse(
        deleted=True,
        report_id=report_id,
        incident_deleted=incident_deleted,
        image_deleted=image_deleted,
    )
