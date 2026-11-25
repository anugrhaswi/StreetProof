"""Admin match moderation API (Phase D3).

Queue of REVIEW_CANDIDATE/PENDING suggestions for human review.
Accept triggers D2 merge service; reject marks suggestion REJECTED.
"""

from __future__ import annotations

import logging
import math

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
    MatchSuggestion,
    MergeEvent,
    MergeExecution,
    Report,
    SuggestionStatusEnum,
)
from app.schemas import (
    AcceptMatchResponse,
    AdminMatchReport,
    AdminMatchSuggestionDetailResponse,
    AdminMatchSuggestionListItem,
    PaginatedResponse,
    RejectMatchRequest,
    RejectMatchResponse,
    SuggestionStatusEnum as SuggestionStatusSchema,
)
from app.services.incident_merge import (
    MergeConflictError,
    execute_auto_merge,
    utc_now,
)
from app.services.matching_engine import find_candidate_incidents_multisignal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/matches", tags=["admin-matches"])


def _to_match_report(report: Report) -> AdminMatchReport:
    return AdminMatchReport(
        id=report.id,
        description=report.description,
        category=report.category,
        latitude=report.latitude,
        longitude=report.longitude,
        image_path=report.image_path,
        created_at=report.created_at,
        incident_id=report.incident_id,
        incident_status=report.incident.status if report.incident else None,
    )


def _to_list_item(s: MatchSuggestion) -> AdminMatchSuggestionListItem:
    report = s.report
    matched = s.matched_report
    if report is None or matched is None:
        raise ValueError("Suggestion missing report relation")
    return AdminMatchSuggestionListItem(
        id=s.id,
        report_id=s.report_id,
        incident_id=s.incident_id,
        matched_report_id=s.matched_report_id,
        similarity_score=s.similarity_score,
        status=s.status,
        candidate_classification=s.candidate_classification,
        created_at=s.created_at,
        sha256_match=s.sha256_match,
        phash_hamming_distance=s.phash_hamming_distance,
        phash_similarity=s.phash_similarity,
        text_similarity=s.text_similarity,
        geo_distance_meters=s.geo_distance_meters,
        category_match=s.category_match,
        report=_to_match_report(report),
        matched_report=_to_match_report(matched),
        incident_title=s.incident.title if s.incident else None,
    )


@router.get("", response_model=PaginatedResponse[AdminMatchSuggestionListItem])
def list_admin_matches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: SuggestionStatusSchema | None = Query(None, alias="status"),
    search: str | None = Query(None, max_length=200),
    category: str | None = Query(None, max_length=50),
    classification: str | None = Query(None, max_length=50),
    _admin: dict[str, str] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PaginatedResponse[AdminMatchSuggestionListItem]:
    base = select(MatchSuggestion).join(Report, MatchSuggestion.report_id == Report.id)
    if status_filter:
        base = base.where(MatchSuggestion.status == SuggestionStatusEnum(status_filter.value))
    if category:
        base = base.where(Report.category == category)
    if classification:
        base = base.where(MatchSuggestion.candidate_classification == classification)
    if search:
        term = search.strip()
        if term:
            like = f"%{term}%"
            prefix = f"{term}%"
            base = base.where(
                or_(
                    MatchSuggestion.id.ilike(prefix),
                    MatchSuggestion.report_id.ilike(prefix),
                    MatchSuggestion.incident_id.ilike(prefix),
                    MatchSuggestion.matched_report_id.ilike(prefix),
                    Report.description.ilike(like),
                )
            )

    count_stmt = select(func.count()).select_from(base.subquery())
    total = db.scalar(count_stmt) or 0
    total_pages = max(1, math.ceil(total / page_size)) if total else 1
    if page > total_pages and total > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page out of range.")

    stmt = (
        base.options(
            selectinload(MatchSuggestion.report).selectinload(Report.incident),
            selectinload(MatchSuggestion.matched_report).selectinload(Report.incident),
            selectinload(MatchSuggestion.incident),
        )
        .order_by(MatchSuggestion.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    suggestions = list(db.scalars(stmt).all())
    items = [_to_list_item(s) for s in suggestions if s.report and s.matched_report]
    return PaginatedResponse[AdminMatchSuggestionListItem](
        items=items, page=page, page_size=page_size, total=total, total_pages=total_pages
    )


@router.get("/{suggestion_id}", response_model=AdminMatchSuggestionDetailResponse)
def get_admin_match(
    suggestion_id: str,
    _admin: dict[str, str] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminMatchSuggestionDetailResponse:
    s = db.scalar(
        select(MatchSuggestion)
        .options(
            selectinload(MatchSuggestion.report).selectinload(Report.incident),
            selectinload(MatchSuggestion.matched_report).selectinload(Report.incident),
            selectinload(MatchSuggestion.incident),
        )
        .where(MatchSuggestion.id == suggestion_id)
    )
    if not s or not s.report or not s.matched_report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match suggestion not found.")

    execution = db.scalar(
        select(MergeExecution).where(MergeExecution.match_suggestion_id == s.id)
    )
    merge_event = db.get(MergeEvent, execution.merge_event_id) if execution and execution.merge_event_id else None
    reversible = bool(
        merge_event
        and merge_event.action in ("AUTOMATIC_INCIDENT_MERGE", "MANUAL_INCIDENT_MERGE")
        and merge_event.reversed_at is None
    )

    item = _to_list_item(s)
    return AdminMatchSuggestionDetailResponse(
        **item.model_dump(),
        merge_event_id=execution.merge_event_id if execution else None,
        merge_execution_status=execution.status.value if execution else None,
        merge_execution_error=execution.last_error if execution else None,
        reversible=reversible,
    )


def _recompute_ranked_candidates(db: Session, report: Report):
    candidates = db.scalars(
        select(Report)
        .options(selectinload(Report.incident))
        .where(Report.id != report.id, Report.incident_id != report.incident_id)
    ).all()
    candidate_reports = []
    for c in candidates:
        if c.incident is None:
            continue
        emb = c.embedding
        if hasattr(emb, "tolist"):
            emb = emb.tolist()
        candidate_reports.append(
            {
                "report_id": c.id,
                "incident_id": c.incident_id,
                "report_description": c.description,
                "embedding": emb if isinstance(emb, list) else None,
                "sha256_hash": c.sha256_hash,
                "phash": c.phash,
                "category": c.category.value if hasattr(c.category, "value") else str(c.category),
                "latitude": c.latitude,
                "longitude": c.longitude,
                "incident_title": c.incident.title,
                "incident_category": c.incident.category.value if hasattr(c.incident.category, "value") else str(c.incident.category),
                "incident_status": c.incident.status.value if hasattr(c.incident.status, "value") else str(c.incident.status),
                "incident_latitude": c.incident.latitude,
                "incident_longitude": c.incident.longitude,
            }
        )
    target_emb = report.embedding
    if hasattr(target_emb, "tolist"):
        target_emb = target_emb.tolist()
    semantic_enabled = settings.semantic_matching_is_enabled() and EmbeddingService.get_instance().is_enabled()
    return find_candidate_incidents_multisignal(
        target_report_id=report.id,
        target_incident_id=report.incident_id,
        target_embedding=(target_emb if isinstance(target_emb, list) else None) if semantic_enabled else None,
        target_sha256=report.sha256_hash,
        target_phash=report.phash,
        target_category=report.category.value if hasattr(report.category, "value") else str(report.category),
        target_lat=report.latitude,
        target_lng=report.longitude,
        candidate_reports=candidate_reports,
        matching_radius_meters=settings.matching_radius_meters,
        auto_merge_radius_meters=settings.auto_merge_radius_meters,
        phash_similarity_threshold=settings.phash_similarity_threshold,
        phash_review_threshold=settings.phash_review_threshold,
        text_similarity_threshold=settings.text_similarity_threshold,
        auto_merge_text_threshold=settings.auto_merge_text_threshold,
        max_candidates=max(50, settings.max_candidates),
        semantic_matching_enabled=semantic_enabled,
    )


@router.post("/{suggestion_id}/accept", response_model=AcceptMatchResponse)
def accept_match(
    suggestion_id: str,
    _admin: dict[str, str] = Depends(get_current_admin),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> AcceptMatchResponse:
    s = db.scalar(
        select(MatchSuggestion)
        .options(selectinload(MatchSuggestion.report), selectinload(MatchSuggestion.matched_report))
        .where(MatchSuggestion.id == suggestion_id)
        .with_for_update()
    )
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match suggestion not found.")
    if s.status not in {SuggestionStatusEnum.PENDING, SuggestionStatusEnum.REVIEWED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Suggestion cannot be accepted from status {s.status.value}.")
    report = db.get(Report, s.report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    ranked_candidates = _recompute_ranked_candidates(db, report)
    try:
        merge_event = execute_auto_merge(
            db,
            suggestion=s,
            ranked_candidates=ranked_candidates,
            settings=settings,
            actor_type=ActorTypeEnum.ADMIN,
            system_actor="admin",
            admin_username=_admin["username"],
        )
        if merge_event is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Merge not eligible. Check evidence, policy, or incident state.",
            )
        db.commit()
        db.refresh(s)
    except MergeConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to accept match suggestion %s", suggestion_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to accept match.")

    return AcceptMatchResponse(suggestion_id=s.id, status=s.status, merge_event_id=merge_event.id)


@router.post("/{suggestion_id}/reject", response_model=RejectMatchResponse)
def reject_match(
    suggestion_id: str,
    payload: RejectMatchRequest | None = None,
    _admin: dict[str, str] = Depends(get_current_admin),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> RejectMatchResponse:
    s = db.scalar(select(MatchSuggestion).where(MatchSuggestion.id == suggestion_id).with_for_update())
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match suggestion not found.")
    if s.status not in {SuggestionStatusEnum.PENDING, SuggestionStatusEnum.REVIEWED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Suggestion cannot be rejected from status {s.status.value}.")

    s.status = SuggestionStatusEnum.REJECTED
    s.reviewed_at = utc_now()
    db.add(s)
    audit = AdminAuditLog(
        actor_type=ActorTypeEnum.ADMIN,
        admin_username=_admin["username"],
        system_actor=None,
        action="MATCH_REJECTED",
        target_type="match_suggestion",
        target_id=s.id,
        metadata_json={
            "reason": (payload.reason if payload else None),
            "report_id": s.report_id,
            "incident_id": s.incident_id,
            "matched_report_id": s.matched_report_id,
            "candidate_classification": s.candidate_classification,
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(s)
    return RejectMatchResponse(suggestion_id=s.id, status=s.status)
