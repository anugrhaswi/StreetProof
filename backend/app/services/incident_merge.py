"""Automatic incident merge service (Phase D2).

Safety properties:
- Merge execution is transactional and idempotent.
- Source incident becomes MERGED with merged_into_incident_id set.
- Original reports/photos are never deleted or modified except incident reassignment.
- Merge history is immutable (MergeEvent + AdminAuditLog).
- AUTO_MERGE_ENABLED defaults false; disabled path records suggestions only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import (
    ActorTypeEnum,
    AdminAuditLog,
    Incident,
    MatchSuggestion,
    MergeEvent,
    MergeExecution,
    MergeExecutionStatusEnum,
    Report,
    StatusEnum,
    SuggestionStatusEnum,
)
from app.services.matching_engine import (
    CandidateClassification,
    MultisignalCandidate,
    build_policy_snapshot,
    is_ambiguous_auto_merge,
)

logger = logging.getLogger(__name__)


class MergeConflictError(ValueError):
    """Safe, expected merge conflict (no partial merge committed)."""


class MergeReversalConflictError(ValueError):
    """Safe, expected reversal refusal."""


@dataclass
class MergeEligibilityResult:
    eligible: bool
    reason: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def merge_idempotency_key(report_id: str, incident_id: str) -> str:
    return f"merge:{report_id}:{incident_id}"


def check_auto_merge_eligibility(
    candidate: MultisignalCandidate,
    ranked_candidates: list[MultisignalCandidate],
    settings: Settings,
    actor_type: ActorTypeEnum = ActorTypeEnum.SYSTEM,
) -> MergeEligibilityResult:
    """Eligibility check. System merges are conservative; admin manual merges
    bypass threshold gates but still block contradictory evidence."""
    # Contradiction guards — always enforced
    if candidate.category_match is False:
        return MergeEligibilityResult(False, "contradictory_category")
    if candidate.phash_similarity is not None and candidate.phash_similarity < 0.0:
        return MergeEligibilityResult(False, "invalid_phash_similarity")

    # Exact image reuse at distant locations is suspicious evidence, not proof of same incident.
    if (
        candidate.sha256_match is True
        and candidate.geo_distance_meters is not None
        and candidate.geo_distance_meters > float(settings.matching_radius_meters)
    ):
        return MergeEligibilityResult(False, "sha256_far_apart")

    if actor_type == ActorTypeEnum.ADMIN:
        # Human-reviewed: bypass strict thresholds, keep contradiction/safety guards.
        if candidate.candidate_classification == CandidateClassification.NO_MATCH:
            return MergeEligibilityResult(False, "candidate_not_match")
        if candidate.geo_distance_meters is None:
            return MergeEligibilityResult(False, "missing_coordinates")
        return MergeEligibilityResult(True, "eligible_admin_override")

    if candidate.candidate_classification != CandidateClassification.AUTO_MERGE_CANDIDATE:
        return MergeEligibilityResult(False, "candidate_not_auto_merge")
    if is_ambiguous_auto_merge(ranked_candidates, settings.auto_merge_min_score_margin):
        return MergeEligibilityResult(False, "ambiguous_candidates")
    if settings.auto_merge_require_category and candidate.category_match is not True:
        return MergeEligibilityResult(False, "category_disagreement")
    if settings.auto_merge_require_geo:
        if candidate.geo_distance_meters is None:
            return MergeEligibilityResult(False, "missing_coordinates")
        if candidate.geo_distance_meters > float(settings.auto_merge_radius_meters):
            return MergeEligibilityResult(False, "outside_auto_merge_radius")
    if settings.auto_merge_require_text_support:
        if candidate.text_similarity is None:
            return MergeEligibilityResult(False, "missing_text_support")
        if candidate.text_similarity < float(settings.auto_merge_text_threshold):
            return MergeEligibilityResult(False, "insufficient_text_support")
    return MergeEligibilityResult(True, "eligible")


def _incident_report_ids(db: Session, incident_id: str) -> list[str]:
    rows = db.scalars(
        select(Report.id).where(Report.incident_id == incident_id).order_by(Report.created_at.asc(), Report.id.asc())
    ).all()
    return [str(r) for r in rows]


def _lock_incidents(db: Session, ids: list[str]) -> dict[str, Incident]:
    incidents: dict[str, Incident] = {}
    for incident_id in sorted(set(ids)):
        incident = db.scalar(select(Incident).where(Incident.id == incident_id).with_for_update())
        if incident is None:
            raise MergeConflictError(f"incident_not_found:{incident_id}")
        incidents[incident_id] = incident
    return incidents


def get_or_create_merge_execution(
    db: Session,
    *,
    suggestion: MatchSuggestion,
) -> MergeExecution:
    key = merge_idempotency_key(suggestion.report_id, suggestion.incident_id)
    existing = db.scalar(
        select(MergeExecution).where(MergeExecution.idempotency_key == key).with_for_update()
    )
    if existing:
        # Keep link consistent if suggestion row was recreated in edge cases.
        if existing.match_suggestion_id != suggestion.id:
            existing.match_suggestion_id = suggestion.id
            db.add(existing)
        return existing
    execution = MergeExecution(
        match_suggestion_id=suggestion.id,
        status=MergeExecutionStatusEnum.PENDING,
        attempt_count=0,
        idempotency_key=key,
    )
    db.add(execution)
    db.flush()
    return execution


def schedule_merge_retry(
    db: Session,
    execution: MergeExecution,
    error: str,
    *,
    settings: Settings,
    permanent: bool = False,
) -> None:
    execution.last_error = (error or "merge failed")[:1000]
    execution.updated_at = utc_now()
    if permanent or execution.attempt_count >= max(0, int(settings.merge_max_retries)):
        execution.status = MergeExecutionStatusEnum.FAILED
        execution.completed_at = utc_now()
        execution.next_retry_at = None
    else:
        delay = min(
            int(settings.merge_retry_max_delay_seconds),
            int(settings.merge_retry_base_delay_seconds) * (2 ** max(0, execution.attempt_count - 1)),
        )
        execution.status = MergeExecutionStatusEnum.RETRYING
        execution.next_retry_at = utc_now() + timedelta(seconds=max(1, delay))
        execution.completed_at = None
    db.add(execution)


def execute_auto_merge(
    db: Session,
    *,
    suggestion: MatchSuggestion,
    ranked_candidates: list[MultisignalCandidate],
    settings: Settings,
    actor_type: ActorTypeEnum = ActorTypeEnum.SYSTEM,
    system_actor: str = "matching_worker",
    admin_username: str | None = None,
) -> MergeEvent | None:
    """Execute merge transactionally. Caller owns transaction boundary.

    Returns MergeEvent on success, None when merge is not executed (ineligible/disabled).
    Raises MergeConflictError for safe conflicts. Other exceptions should be treated as retryable by caller.
    """
    # AUTO_MERGE_ENABLED gates automatic worker merges only; admin manual accept bypasses it.
    if not settings.auto_merge_enabled and actor_type != ActorTypeEnum.ADMIN:
        return None

    candidate = next(
        (c for c in ranked_candidates if c.incident_id == suggestion.incident_id and c.matched_report_id == suggestion.matched_report_id),
        None,
    )
    if candidate is None:
        candidate = next((c for c in ranked_candidates if c.incident_id == suggestion.incident_id), None)
    if candidate is None:
        raise MergeConflictError("candidate_not_found")

    eligibility = check_auto_merge_eligibility(candidate, ranked_candidates, settings, actor_type=actor_type)
    if not eligibility.eligible:
        raise MergeConflictError(eligibility.reason)

    execution = get_or_create_merge_execution(db, suggestion=suggestion)

    # Idempotency: existing successful merge for this suggestion/execution.
    if execution.status == MergeExecutionStatusEnum.SUCCEEDED and execution.merge_event_id:
        existing_event = db.get(MergeEvent, execution.merge_event_id)
        if existing_event and existing_event.reversed_at is None:
            return existing_event

    execution.status = MergeExecutionStatusEnum.PENDING
    execution.attempt_count += 1
    execution.started_at = execution.started_at or utc_now()
    execution.last_error = None
    execution.next_retry_at = None
    execution.completed_at = None
    db.add(execution)
    db.flush()

    report = db.scalar(select(Report).where(Report.id == suggestion.report_id).with_for_update())
    if report is None:
        raise MergeConflictError("report_not_found")

    matched_report = db.get(Report, suggestion.matched_report_id)
    # matched_report may be missing; preserve evidence from suggestion/candidate.

    source_incident_id = report.incident_id
    target_incident_id = suggestion.incident_id
    if source_incident_id == target_incident_id:
        raise MergeConflictError("same_incident")

    incidents = _lock_incidents(db, [source_incident_id, target_incident_id])
    source_incident = incidents[source_incident_id]
    target_incident = incidents[target_incident_id]

    if source_incident.status == StatusEnum.MERGED:
        raise MergeConflictError("source_already_merged")
    if target_incident.status != StatusEnum.OPEN:
        raise MergeConflictError("target_not_open")
    if source_incident.status != StatusEnum.OPEN:
        raise MergeConflictError("source_not_open")

    # Conservative: re-check no existing merge event for same report/source/target.
    existing_same = db.scalar(
        select(MergeEvent).where(
            MergeEvent.report_id == report.id,
            MergeEvent.source_incident_id == source_incident.id,
            MergeEvent.target_incident_id == target_incident.id,
            MergeEvent.action == "AUTOMATIC_INCIDENT_MERGE",
            MergeEvent.reversed_at.is_(None),
        )
    )
    if existing_same:
        execution.status = MergeExecutionStatusEnum.SUCCEEDED
        execution.merge_event_id = existing_same.id
        execution.completed_at = utc_now()
        db.add(execution)
        return existing_same

    # Snapshot actual DB state immediately before merge.
    source_report_ids_before = _incident_report_ids(db, source_incident.id)
    target_report_ids_before = _incident_report_ids(db, target_incident.id)
    transferred_report_ids = [report.id]

    # Re-check candidate incident still valid (not merged away).
    if target_incident.merged_into_incident_id:
        raise MergeConflictError("target_merged_away")

    # Perform merge: move only the newly evaluated report.
    report.incident_id = target_incident.id
    db.add(report)

    # Mark source incident merged only if it no longer has other reports.
    remaining_source_reports = [rid for rid in source_report_ids_before if rid != report.id]
    if not remaining_source_reports:
        source_incident.status = StatusEnum.MERGED
        source_incident.merged_into_incident_id = target_incident.id
        source_incident.updated_at = utc_now()
        db.add(source_incident)

    target_incident.updated_at = utc_now()
    db.add(target_incident)

    merge_event = MergeEvent(
        source_incident_id=source_incident.id,
        target_incident_id=target_incident.id,
        report_id=report.id,
        matched_report_id=matched_report.id if matched_report else suggestion.matched_report_id,
        action="AUTOMATIC_INCIDENT_MERGE",
        actor=system_actor if actor_type == ActorTypeEnum.SYSTEM else "admin",
        transferred_report_ids=transferred_report_ids,
        target_incident_report_ids_before=target_report_ids_before,
        source_incident_status_before=source_incident.status.value if remaining_source_reports else StatusEnum.OPEN.value,
        target_incident_status_before=StatusEnum.OPEN.value,
        sha256_match=candidate.sha256_match,
        phash_hamming_distance=candidate.phash_hamming_distance,
        phash_similarity=candidate.phash_similarity,
        text_similarity=candidate.text_similarity,
        geo_distance_meters=candidate.geo_distance_meters,
        category_match=candidate.category_match,
        candidate_classification=candidate.candidate_classification.value,
        heuristic_score=candidate.heuristic_score,
        policy_snapshot=build_policy_snapshot(settings),
    )
    db.add(merge_event)
    db.flush()

    # Mark winning suggestion as AUTO_MERGED.
    suggestion.status = SuggestionStatusEnum.AUTO_MERGED
    suggestion.reviewed_at = utc_now()
    db.add(suggestion)

    # Supersede competing suggestions for same report only.
    competing = db.scalars(
        select(MatchSuggestion).where(
            MatchSuggestion.report_id == report.id,
            MatchSuggestion.id != suggestion.id,
            MatchSuggestion.status == SuggestionStatusEnum.PENDING,
        )
    ).all()
    for other in competing:
        other.status = SuggestionStatusEnum.SUPERSEDED
        other.reviewed_at = utc_now()
        db.add(other)

    execution.status = MergeExecutionStatusEnum.SUCCEEDED
    execution.merge_event_id = merge_event.id
    execution.completed_at = utc_now()
    execution.last_error = None
    execution.next_retry_at = None
    db.add(execution)

    merge_action = "MANUAL_INCIDENT_MERGE" if actor_type == ActorTypeEnum.ADMIN else "AUTOMATIC_INCIDENT_MERGE"
    merge_event.action = merge_action
    db.add(merge_event)

    audit = AdminAuditLog(
        actor_type=actor_type,
        admin_username=admin_username if actor_type == ActorTypeEnum.ADMIN else None,
        system_actor=system_actor if actor_type == ActorTypeEnum.SYSTEM else None,
        action=merge_action,
        target_type="merge_event",
        target_id=merge_event.id,
        merge_event_id=merge_event.id,
        metadata_json={
            "source_incident_id": source_incident.id,
            "target_incident_id": target_incident.id,
            "report_id": report.id,
            "matched_report_id": merge_event.matched_report_id,
            "transferred_report_ids": transferred_report_ids,
            "heuristic_score": candidate.heuristic_score,
            "candidate_classification": candidate.candidate_classification.value,
            "idempotency_key": execution.idempotency_key,
        },
    )
    db.add(audit)
    db.flush()
    return merge_event


def reverse_merge(
    db: Session,
    *,
    merge_event: MergeEvent,
    actor_username: str,
) -> MergeEvent:
    """Conservative reversal. Caller owns transaction boundary.

    Raises MergeReversalConflictError with clear explanation on any unsafe condition.
    """
    locked_event = db.scalar(select(MergeEvent).where(MergeEvent.id == merge_event.id).with_for_update())
    if locked_event is None:
        raise MergeReversalConflictError("merge_event_not_found")
    if locked_event.action != "AUTOMATIC_INCIDENT_MERGE":
        raise MergeReversalConflictError("not_an_automatic_merge_event")
    if locked_event.reversed_at is not None:
        raise MergeReversalConflictError("merge_event_already_reversed")

    # No subsequent merge events involving either incident.
    incident_ids = [i for i in [locked_event.source_incident_id, locked_event.target_incident_id] if i]
    subsequent = db.scalar(
        select(func.count())
        .select_from(MergeEvent)
        .where(
            MergeEvent.id != locked_event.id,
            MergeEvent.created_at > locked_event.created_at,
            (
                (MergeEvent.source_incident_id.in_(incident_ids))
                | (MergeEvent.target_incident_id.in_(incident_ids))
            ),
        )
    )
    if (subsequent or 0) > 0:
        raise MergeReversalConflictError("subsequent_merge_events_exist")

    source_incident = db.scalar(
        select(Incident).where(Incident.id == locked_event.source_incident_id).with_for_update()
    ) if locked_event.source_incident_id else None
    target_incident = db.scalar(
        select(Incident).where(Incident.id == locked_event.target_incident_id).with_for_update()
    )
    if source_incident is None or target_incident is None:
        raise MergeReversalConflictError("incident_missing")

    if source_incident.status != StatusEnum.MERGED:
        raise MergeReversalConflictError("source_incident_not_merged")
    if source_incident.merged_into_incident_id != target_incident.id:
        raise MergeReversalConflictError("source_not_merged_into_target")
    if target_incident.status.value != locked_event.target_incident_status_before:
        raise MergeReversalConflictError("target_status_changed")

    # Transferred reports must still belong to target.
    transferred_ids = list(locked_event.transferred_report_ids or [])
    if not transferred_ids:
        raise MergeReversalConflictError("missing_transferred_report_snapshot")
    for rid in transferred_ids:
        report = db.scalar(select(Report).where(Report.id == rid).with_for_update())
        if report is None:
            raise MergeReversalConflictError(f"transferred_report_missing:{rid}")
        if report.incident_id != target_incident.id:
            raise MergeReversalConflictError(f"transferred_report_moved:{rid}")

    # Target must not have new reports since merge.
    current_target_ids = set(_incident_report_ids(db, target_incident.id))
    expected_target_ids = set(locked_event.target_incident_report_ids_before or []) | set(transferred_ids)
    if current_target_ids != expected_target_ids:
        raise MergeReversalConflictError("target_incident_reports_changed")

    # Perform reversal.
    for rid in transferred_ids:
        report = db.get(Report, rid)
        if report is None:
            raise MergeReversalConflictError(f"transferred_report_missing:{rid}")
        report.incident_id = source_incident.id
        db.add(report)

    source_incident.status = StatusEnum.OPEN
    source_incident.merged_into_incident_id = None
    source_incident.updated_at = utc_now()
    target_incident.updated_at = utc_now()
    db.add(source_incident)
    db.add(target_incident)

    reversal_event = MergeEvent(
        source_incident_id=locked_event.source_incident_id,
        target_incident_id=locked_event.target_incident_id,
        report_id=locked_event.report_id,
        matched_report_id=locked_event.matched_report_id,
        action="MERGE_REVERSAL",
        actor=actor_username,
        transferred_report_ids=transferred_ids,
        target_incident_report_ids_before=list(locked_event.target_incident_report_ids_before or []),
        source_incident_status_before=locked_event.source_incident_status_before,
        target_incident_status_before=locked_event.target_incident_status_before,
        sha256_match=locked_event.sha256_match,
        phash_hamming_distance=locked_event.phash_hamming_distance,
        phash_similarity=locked_event.phash_similarity,
        text_similarity=locked_event.text_similarity,
        geo_distance_meters=locked_event.geo_distance_meters,
        category_match=locked_event.category_match,
        candidate_classification=locked_event.candidate_classification,
        heuristic_score=locked_event.heuristic_score,
        policy_snapshot=dict(locked_event.policy_snapshot or {}),
        reversal_merge_event_id=locked_event.id,
    )
    db.add(reversal_event)
    db.flush()

    locked_event.reversed_at = utc_now()
    locked_event.reversal_merge_event_id = reversal_event.id
    db.add(locked_event)

    # Update suggestion/execution state conservatively.
    suggestion = db.scalar(
        select(MatchSuggestion).where(
            MatchSuggestion.report_id == locked_event.report_id,
            MatchSuggestion.incident_id == locked_event.target_incident_id,
        )
    )
    if suggestion:
        suggestion.status = SuggestionStatusEnum.PENDING
        suggestion.reviewed_at = None
        db.add(suggestion)
    execution = db.scalar(
        select(MergeExecution).where(MergeExecution.idempotency_key == merge_idempotency_key(locked_event.report_id, locked_event.target_incident_id))
    )
    if execution:
        execution.status = MergeExecutionStatusEnum.FAILED
        execution.last_error = "reversed_by_admin"
        execution.completed_at = utc_now()
        db.add(execution)

    audit = AdminAuditLog(
        actor_type=ActorTypeEnum.ADMIN,
        admin_username=actor_username,
        system_actor=None,
        action="MERGE_REVERSAL",
        target_type="merge_event",
        target_id=locked_event.id,
        merge_event_id=reversal_event.id,
        metadata_json={
            "original_merge_event_id": locked_event.id,
            "reversal_merge_event_id": reversal_event.id,
            "source_incident_id": locked_event.source_incident_id,
            "target_incident_id": locked_event.target_incident_id,
            "transferred_report_ids": transferred_ids,
        },
    )
    db.add(audit)
    db.flush()
    return reversal_event
