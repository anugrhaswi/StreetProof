from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_admin, require_csrf
from app.database import get_db
from app.models import MergeEvent, MergeExecution, MergeExecutionStatusEnum
from app.schemas import MergeEventDetailResponse, MergeEventListItem, PaginatedResponse
from app.services.incident_merge import MergeReversalConflictError, reverse_merge

router = APIRouter(prefix="/api/admin/merges", tags=["admin-merges"])


@router.get("", response_model=PaginatedResponse[MergeEventListItem])
def list_merge_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: dict[str, str] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PaginatedResponse[MergeEventListItem]:
    total = db.scalar(select(func.count()).select_from(MergeEvent)) or 0
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    if page > total_pages and total > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page out of range.")

    events = list(
        db.scalars(
            select(MergeEvent)
            .order_by(MergeEvent.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return PaginatedResponse[MergeEventListItem](
        items=[
            MergeEventListItem(
                id=e.id,
                source_incident_id=e.source_incident_id,
                target_incident_id=e.target_incident_id,
                report_id=e.report_id,
                matched_report_id=e.matched_report_id,
                action=e.action,
                actor=e.actor,
                candidate_classification=e.candidate_classification,
                heuristic_score=e.heuristic_score,
                created_at=e.created_at,
                reversed_at=e.reversed_at,
            )
            for e in events
        ],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{merge_event_id}", response_model=MergeEventDetailResponse)
def get_merge_event(
    merge_event_id: str,
    _admin: dict[str, str] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> MergeEventDetailResponse:
    event = db.get(MergeEvent, merge_event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merge event not found.")

    execution = db.scalar(
        select(MergeExecution).where(MergeExecution.merge_event_id == event.id).limit(1)
    )
    return MergeEventDetailResponse(
        id=event.id,
        source_incident_id=event.source_incident_id,
        target_incident_id=event.target_incident_id,
        report_id=event.report_id,
        matched_report_id=event.matched_report_id,
        action=event.action,
        actor=event.actor,
        candidate_classification=event.candidate_classification,
        heuristic_score=event.heuristic_score,
        created_at=event.created_at,
        reversed_at=event.reversed_at,
        transferred_report_ids=list(event.transferred_report_ids or []),
        target_incident_report_ids_before=list(event.target_incident_report_ids_before or []),
        source_incident_status_before=event.source_incident_status_before,
        target_incident_status_before=event.target_incident_status_before,
        sha256_match=event.sha256_match,
        phash_hamming_distance=event.phash_hamming_distance,
        phash_similarity=event.phash_similarity,
        text_similarity=event.text_similarity,
        geo_distance_meters=event.geo_distance_meters,
        category_match=event.category_match,
        policy_snapshot=dict(event.policy_snapshot or {}),
        reversal_merge_event_id=event.reversal_merge_event_id,
        merge_execution_status=execution.status.value if execution else None,
        merge_execution_error=execution.last_error if execution else None,
    )


@router.post("/{merge_event_id}/reverse", response_model=MergeEventDetailResponse)
def reverse_merge_event(
    merge_event_id: str,
    _admin: dict[str, str] = Depends(get_current_admin),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> MergeEventDetailResponse:
    event = db.get(MergeEvent, merge_event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merge event not found.")
    try:
        reversal = reverse_merge(db, merge_event=event, actor_username=_admin["username"])
        db.commit()
        db.refresh(reversal)
    except MergeReversalConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return get_merge_event(reversal.id, _admin=_admin, db=db)
