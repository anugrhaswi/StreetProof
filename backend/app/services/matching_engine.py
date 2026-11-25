"""Multisignal duplicate detection engine (Phase D1).

Detection/classification only. No automatic merging.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.services.embeddings import EmbeddingService
from app.services.geo import haversine_distance, valid_coords
from app.services.image_fingerprint import hamming_distance, phash_similarity


class CandidateClassification(str, Enum):
    AUTO_MERGE_CANDIDATE = "AUTO_MERGE_CANDIDATE"
    REVIEW_CANDIDATE = "REVIEW_CANDIDATE"
    NO_MATCH = "NO_MATCH"


@dataclass
class MultisignalCandidate:
    incident_id: str
    incident_title: str
    incident_category: str
    incident_status: str
    incident_latitude: float
    incident_longitude: float
    matched_report_id: str
    matched_report_description: str

    # Component evidence
    sha256_match: bool | None
    phash_hamming_distance: int | None
    phash_similarity: float | None
    text_similarity: float | None
    geo_distance_meters: float | None
    category_match: bool | None
    candidate_classification: CandidateClassification
    heuristic_score: float


# Backward-compatible alias for older tests/imports that may remain.
@dataclass
class CandidateResult:
    incident_id: str
    incident_title: str
    incident_category: str
    incident_status: str
    incident_latitude: float
    incident_longitude: float
    matched_report_id: str
    matched_report_description: str
    similarity_score: float


def _heuristic_score(
    *,
    sha256_match: bool | None,
    phash_sim: float | None,
    text_sim: float | None,
    geo_distance_m: float | None,
    category_match: bool | None,
    matching_radius_m: int,
) -> float:
    """Configurable heuristic ranking score in [0,1]. Not a probability."""
    score = 0.0
    # Exact image is strongest signal.
    if sha256_match is True:
        score += 0.45
    # Visual similarity.
    if phash_sim is not None:
        score += 0.25 * max(0.0, min(1.0, phash_sim))
    # Text similarity.
    if text_sim is not None:
        score += 0.20 * max(0.0, min(1.0, text_sim))
    # Category agreement.
    if category_match is True:
        score += 0.10
    # Proximity bonus (closer is better, within radius).
    if geo_distance_m is not None and matching_radius_m > 0:
        proximity = max(0.0, 1.0 - (geo_distance_m / float(matching_radius_m)))
        score += 0.10 * proximity
    return max(0.0, min(1.0, score))


def classify_candidate(
    *,
    sha256_match: bool | None,
    phash_sim: float | None,
    text_sim: float | None,
    geo_distance_m: float | None,
    category_match: bool | None,
    has_target_coords: bool,
    has_candidate_coords: bool,
    matching_radius_meters: int,
    auto_merge_radius_meters: int,
    phash_similarity_threshold: float,
    phash_review_threshold: float,
    text_similarity_threshold: float,
    auto_merge_text_threshold: float,
) -> CandidateClassification:
    """Classify a candidate based on multisignal evidence.

    Conservative by design: missing coordinates prevent auto-merge.
    Category disagreement prevents auto-merge.
    """
    coords_present = has_target_coords and has_candidate_coords
    geo_close_auto = coords_present and geo_distance_m is not None and geo_distance_m <= auto_merge_radius_meters
    geo_close_review = coords_present and geo_distance_m is not None and geo_distance_m <= matching_radius_meters

    # Category disagreement: never auto-merge. May still be review only in rare cases? Spec says
    # "A category disagreement must prevent automatic merging. Strong conflicting evidence may still be sent for human review."
    # We'll allow review only when visual evidence is very strong or sha256 matches and geo close enough for review.
    category_disagrees = category_match is False

    # AUTO_MERGE_CANDIDATE: very strong evidence, no contradiction.
    if coords_present and geo_close_auto and category_match is True:
        if sha256_match is True:
            return CandidateClassification.AUTO_MERGE_CANDIDATE
        if (
            phash_sim is not None
            and phash_sim >= phash_similarity_threshold
            and text_sim is not None
            and text_sim >= auto_merge_text_threshold
        ):
            return CandidateClassification.AUTO_MERGE_CANDIDATE

    # Missing coordinates prevent auto-merge, but may allow review.
    # REVIEW_CANDIDATE logic.
    strong_visual = phash_sim is not None and phash_sim >= phash_similarity_threshold
    moderate_visual = phash_sim is not None and phash_sim >= phash_review_threshold
    strong_text = text_sim is not None and text_sim >= text_similarity_threshold

    if category_disagrees:
        # Conflicting evidence: only escalate to review if extremely strong visual/identical image and within review radius.
        if (sha256_match is True or strong_visual) and geo_close_review:
            return CandidateClassification.REVIEW_CANDIDATE
        return CandidateClassification.NO_MATCH

    # Same photo but far apart - review, not auto.
    if sha256_match is True:
        if geo_close_review or not coords_present:
            return CandidateClassification.REVIEW_CANDIDATE
        # Even if far, identical image is suspicious; review if within general reason. We already checked radius.
        # Outside matching radius with coords: no match.
        return CandidateClassification.NO_MATCH

    if moderate_visual and (geo_close_review or not coords_present):
        # If coords missing, never auto-merge; review allowed when other evidence strong enough.
        if coords_present or strong_text or moderate_visual:
            return CandidateClassification.REVIEW_CANDIDATE

    if strong_text and (geo_close_review or not coords_present):
        # Weak/unavailable pHash but strong text+geo - review
        if phash_sim is None or phash_sim < phash_review_threshold:
            if coords_present or category_match is True:
                return CandidateClassification.REVIEW_CANDIDATE

    # If coords present but outside matching radius, no match.
    if coords_present and geo_distance_m is not None and geo_distance_m > matching_radius_meters:
        return CandidateClassification.NO_MATCH

    return CandidateClassification.NO_MATCH


def find_candidate_incidents_multisignal(
    *,
    target_report_id: str,
    target_incident_id: str,
    target_embedding: list[float] | None,
    target_sha256: str | None,
    target_phash: str | None,
    target_category: str | None,
    target_lat: float | None,
    target_lng: float | None,
    candidate_reports: list[dict],
    matching_radius_meters: int,
    auto_merge_radius_meters: int,
    phash_similarity_threshold: float,
    phash_review_threshold: float,
    text_similarity_threshold: float,
    auto_merge_text_threshold: float,
    max_candidates: int,
) -> list[MultisignalCandidate]:
    """Rank candidate incidents by multisignal evidence.

    candidate_reports items include: report_id, incident_id, report_description, embedding,
    sha256_hash, phash, category, latitude, longitude, incident_title, incident_category,
    incident_status, incident_latitude, incident_longitude.
    """
    if max_candidates <= 0:
        return []

    has_target_coords = valid_coords(target_lat, target_lng)
    best_by_incident: dict[str, MultisignalCandidate] = {}

    for cand in candidate_reports:
        report_id = cand.get("report_id")
        incident_id = cand.get("incident_id")
        if not report_id or not incident_id:
            continue
        if report_id == target_report_id or incident_id == target_incident_id:
            continue

        cand_lat = cand.get("latitude")
        cand_lng = cand.get("longitude")
        has_cand_coords = valid_coords(cand_lat, cand_lng)

        geo_distance_m: float | None = None
        if has_target_coords and has_cand_coords:
            geo_distance_m = haversine_distance(float(target_lat), float(target_lng), float(cand_lat), float(cand_lng))
            # Filter outside general matching radius when both have valid coords.
            if geo_distance_m > matching_radius_meters:
                # Exception: identical SHA-256 at distance is suspicious - but spec says filter outside general radius
                # when both reports have valid coordinates. Keep it simple: skip.
                # (sha256 identical but far apart - NO_MATCH by classification; filtering is fine)
                # We'll still allow if sha256 matches? Spec: "Filter candidates outside the general matching radius when both reports have valid coordinates."
                # That's clear - filter out.
                pass

        # Component scores
        cand_sha256 = cand.get("sha256_hash")
        sha256_match: bool | None = None
        if target_sha256 and cand_sha256:
            sha256_match = target_sha256 == cand_sha256

        cand_phash = cand.get("phash")
        phash_dist: int | None = None
        phash_sim: float | None = None
        if target_phash and cand_phash:
            phash_dist = hamming_distance(target_phash, cand_phash)
            phash_sim = phash_similarity(target_phash, cand_phash)

        text_sim: float | None = None
        cand_embedding = cand.get("embedding")
        if isinstance(target_embedding, list) and isinstance(cand_embedding, list):
            raw = EmbeddingService.cosine_similarity(target_embedding, cand_embedding)
            text_sim = max(0.0, min(1.0, float(raw)))

        cand_category = cand.get("category")
        category_match: bool | None = None
        if target_category and cand_category:
            category_match = str(target_category) == str(cand_category)

        classification = classify_candidate(
            sha256_match=sha256_match,
            phash_sim=phash_sim,
            text_sim=text_sim,
            geo_distance_m=geo_distance_m,
            category_match=category_match,
            has_target_coords=has_target_coords,
            has_candidate_coords=has_cand_coords,
            matching_radius_meters=matching_radius_meters,
            auto_merge_radius_meters=auto_merge_radius_meters,
            phash_similarity_threshold=phash_similarity_threshold,
            phash_review_threshold=phash_review_threshold,
            text_similarity_threshold=text_similarity_threshold,
            auto_merge_text_threshold=auto_merge_text_threshold,
        )

        if classification == CandidateClassification.NO_MATCH:
            continue

        # Apply geo radius filter when both coords valid (after classification, sha256-far is NO_MATCH anyway).
        if has_target_coords and has_cand_coords and geo_distance_m is not None and geo_distance_m > matching_radius_meters:
            continue

        heuristic = _heuristic_score(
            sha256_match=sha256_match,
            phash_sim=phash_sim,
            text_sim=text_sim,
            geo_distance_m=geo_distance_m,
            category_match=category_match,
            matching_radius_m=matching_radius_meters,
        )

        candidate = MultisignalCandidate(
            incident_id=incident_id,
            incident_title=str(cand.get("incident_title", "")),
            incident_category=str(cand.get("incident_category", "")),
            incident_status=str(cand.get("incident_status", "")),
            incident_latitude=float(cand.get("incident_latitude", 0.0)),
            incident_longitude=float(cand.get("incident_longitude", 0.0)),
            matched_report_id=report_id,
            matched_report_description=str(cand.get("report_description", "")),
            sha256_match=sha256_match,
            phash_hamming_distance=phash_dist,
            phash_similarity=phash_sim,
            text_similarity=text_sim,
            geo_distance_meters=geo_distance_m,
            category_match=category_match,
            candidate_classification=classification,
            heuristic_score=heuristic,
        )

        existing = best_by_incident.get(incident_id)
        if existing is None or candidate.heuristic_score > existing.heuristic_score:
            best_by_incident[incident_id] = candidate

    ranked = sorted(best_by_incident.values(), key=lambda r: r.heuristic_score, reverse=True)
    return ranked[:max_candidates]


def find_candidate_incidents(
    *,
    target_report_id: str,
    target_incident_id: str,
    target_embedding: list[float],
    candidate_reports: list[dict],
    threshold: float,
    max_candidates: int,
) -> list[CandidateResult]:
    """Backward-compatible semantic-only wrapper used by older code/tests."""
    if not target_embedding or max_candidates <= 0:
        return []
    best_by_incident: dict[str, CandidateResult] = {}
    for cand in candidate_reports:
        report_id = cand.get("report_id")
        incident_id = cand.get("incident_id")
        embedding = cand.get("embedding")
        if not report_id or not incident_id or not isinstance(embedding, list):
            continue
        if report_id == target_report_id or incident_id == target_incident_id:
            continue
        score = EmbeddingService.cosine_similarity(target_embedding, embedding)
        score = max(0.0, min(1.0, float(score)))
        if score < threshold:
            continue
        existing = best_by_incident.get(incident_id)
        if existing is None or score > existing.similarity_score:
            best_by_incident[incident_id] = CandidateResult(
                incident_id=incident_id,
                incident_title=str(cand.get("incident_title", "")),
                incident_category=str(cand.get("incident_category", "")),
                incident_status=str(cand.get("incident_status", "")),
                incident_latitude=float(cand.get("incident_latitude", 0.0)),
                incident_longitude=float(cand.get("incident_longitude", 0.0)),
                matched_report_id=report_id,
                matched_report_description=str(cand.get("report_description", "")),
                similarity_score=score,
            )
    ranked = sorted(best_by_incident.values(), key=lambda r: r.similarity_score, reverse=True)
    return ranked[:max_candidates]
