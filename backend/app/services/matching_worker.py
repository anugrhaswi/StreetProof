"""Database-backed background worker for multisignal duplicate detection (Phase D1).

Sequential processing, no Redis/Celery. Preserves Phase 3 job lifecycle.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import SessionLocal
from app.models import MatchingJob, MatchingJobStatusEnum, MatchSuggestion, Report, SuggestionStatusEnum
from app.services.embeddings import EmbeddingService
from app.services.image_fingerprint import compute_phash, compute_sha256
from app.services.matching_engine import CandidateClassification, find_candidate_incidents_multisignal

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MatchingWorker:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._interval = max(1, int(settings.matching_worker_interval_seconds))
        self._max_retries = max(0, int(settings.matching_max_retries))

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        await asyncio.to_thread(self._recover_interrupted_jobs)
        self._task = asyncio.create_task(self._run_loop(), name="matching-worker")
        logger.info("Matching worker started (interval=%ss, max_retries=%s)", self._interval, self._max_retries)

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Matching worker stopped")

    def _recover_interrupted_jobs(self) -> None:
        db = SessionLocal()
        try:
            stmt = (
                update(MatchingJob)
                .where(MatchingJob.status == MatchingJobStatusEnum.PROCESSING)
                .values(status=MatchingJobStatusEnum.PENDING, updated_at=utc_now(), error_message=None)
            )
            result = db.execute(stmt)
            db.commit()
            if result.rowcount:
                logger.info("Recovered %s interrupted matching jobs", result.rowcount)
        except Exception:
            db.rollback()
            logger.exception("Failed to recover interrupted matching jobs")
        finally:
            db.close()

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.to_thread(self._process_next_job)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Matching worker loop error")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval)
            except asyncio.TimeoutError:
                pass

    def _claim_next_job(self, db: Session) -> str | None:
        job = db.scalar(
            select(MatchingJob)
            .where(MatchingJob.status == MatchingJobStatusEnum.PENDING)
            .order_by(MatchingJob.created_at.asc())
            .limit(1)
        )
        if not job:
            return None
        stmt = (
            update(MatchingJob)
            .where(MatchingJob.id == job.id, MatchingJob.status == MatchingJobStatusEnum.PENDING)
            .values(
                status=MatchingJobStatusEnum.PROCESSING,
                attempts=MatchingJob.attempts + 1,
                updated_at=utc_now(),
                error_message=None,
            )
        )
        result = db.execute(stmt)
        db.commit()
        if result.rowcount and result.rowcount > 0:
            return job.id
        return None

    def _process_next_job(self) -> None:
        embedding_service = EmbeddingService.get_instance()
        if not embedding_service.is_ready():
            return
        db = SessionLocal()
        try:
            job_id = self._claim_next_job(db)
            if not job_id:
                return
            self._process_job(db, job_id, embedding_service)
        finally:
            db.close()

    def _ensure_fingerprints(self, report: Report) -> bool:
        """Compute missing SHA-256/pHash from stored image. Returns True if fingerprints usable."""
        if report.sha256_hash and report.phash:
            return True
        image_path = Path(settings.upload_dir) / Path(report.image_path).name
        if not image_path.exists():
            logger.warning("Image missing for report %s at %s; fingerprinting skipped", report.id, image_path)
            return bool(report.phash)  # pHash may exist from old data
        try:
            content = image_path.read_bytes()
        except Exception:
            logger.exception("Failed to read image for report %s", report.id)
            return bool(report.phash)
        changed = False
        if not report.sha256_hash:
            try:
                report.sha256_hash = compute_sha256(content)
                changed = True
            except Exception:
                logger.exception("Failed to compute SHA-256 for report %s", report.id)
        if not report.phash:
            try:
                ph = compute_phash(content, hash_size=int(settings.phash_hash_size))
                if ph:
                    report.phash = ph
                    report.phash_size = int(settings.phash_hash_size)
                    changed = True
            except Exception:
                logger.exception("Failed to compute pHash for report %s", report.id)
        return changed

    def _process_job(self, db: Session, job_id: str, embedding_service: EmbeddingService) -> None:
        job = db.get(MatchingJob, job_id)
        if not job:
            return
        try:
            report = db.get(Report, job.report_id)
            if not report:
                self._mark_failed(db, job, "Report not found", final=True)
                return

            changed = False
            if self._ensure_fingerprints(report):
                changed = True

            # Ensure embedding.
            if not report.embedding:
                embedding = embedding_service.encode(report.description)
                if embedding is None:
                    raise RuntimeError("Failed to generate embedding for report")
                report.embedding = embedding
                changed = True

            if changed:
                db.add(report)
                db.commit()
                db.refresh(report)

            candidates_stmt = (
                select(Report)
                .options(selectinload(Report.incident))
                .where(Report.incident_id != report.incident_id)
            )
            candidates = list(db.scalars(candidates_stmt).all())

            # Lazy backfill fingerprints for candidates when missing (best-effort).
            candidate_dicts = []
            any_candidate_changed = False
            for cand in candidates:
                if not cand.sha256_hash or not cand.phash:
                    if self._ensure_fingerprints(cand):
                        any_candidate_changed = True
                        db.add(cand)
                incident = cand.incident
                candidate_dicts.append(
                    {
                        "report_id": cand.id,
                        "incident_id": cand.incident_id,
                        "report_description": cand.description,
                        "embedding": cand.embedding,
                        "sha256_hash": cand.sha256_hash,
                        "phash": cand.phash,
                        "category": cand.category.value if cand.category else None,
                        "latitude": cand.latitude,
                        "longitude": cand.longitude,
                        "incident_title": incident.title if incident else "",
                        "incident_category": incident.category.value if incident else "",
                        "incident_status": incident.status.value if incident else "",
                        "incident_latitude": incident.latitude if incident else 0.0,
                        "incident_longitude": incident.longitude if incident else 0.0,
                    }
                )
            if any_candidate_changed:
                db.commit()

            results = find_candidate_incidents_multisignal(
                target_report_id=report.id,
                target_incident_id=report.incident_id,
                target_embedding=report.embedding,
                target_sha256=report.sha256_hash,
                target_phash=report.phash,
                target_category=report.category.value if report.category else None,
                target_lat=report.latitude,
                target_lng=report.longitude,
                candidate_reports=candidate_dicts,
                matching_radius_meters=int(settings.matching_radius_meters),
                auto_merge_radius_meters=int(settings.auto_merge_radius_meters),
                phash_similarity_threshold=float(settings.phash_similarity_threshold),
                phash_review_threshold=float(settings.phash_review_threshold),
                text_similarity_threshold=float(settings.text_similarity_threshold),
                auto_merge_text_threshold=float(settings.auto_merge_text_threshold),
                max_candidates=int(settings.max_candidates),
            )

            for r in results:
                if r.candidate_classification == CandidateClassification.NO_MATCH:
                    continue
                existing = db.scalar(
                    select(MatchSuggestion).where(
                        MatchSuggestion.report_id == report.id,
                        MatchSuggestion.incident_id == r.incident_id,
                    )
                )
                if existing:
                    existing.similarity_score = r.heuristic_score
                    existing.matched_report_id = r.matched_report_id
                    existing.sha256_match = r.sha256_match
                    existing.phash_hamming_distance = r.phash_hamming_distance
                    existing.phash_similarity = r.phash_similarity
                    existing.text_similarity = r.text_similarity
                    existing.geo_distance_meters = r.geo_distance_meters
                    existing.category_match = r.category_match
                    existing.candidate_classification = r.candidate_classification.value
                    db.add(existing)
                    continue

                suggestion = MatchSuggestion(
                    report_id=report.id,
                    incident_id=r.incident_id,
                    matched_report_id=r.matched_report_id,
                    similarity_score=r.heuristic_score,
                    status=SuggestionStatusEnum.PENDING,
                    sha256_match=r.sha256_match,
                    phash_hamming_distance=r.phash_hamming_distance,
                    phash_similarity=r.phash_similarity,
                    text_similarity=r.text_similarity,
                    geo_distance_meters=r.geo_distance_meters,
                    category_match=r.category_match,
                    candidate_classification=r.candidate_classification.value,
                )
                db.add(suggestion)
                try:
                    db.flush()
                except IntegrityError:
                    db.rollback()
                    db.refresh(job)
                    existing = db.scalar(
                        select(MatchSuggestion).where(
                            MatchSuggestion.report_id == report.id,
                            MatchSuggestion.incident_id == r.incident_id,
                        )
                    )
                    if existing:
                        existing.similarity_score = r.heuristic_score
                        existing.matched_report_id = r.matched_report_id
                        existing.sha256_match = r.sha256_match
                        existing.phash_hamming_distance = r.phash_hamming_distance
                        existing.phash_similarity = r.phash_similarity
                        existing.text_similarity = r.text_similarity
                        existing.geo_distance_meters = r.geo_distance_meters
                        existing.category_match = r.category_match
                        existing.candidate_classification = r.candidate_classification.value
                        db.add(existing)
                        db.flush()

            job.status = MatchingJobStatusEnum.COMPLETED
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            job.error_message = None
            db.add(job)
            db.commit()
            logger.info("Matching job %s completed with %s suggestions", job.id, len(results))

        except Exception as exc:
            db.rollback()
            job = db.get(MatchingJob, job_id)
            if not job:
                return
            logger.exception("Matching job %s failed", job_id)
            final = job.attempts >= self._max_retries
            self._mark_failed(db, job, str(exc), final=final)

    def _mark_failed(self, db: Session, job: MatchingJob, message: str, *, final: bool) -> None:
        job.error_message = message[:1000]
        job.updated_at = utc_now()
        if final:
            job.status = MatchingJobStatusEnum.FAILED
            job.completed_at = utc_now()
        else:
            job.status = MatchingJobStatusEnum.PENDING
            job.completed_at = None
        db.add(job)
        db.commit()
