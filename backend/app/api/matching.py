from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import MatchingJob, MatchSuggestion, Report
from app.schemas import MatchingJobResponse, MatchSuggestionResponse

router = APIRouter(prefix="/api/matching", tags=["matching"])


def _suggestion_to_response(s: MatchSuggestion) -> MatchSuggestionResponse:
    incident = s.incident
    matched_report = s.matched_report
    return MatchSuggestionResponse(
        id=s.id,
        report_id=s.report_id,
        incident_id=s.incident_id,
        matched_report_id=s.matched_report_id,
        similarity_score=s.similarity_score,
        status=s.status.value,
        created_at=s.created_at,
        incident_title=incident.title if incident else None,
        incident_category=incident.category.value if incident else None,
        incident_status=incident.status.value if incident else None,
        incident_latitude=incident.latitude if incident else None,
        incident_longitude=incident.longitude if incident else None,
        matched_report_description=matched_report.description if matched_report else None,
        sha256_match=s.sha256_match,
        phash_hamming_distance=s.phash_hamming_distance,
        phash_similarity=s.phash_similarity,
        text_similarity=s.text_similarity,
        geo_distance_meters=s.geo_distance_meters,
        category_match=s.category_match,
        candidate_classification=s.candidate_classification,
    )


@router.get("/reports/{report_id}", response_model=MatchingJobResponse | None)
def get_matching_status(report_id: str, db: Session = Depends(get_db)) -> MatchingJobResponse | None:
    """Return latest matching job and suggestions for a report. Used by frontend polling."""
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    job = db.scalar(
        select(MatchingJob)
        .where(MatchingJob.report_id == report_id)
        .order_by(MatchingJob.created_at.desc())
        .limit(1)
    )
    if not job:
        return None

    suggestions = list(
        db.scalars(
            select(MatchSuggestion)
            .options(selectinload(MatchSuggestion.incident), selectinload(MatchSuggestion.matched_report))
            .where(MatchSuggestion.report_id == report_id)
            .order_by(MatchSuggestion.similarity_score.desc())
        ).all()
    )

    return MatchingJobResponse(
        id=job.id,
        report_id=job.report_id,
        status=job.status.value,
        error_message=job.error_message,
        attempts=job.attempts,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        suggestions=[_suggestion_to_response(s) for s in suggestions],
    )


@router.get("/suggestions/{report_id}", response_model=list[MatchSuggestionResponse])
def get_suggestions(report_id: str, db: Session = Depends(get_db)) -> list[MatchSuggestionResponse]:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    suggestions = list(
        db.scalars(
            select(MatchSuggestion)
            .options(selectinload(MatchSuggestion.incident), selectinload(MatchSuggestion.matched_report))
            .where(MatchSuggestion.report_id == report_id)
            .order_by(MatchSuggestion.similarity_score.desc())
        ).all()
    )
    return [_suggestion_to_response(s) for s in suggestions]