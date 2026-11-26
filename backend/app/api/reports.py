import math

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Incident, MatchingJob, MatchingJobStatusEnum, Report, StatusEnum
from app.schemas import CategoryEnum, PaginatedResponse, ReportResponse
from app.services.image_service import delete_image, save_image

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    description: str = Form(..., min_length=10, max_length=5000),
    category: CategoryEnum = Form(...),
    latitude: float = Form(..., ge=-90, le=90),
    longitude: float = Form(..., ge=-180, le=180),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Report:
    image_path, sha256_hash, phash_hex, phash_size = await save_image(image)

    try:
        incident = Incident(
            title=f"{category.value.title()} at {latitude:.4f}, {longitude:.4f}",
            description=description,
            category=category,
            latitude=latitude,
            longitude=longitude,
            status=StatusEnum.OPEN,
        )
        db.add(incident)
        db.flush()  # assign incident.id

        report = Report(
            description=description,
            category=category,
            latitude=latitude,
            longitude=longitude,
            image_path=image_path,
            sha256_hash=sha256_hash,
            phash=phash_hex,
            phash_size=phash_size,
            incident_id=incident.id,
        )
        db.add(report)
        db.flush()  # assign report.id

        matching_job = MatchingJob(
            report_id=report.id,
            status=MatchingJobStatusEnum.PENDING,
        )
        db.add(matching_job)

        db.commit()
        db.refresh(report)
        db.refresh(incident)
        report.incident = incident
        return report
    except Exception:
        db.rollback()
        # Best-effort cleanup for stored image on DB failure.
        try:
            delete_image(image_path)
        except Exception:
            pass
        raise


@router.get("", response_model=PaginatedResponse[ReportResponse])
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ReportResponse]:
    total = db.scalar(select(func.count()).select_from(Report)) or 0
    total_pages = max(1, math.ceil(total / page_size)) if total else 1
    if page > total_pages and total > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page out of range.")

    stmt = (
        select(Report)
        .options(selectinload(Report.incident))
        .order_by(Report.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    reports = list(db.scalars(stmt).all())
    return PaginatedResponse[ReportResponse](
        items=reports,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: str, db: Session = Depends(get_db)) -> Report:
    stmt = select(Report).options(selectinload(Report.incident)).where(Report.id == report_id)
    report = db.scalar(stmt)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return report
