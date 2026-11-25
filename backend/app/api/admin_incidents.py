import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_admin, require_csrf
from app.database import get_db
from app.models import ActorTypeEnum, AdminAuditLog, Incident, Report, StatusEnum
from app.schemas import (
    AdminIncidentListItem,
    AdminIncidentStatusUpdateRequest,
    IncidentDetailResponse,
    PaginatedResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/incidents", tags=["admin-incidents"])


@router.get("", response_model=PaginatedResponse[AdminIncidentListItem])
def list_admin_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: StatusEnum | None = Query(None, alias="status"),
    _admin: dict[str, str] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PaginatedResponse[AdminIncidentListItem]:
    base = select(Incident)
    if status_filter is not None:
        base = base.where(Incident.status == status_filter)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    total_pages = max(1, math.ceil(total / page_size)) if total else 1
    if page > total_pages and total > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page out of range.")

    stmt = (
        base.options(selectinload(Incident.reports))
        .order_by(Incident.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    incidents = list(db.scalars(stmt).all())
    items = [
        AdminIncidentListItem(
            id=inc.id,
            title=inc.title,
            description=inc.description,
            category=inc.category,
            latitude=inc.latitude,
            longitude=inc.longitude,
            status=inc.status,
            merged_into_incident_id=inc.merged_into_incident_id,
            created_at=inc.created_at,
            updated_at=inc.updated_at,
            report_count=len(inc.reports),
        )
        for inc in incidents
    ]
    return PaginatedResponse[AdminIncidentListItem](
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_admin_incident(
    incident_id: str,
    _admin: dict[str, str] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Incident:
    stmt = select(Incident).options(selectinload(Incident.reports)).where(Incident.id == incident_id)
    incident = db.scalar(stmt)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    return incident


@router.patch("/{incident_id}/status", response_model=IncidentDetailResponse)
def update_admin_incident_status(
    incident_id: str,
    payload: AdminIncidentStatusUpdateRequest,
    _admin: dict[str, str] = Depends(get_current_admin),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> Incident:
    new_status = StatusEnum(payload.status.value) if hasattr(payload.status, "value") else StatusEnum(payload.status)

    if new_status == StatusEnum.MERGED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Manual status change to merged is not allowed.",
        )

    incident = db.scalar(
        select(Incident)
        .options(selectinload(Incident.reports))
        .where(Incident.id == incident_id)
        .with_for_update()
    )
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")

    if incident.status == StatusEnum.MERGED or incident.merged_into_incident_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Merged incidents cannot be manually reopened or closed.",
        )

    if incident.status == new_status:
        return incident

    if incident.status not in {StatusEnum.OPEN, StatusEnum.CLOSED} or new_status not in {StatusEnum.OPEN, StatusEnum.CLOSED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only open/closed status transitions are supported.",
        )

    old_status = incident.status
    incident.status = new_status
    db.add(incident)
    db.add(
        AdminAuditLog(
            actor_type=ActorTypeEnum.ADMIN,
            admin_username=_admin["username"],
            system_actor=None,
            action="INCIDENT_STATUS_UPDATED",
            target_type="incident",
            target_id=incident.id,
            metadata_json={
                "old_status": old_status.value,
                "new_status": new_status.value,
            },
        )
    )
    db.commit()
    db.refresh(incident)
    # reload reports relationship after refresh
    incident = db.scalar(
        select(Incident).options(selectinload(Incident.reports)).where(Incident.id == incident_id)
    )
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    return incident
