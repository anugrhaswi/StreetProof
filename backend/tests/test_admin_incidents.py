from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Incident, StatusEnum


def _login(client: TestClient) -> dict[str, str]:
    res = client.post("/api/admin/login", json={"username": "admin", "password": "test-password-123"})
    assert res.status_code == 200
    return {"X-CSRF-Token": client.cookies.get("streetproof_csrf_token", "")}


def test_admin_incidents_list_detail_and_status_update(client: TestClient, db_session: Session):
    incident = Incident(
        title="Pothole at 40.7000, -74.0000",
        description="Test incident",
        category="pothole",
        latitude=40.7,
        longitude=-74.0,
        status=StatusEnum.OPEN,
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    headers = _login(client)

    res = client.get("/api/admin/incidents")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == incident.id
    assert data["items"][0]["report_count"] == 0
    assert data["items"][0]["status"] == "open"

    detail = client.get(f"/api/admin/incidents/{incident.id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "open"

    patch = client.patch(
        f"/api/admin/incidents/{incident.id}/status",
        json={"status": "closed"},
        headers=headers,
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "closed"

    reopen = client.patch(
        f"/api/admin/incidents/{incident.id}/status",
        json={"status": "open"},
        headers=headers,
    )
    assert reopen.status_code == 200
    assert reopen.json()["status"] == "open"

    bad = client.patch(
        f"/api/admin/incidents/{incident.id}/status",
        json={"status": "merged"},
        headers=headers,
    )
    assert bad.status_code == 409


def test_admin_incidents_require_auth(client: TestClient):
    res = client.get("/api/admin/incidents")
    assert res.status_code == 401
