import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Incident
from app.schemas import IncidentDetailResponse, PaginatedResponse

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=PaginatedResponse[IncidentDetailResponse])
def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse[IncidentDetailResponse]:
    total = db.scalar(select(func.count()).select_from(Incident)) or 0
    total_pages = max(1, math.ceil(total / page_size)) if total else 1
    if page > total_pages and total > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page out of range.")

    stmt = (
        select(Incident)
        .options(selectinload(Incident.reports))
        .order_by(Incident.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    incidents = list(db.scalars(stmt).all())
    return PaginatedResponse[IncidentDetailResponse](
        items=incidents,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(incident_id: str, db: Session = Depends(get_db)) -> Incident:
    stmt = select(Incident).options(selectinload(Incident.reports)).where(Incident.id == incident_id)
    incident = db.scalar(stmt)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    return incident
