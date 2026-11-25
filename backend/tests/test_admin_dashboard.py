from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    CategoryEnum,
    Incident,
    MatchingJob,
    MatchingJobStatusEnum,
    MatchSuggestion,
    Report,
    StatusEnum,
    SuggestionStatusEnum,
)


def _login(client: TestClient) -> None:
    res = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
    assert res.status_code == 200


def _seed_data(db: Session) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    incident = Incident(
        title="Pothole at 1.0000, 2.0000",
        description="Incident description",
        category=CategoryEnum.POTHOLE,
        latitude=1.0,
        longitude=2.0,
        status=StatusEnum.OPEN,
    )
    db.add(incident)
    db.flush()

    report_recent = Report(
        description="Recent pothole report description",
        category=CategoryEnum.POTHOLE,
        latitude=1.0,
        longitude=2.0,
        image_path="uploads/recent.jpg",
        sha256_hash="e" * 64,
        phash="7777888899990000",
        phash_size=8,
        incident_id=incident.id,
        created_at=now - timedelta(days=1),
    )
    report_old = Report(
        description="Old pothole report description",
        category=CategoryEnum.POTHOLE,
        latitude=1.1,
        longitude=2.1,
        image_path="uploads/old.jpg",
        sha256_hash="f" * 64,
        phash="aaaabbbbccccdddd",
        phash_size=8,
        incident_id=incident.id,
        created_at=now - timedelta(days=10),
    )
    db.add_all([report_recent, report_old])
    db.flush()

    db.add_all(
        [
            MatchingJob(report_id=report_recent.id, status=MatchingJobStatusEnum.COMPLETED),
            MatchingJob(report_id=report_old.id, status=MatchingJobStatusEnum.FAILED),
        ]
    )
    db.add(
        MatchSuggestion(
            report_id=report_recent.id,
            incident_id=incident.id,
            matched_report_id=report_old.id,
            similarity_score=0.88,
            status=SuggestionStatusEnum.PENDING,
        )
    )
    db.commit()
    return {"recent_id": report_recent.id, "old_id": report_old.id, "incident_id": incident.id}


def test_dashboard_stats_requires_auth(client: TestClient):
    res = client.get("/api/admin/dashboard/stats")
    assert res.status_code == 401


def test_dashboard_recent_reports_requires_auth(client: TestClient):
    res = client.get("/api/admin/dashboard/recent-reports")
    assert res.status_code == 401


def test_dashboard_stats_match_database(client: TestClient, db_session: Session):
    _seed_data(db_session)
    _login(client)
    res = client.get("/api/admin/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_reports"] == 2
    assert data["total_incidents"] == 1
    assert data["pending_suggestions"] == 1
    assert data["completed_jobs"] == 1
    assert data["failed_jobs"] == 1
    assert data["reports_last_7_days"] == 1


def test_dashboard_recent_reports_order_and_limit(client: TestClient, db_session: Session):
    ids = _seed_data(db_session)
    _login(client)
    res = client.get("/api/admin/dashboard/recent-reports")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    assert items[0]["id"] == ids["recent_id"]
    assert items[1]["id"] == ids["old_id"]
    assert items[0]["incident_id"] == ids["incident_id"]
    assert items[0]["image_path"] == "uploads/recent.jpg"


def test_dashboard_empty_database(client: TestClient):
    _login(client)
    stats = client.get("/api/admin/dashboard/stats")
    assert stats.status_code == 200
    assert stats.json() == {
        "total_reports": 0,
        "total_incidents": 0,
        "pending_suggestions": 0,
        "completed_jobs": 0,
        "failed_jobs": 0,
        "reports_last_7_days": 0,
    }
    recent = client.get("/api/admin/dashboard/recent-reports")
    assert recent.status_code == 200
    assert recent.json() == []
