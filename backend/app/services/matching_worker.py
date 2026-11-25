"""Database-backed background worker for multisignal duplicate detection (Phase D1/D2).

Sequential processing, no Redis/Celery. Preserves Phase 3 job lifecycle.
D2: after matching evaluation completes, may execute auto-merge when enabled.
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
from app.models import (
    ActorTypeEnum,
    MatchingJob,
    MatchingJobStatusEnum,
    MatchSuggestion,
    MergeExecution,
    MergeExecutionStatusEnum,
    Report,
    SuggestionStatusEnum,
)
from app.services.embeddings import EmbeddingService
from app.services.image_fingerprint import compute_phash, compute_sha256
from app.services.incident_merge import (
    MergeConflictError,
    execute_auto_merge,
    get_or_create_merge_execution,
    schedule_merge_retry,
)
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
                await asyncio.to_thread(self._process_due_merge_retries)
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
        """Compute missing SHA-256/pHash from stored image. Returns True if fingerprints changed."""
        if report.sha256_hash and report.phash:
            return False
        image_path = Path(settings.upload_dir) / Path(report.image_path).name
        if not image_path.exists():
            logger.warning("Image missing for report %s at %s; fingerprinting skipped", report.id, image_path)
            return False
        try:
            content = image_path.read_bytes()
        except Exception:
            logger.exception("Failed to read image for report %s", report.id)
            return False
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

            changed = self._ensure_fingerprints(report)
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

            self._persist_suggestions(db, report, job, results)

            # Matching evaluation is complete regardless of merge outcome.
            job.status = MatchingJobStatusEnum.COMPLETED
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            job.error_message = None
            db.add(job)
            db.commit()
            logger.info("Matching job %s completed with %s suggestions", job.id, len(results))

            # D2: auto-merge attempt separated from matching completion.
            self._attempt_auto_merge(db, report.id, results)

        except Exception as exc:
            db.rollback()
            job = db.get(MatchingJob, job_id)
            if not job:
                return
            logger.exception("Matching job %s failed", job_id)
            final = job.attempts >= self._max_retries
            self._mark_failed(db, job, str(exc), final=final)

    def _persist_suggestions(
        self, db: Session, report: Report, job: MatchingJob, results: list
    ) -> None:
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
                # Preserve terminal/superseded states from prior merge decisions.
                if existing.status not in (
                    SuggestionStatusEnum.AUTO_MERGED,
                    SuggestionStatusEnum.SUPERSEDED,
                ):
                    existing.similarity_score = r.heuristic_score
                    existing.matched_report_id = r.matched_report_id
                    existing.status = SuggestionStatusEnum.PENDING
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
        db.commit()

    def _attempt_auto_merge(self, db: Session, report_id: str, results: list) -> None:
        if not settings.auto_merge_enabled:
            return
        # Only top AUTO_MERGE_CANDIDATE may auto-merge.
        top = results[0] if results else None
        if not top or top.candidate_classification != CandidateClassification.AUTO_MERGE_CANDIDATE:
            return

        try:
            suggestion = db.scalar(
                select(MatchSuggestion)
                .options(selectinload(MatchSuggestion.report), selectinload(MatchSuggestion.incident))
                .where(
                    MatchSuggestion.report_id == report_id,
                    MatchSuggestion.incident_id == top.incident_id,
                )
            )
            if not suggestion:
                return
            if suggestion.status in (SuggestionStatusEnum.AUTO_MERGED, SuggestionStatusEnum.SUPERSEDED):
                return

            execution = get_or_create_merge_execution(db, suggestion=suggestion)
            if execution.status == MergeExecutionStatusEnum.SUCCEEDED:
                db.commit()
                return

            event = execute_auto_merge(
                db,
                suggestion=suggestion,
                ranked_candidates=results,
                settings=settings,
                actor_type=ActorTypeEnum.SYSTEM,
                system_actor="matching_worker",
            )
            if event is None:
                # Disabled or ineligible (no-op); keep suggestion pending for D3.
                db.commit()
                return
            db.commit()
            logger.info("Auto-merged report %s into incident %s (event=%s)", report_id, top.incident_id, event.id)
        except MergeConflictError as exc:
            db.rollback()
            # Permanent/safe conflict: keep suggestion pending for D3 moderation.
            try:
                suggestion = db.scalar(
                    select(MatchSuggestion).where(
                        MatchSuggestion.report_id == report_id,
                        MatchSuggestion.incident_id == top.incident_id,
                    )
                )
                if suggestion:
                    execution = get_or_create_merge_execution(db, suggestion=suggestion)
                    schedule_merge_retry(db, execution, str(exc), settings=settings, permanent=True)
                    db.commit()
            except Exception:
                db.rollback()
                logger.exception("Failed to record merge conflict for report %s", report_id)
            logger.info("Auto-merge skipped for report %s: %s", report_id, exc)
        except Exception as exc:
            db.rollback()
            logger.exception("Auto-merge execution failed for report %s", report_id)
            try:
                suggestion = db.scalar(
                    select(MatchSuggestion).where(
                        MatchSuggestion.report_id == report_id,
                        MatchSuggestion.incident_id == top.incident_id,
                    )
                )
                if suggestion:
                    execution = get_or_create_merge_execution(db, suggestion=suggestion)
                    schedule_merge_retry(db, execution, str(exc), settings=settings, permanent=False)
                    db.commit()
            except Exception:
                db.rollback()
                logger.exception("Failed to schedule merge retry for report %s", report_id)

    def _process_due_merge_retries(self) -> None:
        if not settings.auto_merge_enabled:
            return
        db = SessionLocal()
        try:
            now = utc_now()
            due = list(
                db.scalars(
                    select(MergeExecution)
                    .options(selectinload(MergeExecution.match_suggestion).selectinload(MatchSuggestion.report))
                    .where(
                        MergeExecution.status == MergeExecutionStatusEnum.RETRYING,
                        MergeExecution.next_retry_at.is_not(None),
                        MergeExecution.next_retry_at <= now,
                    )
                    .order_by(MergeExecution.next_retry_at.asc())
                    .limit(10)
                ).all()
            )
            for execution in due:
                self._retry_merge_execution(db, execution.id)
        finally:
            db.close()

    def _retry_merge_execution(self, db: Session, execution_id: str) -> None:
        embedding_service = EmbeddingService.get_instance()
        try:
            execution = db.scalar(
                select(MergeExecution)
                .options(selectinload(MergeExecution.match_suggestion).selectinload(MatchSuggestion.report))
                .where(MergeExecution.id == execution_id)
            )
            if not execution or execution.status != MergeExecutionStatusEnum.RETRYING:
                return
            suggestion = execution.match_suggestion
            report = suggestion.report if suggestion else None
            if not suggestion or not report:
                execution.status = MergeExecutionStatusEnum.FAILED
                execution.last_error = "suggestion_or_report_missing"
                execution.completed_at = utc_now()
                db.add(execution)
                db.commit()
                return
            if suggestion.status == SuggestionStatusEnum.AUTO_MERGED:
                execution.status = MergeExecutionStatusEnum.SUCCEEDED
                execution.completed_at = utc_now()
                db.add(execution)
                db.commit()
                return

            # Recompute candidates for safety using current DB state.
            candidates_stmt = (
                select(Report)
                .options(selectinload(Report.incident))
                .where(Report.incident_id != report.incident_id)
            )
            candidates = list(db.scalars(candidates_stmt).all())
            candidate_dicts = []
            for cand in candidates:
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

            target_embedding = report.embedding
            if not target_embedding and embedding_service.is_ready():
                target_embedding = embedding_service.encode(report.description)
                if target_embedding:
                    report.embedding = target_embedding
                    db.add(report)
                    db.commit()
                    db.refresh(report)

            results = find_candidate_incidents_multisignal(
                target_report_id=report.id,
                target_incident_id=report.incident_id,
                target_embedding=target_embedding,
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
            event = execute_auto_merge(
                db,
                suggestion=suggestion,
                ranked_candidates=results,
                settings=settings,
                actor_type=ActorTypeEnum.SYSTEM,
                system_actor="matching_worker",
            )
            if event is None:
                raise MergeConflictError("merge_not_eligible_on_retry")
            db.commit()
        except MergeConflictError as exc:
            db.rollback()
            execution = db.get(MergeExecution, execution_id)
            if execution:
                schedule_merge_retry(db, execution, str(exc), settings=settings, permanent=True)
                db.commit()
        except Exception as exc:
            db.rollback()
            logger.exception("Merge retry failed for execution %s", execution_id)
            execution = db.get(MergeExecution, execution_id)
            if execution:
                schedule_merge_retry(db, execution, str(exc), settings=settings, permanent=False)
                db.commit()

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
