from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.models import MatchingJob, MatchSuggestion, Report
from app.schemas import MatchingJobResponse, MatchSuggestionResponse, PublicMatchingStatusResponse

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


@router.get("/reports/{report_id}", response_model=PublicMatchingStatusResponse | None)
def get_matching_status(report_id: str, db: Session = Depends(get_db)) -> PublicMatchingStatusResponse | None:
    """Return minimal public matching status for frontend polling. No internal evidence exposed."""
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

    suggestion_count = db.scalar(
        select(func.count()).select_from(MatchSuggestion).where(MatchSuggestion.report_id == report_id)
    ) or 0

    return PublicMatchingStatusResponse(
        status=job.status.value,
        suggestion_count=int(suggestion_count),
        error_message="Matching failed. Please try again later." if job.status.value == "failed" else None,
    )


@router.get("/suggestions/{report_id}", response_model=list[MatchSuggestionResponse])
def get_suggestions(
    report_id: str,
    _admin: dict[str, str] = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[MatchSuggestionResponse]:
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