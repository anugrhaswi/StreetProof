from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import CSRF_COOKIE_NAME
from app.models import (
    AdminAuditLog,
    CategoryEnum,
    Incident,
    MatchingJob,
    MatchingJobStatusEnum,
    MatchSuggestion,
    MergeEvent,
    MergeExecution,
    MergeExecutionStatusEnum,
    Report,
    StatusEnum,
    SuggestionStatusEnum,
)


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(CSRF_COOKIE_NAME)
    return {"X-CSRF-Token": token} if token else {}


def _login(client: TestClient) -> None:
    res = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
    assert res.status_code == 200


def _seed(db: Session, upload_dir: Path) -> dict:
    now = datetime.now(timezone.utc)
    incident_a = Incident(
        title="Pothole A",
        description="Incident A",
        category=CategoryEnum.POTHOLE,
        latitude=1.0,
        longitude=2.0,
        status=StatusEnum.OPEN,
    )
    incident_b = Incident(
        title="Garbage B",
        description="Incident B",
        category=CategoryEnum.GARBAGE,
        latitude=3.0,
        longitude=4.0,
        status=StatusEnum.CLOSED,
    )
    db.add_all([incident_a, incident_b])
    db.flush()

    img_a = upload_dir / "a.jpg"
    img_a.write_bytes(b"fakejpg")
    img_b = upload_dir / "b.jpg"
    img_b.write_bytes(b"fakejpg2")

    report_a1 = Report(
        description="Big pothole on main street",
        category=CategoryEnum.POTHOLE,
        latitude=1.0,
        longitude=2.0,
        image_path="uploads/a.jpg",
        sha256_hash="a" * 64,
        phash="1111aaaa2222bbbb",
        phash_size=8,
        incident_id=incident_a.id,
        created_at=now - timedelta(days=1),
    )
    report_a2 = Report(
        description="Another pothole nearby",
        category=CategoryEnum.POTHOLE,
        latitude=1.01,
        longitude=2.01,
        image_path="uploads/a2.jpg",
        sha256_hash="b" * 64,
        phash="1111aaaa2222bbbc",
        phash_size=8,
        incident_id=incident_a.id,
        created_at=now - timedelta(days=2),
    )
    report_b1 = Report(
        description="Garbage pile at corner",
        category=CategoryEnum.GARBAGE,
        latitude=3.0,
        longitude=4.0,
        image_path="uploads/b.jpg",
        sha256_hash="c" * 64,
        phash="3333cccc4444dddd",
        phash_size=8,
        incident_id=incident_b.id,
        created_at=now - timedelta(days=3),
    )
    db.add_all([report_a1, report_a2, report_b1])
    db.flush()

    job_a1 = MatchingJob(report_id=report_a1.id, status=MatchingJobStatusEnum.COMPLETED)
    db.add(job_a1)
    db.add(
        MatchSuggestion(
            report_id=report_a1.id,
            incident_id=incident_b.id,
            matched_report_id=report_b1.id,
            similarity_score=0.75,
            status=SuggestionStatusEnum.PENDING,
        )
    )
    db.commit()
    return {
        "incident_a": incident_a.id,
        "incident_b": incident_b.id,
        "report_a1": report_a1.id,
        "report_a2": report_a2.id,
        "report_b1": report_b1.id,
    }


def test_admin_reports_requires_auth(client: TestClient):
    assert client.get("/api/admin/reports").status_code == 401
    assert client.get("/api/admin/reports/some-id").status_code == 401
    assert client.delete("/api/admin/reports/some-id", headers={"X-CSRF-Token": "x"}).status_code == 401


def test_admin_reports_list_pagination(client: TestClient, db_session: Session, upload_dir: Path):
    _seed(db_session, upload_dir)
    _login(client)
    res = client.get("/api/admin/reports", params={"page": 1, "page_size": 2})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert data["page_size"] == 2
    assert len(data["items"]) == 2
    assert data["total_pages"] == 2


def test_admin_reports_search_and_filters(client: TestClient, db_session: Session, upload_dir: Path):
    ids = _seed(db_session, upload_dir)
    _login(client)

    # search by description
    res = client.get("/api/admin/reports", params={"search": "Garbage"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == ids["report_b1"]

    # search by id prefix
    prefix = ids["report_a1"][:8]
    res = client.get("/api/admin/reports", params={"search": prefix})
    assert res.status_code == 200
    assert any(i["id"] == ids["report_a1"] for i in res.json()["items"])

    # category filter
    res = client.get("/api/admin/reports", params={"category": "pothole"})
    assert res.status_code == 200
    assert all(i["category"] == "pothole" for i in res.json()["items"])

    # incident status filter
    res = client.get("/api/admin/reports", params={"status": "closed"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == ids["report_b1"]


def test_admin_report_detail(client: TestClient, db_session: Session, upload_dir: Path):
    ids = _seed(db_session, upload_dir)
    _login(client)
    res = client.get(f"/api/admin/reports/{ids['report_a1']}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == ids["report_a1"]
    assert data["incident"]["id"] == ids["incident_a"]
    assert data["matching_job"]["status"] == "completed"
    assert len(data["match_suggestions"]) == 1


def test_delete_report_preserves_incident_and_other_reports(client: TestClient, db_session: Session, upload_dir: Path):
    ids = _seed(db_session, upload_dir)
    _login(client)

    res = client.delete(f"/api/admin/reports/{ids['report_a1']}", headers=_csrf_headers(client))
    assert res.status_code == 200
    data = res.json()
    assert data["deleted"] is True
    assert data["incident_deleted"] is False
    assert data["image_deleted"] is True

    # report_a1 gone, report_a2 remains, incident_a remains
    assert db_session.get(Report, ids["report_a1"]) is None
    assert db_session.get(Report, ids["report_a2"]) is not None
    assert db_session.get(Incident, ids["incident_a"]) is not None
    # matching job and suggestions for report_a1 gone
    jobs = db_session.scalar(select(func.count()).select_from(MatchingJob).where(MatchingJob.report_id == ids["report_a1"]))
    assert jobs == 0
    sugg = db_session.scalar(select(func.count()).select_from(MatchSuggestion).where(MatchSuggestion.report_id == ids["report_a1"]))
    assert sugg == 0
    # audit log created
    audit = db_session.scalar(select(AdminAuditLog).where(AdminAuditLog.target_id == ids["report_a1"]))
    assert audit is not None
    assert audit.action == "REPORT_DELETED"
    assert audit.admin_username == "admin"
    assert audit.metadata_json["incident_id"] == ids["incident_a"]
    # file deleted
    assert not (upload_dir / "a.jpg").exists()


def test_delete_last_report_deletes_incident(client: TestClient, db_session: Session, upload_dir: Path):
    ids = _seed(db_session, upload_dir)
    _login(client)

    res = client.delete(f"/api/admin/reports/{ids['report_b1']}", headers=_csrf_headers(client))
    assert res.status_code == 200
    assert res.json()["incident_deleted"] is True
    assert db_session.get(Incident, ids["incident_b"]) is None


def test_delete_report_missing_image_and_nonexistent(client: TestClient, db_session: Session, upload_dir: Path):
    ids = _seed(db_session, upload_dir)
    _login(client)

    # remove image file first
    (upload_dir / "a2.jpg").unlink(missing_ok=True)
    res = client.delete(f"/api/admin/reports/{ids['report_a2']}", headers=_csrf_headers(client))
    assert res.status_code == 200
    assert res.json()["image_deleted"] is False

    res = client.delete("/api/admin/reports/does-not-exist", headers=_csrf_headers(client))
    assert res.status_code == 404


def test_delete_last_report_preserves_merged_incident(client: TestClient, db_session: Session, upload_dir: Path):
    now = datetime.now(timezone.utc)
    incident = Incident(
        title="Merged Incident",
        description="Merged",
        category=CategoryEnum.OTHER,
        latitude=0.0,
        longitude=0.0,
        status=StatusEnum.MERGED,
    )
    db_session.add(incident)
    db_session.flush()
    img = upload_dir / "m.jpg"
    img.write_bytes(b"img")
    report = Report(
        description="Report in merged incident",
        category=CategoryEnum.OTHER,
        latitude=0.0,
        longitude=0.0,
        image_path="uploads/m.jpg",
        sha256_hash="d" * 64,
        phash="5555eeee6666ffff",
        phash_size=8,
        incident_id=incident.id,
        created_at=now,
    )
    db_session.add(report)
    db_session.commit()

    _login(client)
    res = client.delete(f"/api/admin/reports/{report.id}", headers=_csrf_headers(client))
    assert res.status_code == 200
    assert res.json()["incident_deleted"] is False
    assert db_session.get(Incident, incident.id) is not None


def test_delete_report_cascades_matched_report_suggestions(client: TestClient, db_session: Session, upload_dir: Path):
    ids = _seed(db_session, upload_dir)
    _login(client)
    # report_b1 is matched_report in suggestion from report_a1; deleting report_b1 should remove that suggestion
    res = client.delete(f"/api/admin/reports/{ids['report_b1']}", headers=_csrf_headers(client))
    assert res.status_code == 200
    sugg = db_session.scalar(select(func.count()).select_from(MatchSuggestion).where(MatchSuggestion.matched_report_id == ids["report_b1"]))
    assert sugg == 0


def _seed_merge_history(db: Session, *, source_report: Report, source_incident: Incident, target_report: Report, target_incident: Incident) -> MergeEvent:
    suggestion = db.scalar(
        select(MatchSuggestion).where(
            MatchSuggestion.report_id == source_report.id,
            MatchSuggestion.incident_id == target_incident.id,
        )
    )
    if suggestion is None:
        suggestion = MatchSuggestion(
            report_id=source_report.id,
            incident_id=target_incident.id,
            matched_report_id=target_report.id,
            similarity_score=0.95,
            status=SuggestionStatusEnum.AUTO_MERGED,
        )
        db.add(suggestion)
        db.flush()
    else:
        suggestion.status = SuggestionStatusEnum.AUTO_MERGED
        suggestion.matched_report_id = target_report.id
        db.add(suggestion)
        db.flush()
    event = MergeEvent(
        source_incident_id=source_incident.id,
        target_incident_id=target_incident.id,
        report_id=source_report.id,
        matched_report_id=target_report.id,
        action="AUTOMATIC_INCIDENT_MERGE",
        actor="system",
        transferred_report_ids=[source_report.id],
        target_incident_report_ids_before=[target_report.id],
        source_incident_status_before="open",
        target_incident_status_before="open",
        candidate_classification="AUTO_MERGE_CANDIDATE",
        heuristic_score=0.95,
        policy_snapshot={"test": True},
    )
    db.add(event)
    db.flush()
    execution = MergeExecution(
        match_suggestion_id=suggestion.id,
        merge_event_id=event.id,
        status=MergeExecutionStatusEnum.SUCCEEDED,
        attempt_count=1,
        idempotency_key=f"merge:{source_report.id}:{target_incident.id}",
    )
    db.add(execution)
    db.commit()
    db.refresh(event)
    return event


def test_delete_report_blocked_when_merge_event_references_report(client: TestClient, db_session: Session, upload_dir):
    ids = _seed(db_session, upload_dir)
    db_session.expire_all()
    source_report = db_session.get(Report, ids["report_a1"])
    source_incident = db_session.get(Incident, ids["incident_a"])
    target_report = db_session.get(Report, ids["report_b1"])
    target_incident = db_session.get(Incident, ids["incident_b"])
    assert source_report and source_incident and target_report and target_incident
    event = _seed_merge_history(
        db_session,
        source_report=source_report,
        source_incident=source_incident,
        target_report=target_report,
        target_incident=target_incident,
    )
    event_id = event.id
    execution_count_before = db_session.scalar(select(func.count()).select_from(MergeExecution)) or 0
    audit_count_before = db_session.scalar(select(func.count()).select_from(AdminAuditLog)) or 0

    _login(client)
    headers = {"X-CSRF-Token": client.cookies.get("streetproof_csrf_token", "")}
    res = client.delete(f"/api/admin/reports/{source_report.id}", headers=headers)
    assert res.status_code == 409
    assert "merge history" in res.json()["detail"].lower()

    db_session.expire_all()
    assert db_session.get(Report, source_report.id) is not None
    assert db_session.get(MergeEvent, event_id) is not None
    assert (db_session.scalar(select(func.count()).select_from(MergeExecution)) or 0) == execution_count_before
    assert (db_session.scalar(select(func.count()).select_from(AdminAuditLog)) or 0) == audit_count_before


def test_delete_last_report_preserves_merge_target_incident(client: TestClient, db_session: Session, upload_dir):
    ids = _seed(db_session, upload_dir)
    db_session.expire_all()
    source_report = db_session.get(Report, ids["report_a1"])
    source_incident = db_session.get(Incident, ids["incident_a"])
    target_report = db_session.get(Report, ids["report_b1"])
    target_incident = db_session.get(Incident, ids["incident_b"])
    assert source_report and source_incident and target_report and target_incident
    event = _seed_merge_history(
        db_session,
        source_report=source_report,
        source_incident=source_incident,
        target_report=target_report,
        target_incident=target_incident,
    )

    _login(client)
    headers = {"X-CSRF-Token": client.cookies.get("streetproof_csrf_token", "")}
    blocked = client.delete(f"/api/admin/reports/{target_report.id}", headers=headers)
    assert blocked.status_code == 409

    merge_target = Incident(
        title="Merge target",
        description="Target incident",
        category=CategoryEnum.SIGNAGE,
        latitude=3.0,
        longitude=3.0,
        status=StatusEnum.OPEN,
    )
    db_session.add(merge_target)
    db_session.flush()
    deletable = Report(
        description="Deletable report on merge target",
        category=CategoryEnum.SIGNAGE,
        latitude=3.0,
        longitude=3.0,
        image_path="uploads/deletable.jpg",
        sha256_hash="d" * 64,
        phash="3333444455556666",
        phash_size=8,
        incident_id=merge_target.id,
    )
    db_session.add(deletable)
    db_session.flush()
    hist_event = MergeEvent(
        source_incident_id=source_incident.id,
        target_incident_id=merge_target.id,
        report_id=source_report.id,
        matched_report_id=target_report.id,
        action="MANUAL_INCIDENT_MERGE",
        actor="admin",
        transferred_report_ids=[source_report.id],
        target_incident_report_ids_before=[deletable.id],
        source_incident_status_before="open",
        target_incident_status_before="open",
        candidate_classification="REVIEW_CANDIDATE",
        heuristic_score=0.8,
        policy_snapshot={"test": True},
    )
    db_session.add(hist_event)
    db_session.commit()

    deletable_id = deletable.id
    merge_target_id = merge_target.id
    hist_event_id = hist_event.id
    event_id = event.id
    res = client.delete(f"/api/admin/reports/{deletable_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["deleted"] is True
    assert data["incident_deleted"] is False

    db_session.expire_all()
    assert db_session.get(Report, deletable_id) is None
    assert db_session.get(Incident, merge_target_id) is not None
    assert db_session.get(MergeEvent, hist_event_id) is not None
    assert db_session.get(MergeEvent, event_id) is not None
