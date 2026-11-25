import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Incident, Report, StatusEnum
from app.schemas import IncidentDetailResponse, IncidentMapResponse, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("/map", response_model=list[IncidentMapResponse])
def get_incidents_for_map(db: Session = Depends(get_db)) -> list[IncidentMapResponse]:
    stmt = (
        select(
            Incident.id,
            Incident.title,
            Incident.description,
            Incident.category,
            Incident.latitude,
            Incident.longitude,
            Incident.status,
            Incident.created_at,
            func.count(Report.id).label("report_count"),
        )
        .outerjoin(Report, Report.incident_id == Incident.id)
        .where(Incident.status != StatusEnum.MERGED)
        .group_by(Incident.id)
        .order_by(Incident.created_at.desc())
    )
    rows = db.execute(stmt).all()

    result: list[IncidentMapResponse] = []
    for row in rows:
        lat = row.latitude
        lng = row.longitude
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            logger.warning("Incident %s excluded from map: non-numeric coordinates", row.id)
            continue
        if not math.isfinite(float(lat)) or not math.isfinite(float(lng)):
            logger.warning("Incident %s excluded from map: non-finite coordinates", row.id)
            continue
        if not (-90 <= float(lat) <= 90) or not (-180 <= float(lng) <= 180):
            logger.warning("Incident %s excluded from map: out-of-range coordinates (%s, %s)", row.id, lat, lng)
            continue
        result.append(
            IncidentMapResponse(
                id=row.id,
                title=row.title,
                description=row.description,
                category=row.category,
                latitude=float(lat),
                longitude=float(lng),
                status=row.status,
                report_count=int(row.report_count or 0),
                created_at=row.created_at,
            )
        )
    return result


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
