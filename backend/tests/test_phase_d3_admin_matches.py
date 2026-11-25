"""Phase D3 admin match moderation tests."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import (
    Incident,
    MatchSuggestion,
    Report,
    StatusEnum,
    SuggestionStatusEnum,
    CategoryEnum,
)


def _create_report(db, *, incident: Incident, desc: str, category=CategoryEnum.POTHOLE, lat=1.0, lng=1.0):
    r = Report(
        description=desc,
        category=category,
        latitude=lat,
        longitude=lng,
        image_path="uploads/test.jpg",
        phash="0" * 16,
        phash_size=8,
        incident_id=incident.id,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def _create_incident(db, *, title="Inc", category=CategoryEnum.POTHOLE, lat=1.0, lng=1.0, status=StatusEnum.OPEN):
    inc = Incident(
        title=title,
        description="desc",
        category=category,
        latitude=lat,
        longitude=lng,
        status=status,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)
    return inc


def _create_suggestion(db, *, report: Report, incident: Incident, matched_report: Report, status=SuggestionStatusEnum.PENDING, classification="REVIEW_CANDIDATE"):
    s = MatchSuggestion(
        report_id=report.id,
        incident_id=incident.id,
        matched_report_id=matched_report.id,
        similarity_score=0.82,
        status=status,
        candidate_classification=classification,
        sha256_match=False,
        phash_hamming_distance=4,
        phash_similarity=0.75,
        text_similarity=0.8,
        geo_distance_meters=20.0,
        category_match=True,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _login(client):
    resp = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
    assert resp.status_code == 200
    csrf = client.cookies.get("streetproof_csrf_token")
    return {"X-CSRF-Token": csrf}


def test_list_matches_requires_admin(client):
    resp = client.get("/api/admin/matches")
    assert resp.status_code == 401


def test_list_matches_filters_and_pagination(client, db_session):
    inc_a = _create_incident(db_session, title="A")
    inc_b = _create_incident(db_session, title="B", lat=1.001, lng=1.001)
    r1 = _create_report(db_session, incident=inc_a, desc="pothole on main st 1")
    r2 = _create_report(db_session, incident=inc_b, desc="pothole on main st 2", lat=1.001, lng=1.001)
    s1 = _create_suggestion(db_session, report=r1, incident=inc_b, matched_report=r2, status=SuggestionStatusEnum.PENDING)
    _create_suggestion(db_session, report=r2, incident=inc_a, matched_report=r1, status=SuggestionStatusEnum.REJECTED)

    _login(client)
    resp = client.get("/api/admin/matches", params={"status": "pending", "page": 1, "page_size": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == s1.id
    assert data["items"][0]["report"]["id"] == r1.id
    assert data["items"][0]["matched_report"]["id"] == r2.id


def test_get_match_detail(client, db_session):
    inc_a = _create_incident(db_session, title="A")
    inc_b = _create_incident(db_session, title="B", lat=1.001, lng=1.001)
    r1 = _create_report(db_session, incident=inc_a, desc="pothole on main st 1")
    r2 = _create_report(db_session, incident=inc_b, desc="pothole on main st 2", lat=1.001, lng=1.001)
    s = _create_suggestion(db_session, report=r1, incident=inc_b, matched_report=r2)

    _login(client)
    resp = client.get(f"/api/admin/matches/{s.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == s.id
    assert body["text_similarity"] == 0.8
    assert body["geo_distance_meters"] == 20.0
    assert body["report"]["description"].startswith("pothole")


def test_reject_match(client, db_session):
    inc_a = _create_incident(db_session, title="A")
    inc_b = _create_incident(db_session, title="B", lat=1.001, lng=1.001)
    r1 = _create_report(db_session, incident=inc_a, desc="pothole on main st 1")
    r2 = _create_report(db_session, incident=inc_b, desc="pothole on main st 2", lat=1.001, lng=1.001)
    s = _create_suggestion(db_session, report=r1, incident=inc_b, matched_report=r2)

    headers = _login(client)
    resp = client.post(f"/api/admin/matches/{s.id}/reject", json={"reason": "not same issue"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    db_session.expire_all()
    updated = db_session.get(MatchSuggestion, s.id)
    assert updated.status == SuggestionStatusEnum.REJECTED
    assert updated.reviewed_at is not None


def test_reject_match_conflict_when_not_pending(client, db_session):
    inc_a = _create_incident(db_session, title="A")
    inc_b = _create_incident(db_session, title="B", lat=1.001, lng=1.001)
    r1 = _create_report(db_session, incident=inc_a, desc="pothole on main st 1")
    r2 = _create_report(db_session, incident=inc_b, desc="pothole on main st 2", lat=1.001, lng=1.001)
    s = _create_suggestion(db_session, report=r1, incident=inc_b, matched_report=r2, status=SuggestionStatusEnum.REJECTED)

    headers = _login(client)
    resp = client.post(f"/api/admin/matches/{s.id}/reject", json={}, headers=headers)
    assert resp.status_code == 409


def test_accept_match_success(client, db_session, monkeypatch):
    inc_a = _create_incident(db_session, title="A")
    inc_b = _create_incident(db_session, title="B", lat=1.001, lng=1.001)
    r1 = _create_report(db_session, incident=inc_a, desc="pothole on main st 1")
    r2 = _create_report(db_session, incident=inc_b, desc="pothole on main st 2", lat=1.001, lng=1.001)
    s = _create_suggestion(db_session, report=r1, incident=inc_b, matched_report=r2)

    from app.services import incident_merge
    from app.models import MergeEvent

    def fake_execute(*args, **kwargs):
        s.status = SuggestionStatusEnum.AUTO_MERGED
        s.reviewed_at = datetime.now(timezone.utc)
        db_session.add(s)
        evt = MergeEvent(
            source_incident_id=inc_a.id,
            target_incident_id=inc_b.id,
            report_id=r1.id,
            matched_report_id=r2.id,
            action="MANUAL_INCIDENT_MERGE",
            actor="admin",
            transferred_report_ids=[r1.id],
            target_incident_report_ids_before=[r2.id],
            source_incident_status_before="open",
            target_incident_status_before="open",
            candidate_classification="REVIEW_CANDIDATE",
            heuristic_score=0.82,
            policy_snapshot={},
        )
        db_session.add(evt)
        db_session.flush()
        return evt

    monkeypatch.setattr("app.api.admin_matches.execute_auto_merge", fake_execute)
    monkeypatch.setattr("app.api.admin_matches._recompute_ranked_candidates", lambda db, report: [])

    headers = _login(client)
    resp = client.post(f"/api/admin/matches/{s.id}/accept", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "auto_merged"
    assert body["merge_event_id"]


def test_accept_match_conflict(client, db_session, monkeypatch):
    inc_a = _create_incident(db_session, title="A")
    inc_b = _create_incident(db_session, title="B", lat=1.001, lng=1.001)
    r1 = _create_report(db_session, incident=inc_a, desc="pothole on main st 1")
    r2 = _create_report(db_session, incident=inc_b, desc="pothole on main st 2", lat=1.001, lng=1.001)
    s = _create_suggestion(db_session, report=r1, incident=inc_b, matched_report=r2)

    from app.services.incident_merge import MergeConflictError

    def fake_execute(*args, **kwargs):
        raise MergeConflictError("target_not_open")

    monkeypatch.setattr("app.api.admin_matches.execute_auto_merge", fake_execute)
    monkeypatch.setattr("app.api.admin_matches._recompute_ranked_candidates", lambda db, report: [])

    headers = _login(client)
    resp = client.post(f"/api/admin/matches/{s.id}/accept", headers=headers)
    assert resp.status_code == 409
    assert "target_not_open" in resp.json()["detail"]
from app.models import SuggestionStatusEnum, CategoryEnum


def test_accept_match_admin_bypasses_text_threshold(client, db_session, monkeypatch):
    """Admin manual accept should bypass strict auto-merge thresholds like text support."""
    from app.models import Incident, Report, MatchSuggestion, StatusEnum
    from app.services.incident_merge import execute_auto_merge
    from app.services.matching_engine import MultisignalCandidate, CandidateClassification
    from app.config import settings

    # Setup: two incidents, low text similarity (0.6 < 0.85 threshold)
    inc_a = Incident(title="A", description="d", category=CategoryEnum.POTHOLE, latitude=1.0, longitude=1.0, status=StatusEnum.OPEN)
    inc_b = Incident(title="B", description="d", category=CategoryEnum.POTHOLE, latitude=1.001, longitude=1.001, status=StatusEnum.OPEN)
    db_session.add_all([inc_a, inc_b]); db_session.commit()
    r1 = Report(description="pothole here", category=CategoryEnum.POTHOLE, latitude=1.0, longitude=1.0, image_path="uploads/a.jpg", phash="0"*16, phash_size=8, incident_id=inc_a.id)
    r2 = Report(description="road damage", category=CategoryEnum.POTHOLE, latitude=1.001, longitude=1.001, image_path="uploads/b.jpg", phash="1"*16, phash_size=8, incident_id=inc_b.id)
    db_session.add_all([r1, r2]); db_session.commit()
    s = MatchSuggestion(report_id=r1.id, incident_id=inc_b.id, matched_report_id=r2.id, similarity_score=0.6, status=SuggestionStatusEnum.PENDING,
                        candidate_classification="REVIEW_CANDIDATE", text_similarity=0.6, geo_distance_meters=20.0, category_match=True,
                        phash_similarity=0.7, phash_hamming_distance=5, sha256_match=False)
    db_session.add(s); db_session.commit()

    # Recompute will return candidate with low text sim
    low_text_candidate = MultisignalCandidate(
        incident_id=inc_b.id, incident_title="B", incident_category="pothole", incident_status="open",
        incident_latitude=1.001, incident_longitude=1.001, matched_report_id=r2.id, matched_report_description="road damage",
        sha256_match=False, phash_hamming_distance=5, phash_similarity=0.7, text_similarity=0.6,
        geo_distance_meters=20.0, category_match=True, candidate_classification=CandidateClassification.REVIEW_CANDIDATE, heuristic_score=0.6,
    )
    monkeypatch.setattr("app.api.admin_matches._recompute_ranked_candidates", lambda db, report: [low_text_candidate])

    # Login and accept
    resp = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
    csrf = client.cookies.get("streetproof_csrf_token")
    resp = client.post(f"/api/admin/matches/{s.id}/accept", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "auto_merged"


def test_accept_match_admin_blocked_on_category_contradiction(client, db_session, monkeypatch):
    """Admin cannot override contradictory category evidence."""
    from app.models import Incident, Report, MatchSuggestion, StatusEnum
    from app.services.matching_engine import MultisignalCandidate, CandidateClassification

    inc_a = Incident(title="A", description="d", category=CategoryEnum.POTHOLE, latitude=1.0, longitude=1.0, status=StatusEnum.OPEN)
    inc_b = Incident(title="B", description="d", category=CategoryEnum.GARBAGE, latitude=1.001, longitude=1.001, status=StatusEnum.OPEN)
    db_session.add_all([inc_a, inc_b]); db_session.commit()
    r1 = Report(description="pothole", category=CategoryEnum.POTHOLE, latitude=1.0, longitude=1.0, image_path="uploads/a.jpg", phash="0"*16, phash_size=8, incident_id=inc_a.id)
    r2 = Report(description="garbage pile", category=CategoryEnum.GARBAGE, latitude=1.001, longitude=1.001, image_path="uploads/b.jpg", phash="1"*16, phash_size=8, incident_id=inc_b.id)
    db_session.add_all([r1, r2]); db_session.commit()
    s = MatchSuggestion(report_id=r1.id, incident_id=inc_b.id, matched_report_id=r2.id, similarity_score=0.5, status=SuggestionStatusEnum.PENDING,
                        candidate_classification="REVIEW_CANDIDATE", text_similarity=0.5, geo_distance_meters=20.0, category_match=False,
                        phash_similarity=0.5, phash_hamming_distance=8, sha256_match=False)
    db_session.add(s); db_session.commit()

    contradiction_candidate = MultisignalCandidate(
        incident_id=inc_b.id, incident_title="B", incident_category="garbage", incident_status="open",
        incident_latitude=1.001, incident_longitude=1.001, matched_report_id=r2.id, matched_report_description="garbage pile",
        sha256_match=False, phash_hamming_distance=8, phash_similarity=0.5, text_similarity=0.5,
        geo_distance_meters=20.0, category_match=False, candidate_classification=CandidateClassification.REVIEW_CANDIDATE, heuristic_score=0.5,
    )
    monkeypatch.setattr("app.api.admin_matches._recompute_ranked_candidates", lambda db, report: [contradiction_candidate])

    resp = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
    csrf = client.cookies.get("streetproof_csrf_token")
    resp = client.post(f"/api/admin/matches/{s.id}/accept", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 409
    assert "contradictory_category" in resp.text
