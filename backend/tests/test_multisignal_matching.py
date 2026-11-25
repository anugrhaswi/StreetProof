from app.services.matching_engine import (
    CandidateClassification,
    classify_candidate,
    find_candidate_incidents_multisignal,
)


BASE_THRESHOLDS = dict(
    matching_radius_meters=500,
    auto_merge_radius_meters=50,
    phash_similarity_threshold=0.85,
    phash_review_threshold=0.65,
    text_similarity_threshold=0.75,
    auto_merge_text_threshold=0.85,
)


def test_auto_merge_candidate_strong_signals():
    c = classify_candidate(
        sha256_match=False,
        phash_sim=0.95,
        text_sim=0.90,
        geo_distance_m=20.0,
        category_match=True,
        has_target_coords=True,
        has_candidate_coords=True,
        **BASE_THRESHOLDS,
    )
    assert c == CandidateClassification.AUTO_MERGE_CANDIDATE


def test_auto_merge_candidate_identical_sha256_close_category_match():
    c = classify_candidate(
        sha256_match=True,
        phash_sim=1.0,
        text_sim=0.1,
        geo_distance_m=10.0,
        category_match=True,
        has_target_coords=True,
        has_candidate_coords=True,
        **BASE_THRESHOLDS,
    )
    assert c == CandidateClassification.AUTO_MERGE_CANDIDATE


def test_missing_coords_prevents_auto_merge():
    c = classify_candidate(
        sha256_match=True,
        phash_sim=1.0,
        text_sim=0.95,
        geo_distance_m=None,
        category_match=True,
        has_target_coords=False,
        has_candidate_coords=True,
        **BASE_THRESHOLDS,
    )
    assert c != CandidateClassification.AUTO_MERGE_CANDIDATE


def test_category_disagreement_prevents_auto_merge():
    c = classify_candidate(
        sha256_match=True,
        phash_sim=0.99,
        text_sim=0.99,
        geo_distance_m=10.0,
        category_match=False,
        has_target_coords=True,
        has_candidate_coords=True,
        **BASE_THRESHOLDS,
    )
    assert c != CandidateClassification.AUTO_MERGE_CANDIDATE


def test_review_candidate_moderate_phash():
    c = classify_candidate(
        sha256_match=False,
        phash_sim=0.70,
        text_sim=0.50,
        geo_distance_m=100.0,
        category_match=True,
        has_target_coords=True,
        has_candidate_coords=True,
        **BASE_THRESHOLDS,
    )
    assert c == CandidateClassification.REVIEW_CANDIDATE


def test_review_candidate_strong_text_weak_phash():
    c = classify_candidate(
        sha256_match=False,
        phash_sim=0.30,
        text_sim=0.90,
        geo_distance_m=100.0,
        category_match=True,
        has_target_coords=True,
        has_candidate_coords=True,
        **BASE_THRESHOLDS,
    )
    assert c == CandidateClassification.REVIEW_CANDIDATE


def test_no_match_outside_radius():
    c = classify_candidate(
        sha256_match=False,
        phash_sim=0.70,
        text_sim=0.80,
        geo_distance_m=800.0,
        category_match=True,
        has_target_coords=True,
        has_candidate_coords=True,
        **BASE_THRESHOLDS,
    )
    assert c == CandidateClassification.NO_MATCH


def test_find_candidates_groups_by_incident_and_picks_strongest():
    target_embedding = [1.0, 0.0, 0.0]
    candidates = [
        {
            "report_id": "r1",
            "incident_id": "i1",
            "report_description": "a",
            "embedding": [1.0, 0.0, 0.0],
            "sha256_hash": "aaa",
            "phash": "f" * 16,
            "category": "pothole",
            "latitude": 27.7,
            "longitude": 85.3,
            "incident_title": "I1",
            "incident_category": "pothole",
            "incident_status": "open",
            "incident_latitude": 27.7,
            "incident_longitude": 85.3,
        },
        {
            "report_id": "r2",
            "incident_id": "i1",  # same incident, weaker
            "report_description": "b",
            "embedding": [0.5, 0.5, 0.0],
            "sha256_hash": "bbb",
            "phash": "0" * 16,
            "category": "pothole",
            "latitude": 27.7001,
            "longitude": 85.3001,
            "incident_title": "I1",
            "incident_category": "pothole",
            "incident_status": "open",
            "incident_latitude": 27.7,
            "incident_longitude": 85.3,
        },
    ]
    results = find_candidate_incidents_multisignal(
        target_report_id="t1",
        target_incident_id="ti",
        target_embedding=target_embedding,
        target_sha256="aaa",
        target_phash="f" * 16,
        target_category="pothole",
        target_lat=27.7,
        target_lng=85.3,
        candidate_reports=candidates,
        max_candidates=10,
        **BASE_THRESHOLDS,
    )
    assert len(results) == 1
    assert results[0].incident_id == "i1"
    assert results[0].matched_report_id == "r1"


def test_radius_filter_excludes_far_candidate_with_coords():
    results = find_candidate_incidents_multisignal(
        target_report_id="t1",
        target_incident_id="ti",
        target_embedding=[1.0, 0.0],
        target_sha256="a",
        target_phash="f" * 16,
        target_category="pothole",
        target_lat=27.7,
        target_lng=85.3,
        candidate_reports=[
            {
                "report_id": "r1",
                "incident_id": "i1",
                "report_description": "far",
                "embedding": [1.0, 0.0],
                "sha256_hash": "b",
                "phash": "f" * 16,
                "category": "pothole",
                "latitude": 28.7,  # far away
                "longitude": 86.3,
                "incident_title": "I1",
                "incident_category": "pothole",
                "incident_status": "open",
                "incident_latitude": 28.7,
                "incident_longitude": 86.3,
            }
        ],
        max_candidates=10,
        **BASE_THRESHOLDS,
    )
    assert results == []
