import math

from app.models import CategoryEnum, Incident, Report, StatusEnum


def _make_incident(db_session, *, title="Test", description="Desc", category=CategoryEnum.POTHOLE,
                   lat=26.7271, lng=88.3953, status=StatusEnum.OPEN, merged_into=None):
    inc = Incident(
        title=title,
        description=description,
        category=category,
        latitude=lat,
        longitude=lng,
        status=status,
        merged_into_incident_id=merged_into,
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)
    return inc


def _make_report(db_session, incident, *, description="A pothole report description here",
                 category=CategoryEnum.POTHOLE, lat=26.7271, lng=88.3953, image_path="uploads/test.jpg"):
    rep = Report(
        description=description,
        category=category,
        latitude=lat,
        longitude=lng,
        image_path=image_path,
        sha256_hash=None,
        phash="a" * 16,
        phash_size=8,
        incident_id=incident.id,
    )
    db_session.add(rep)
    db_session.commit()
    db_session.refresh(rep)
    return rep


def test_map_endpoint_returns_active_incidents_with_report_count(client, db_session):
    inc1 = _make_incident(db_session, title="Pothole A", category=CategoryEnum.POTHOLE)
    _make_report(db_session, inc1, description="Report one about pothole")
    _make_report(db_session, inc1, description="Report two about pothole")

    inc2 = _make_incident(db_session, title="Light B", category=CategoryEnum.STREETLIGHT, lat=26.73, lng=88.40)
    _make_report(db_session, inc2, description="Streetlight report here")

    resp = client.get("/api/incidents/map")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = {item["id"] for item in data}
    assert inc1.id in ids
    assert inc2.id in ids

    by_id = {item["id"]: item for item in data}
    assert by_id[inc1.id]["report_count"] == 2
    assert by_id[inc2.id]["report_count"] == 1
    assert by_id[inc1.id]["status"] == "open"
    assert by_id[inc1.id]["category"] == "pothole"
    assert "latitude" in by_id[inc1.id]
    assert "longitude" in by_id[inc1.id]


def test_map_endpoint_excludes_merged_incidents(client, db_session):
    target = _make_incident(db_session, title="Target", status=StatusEnum.OPEN)
    merged = _make_incident(db_session, title="Merged", status=StatusEnum.MERGED, merged_into=target.id)
    _make_report(db_session, target, description="Target report")
    _make_report(db_session, merged, description="Merged report")

    resp = client.get("/api/incidents/map")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert target.id in ids
    assert merged.id not in ids


def test_map_endpoint_excludes_invalid_coordinates(client, db_session):
    good = _make_incident(db_session, title="Good", lat=26.7, lng=88.4)
    bad_lat = _make_incident(db_session, title="BadLat", lat=999.0, lng=88.4)
    bad_lng = _make_incident(db_session, title="BadLng", lat=26.7, lng=-999.0)
    _make_report(db_session, good, description="Good report")
    _make_report(db_session, bad_lat, description="Bad lat report")
    _make_report(db_session, bad_lng, description="Bad lng report")

    resp = client.get("/api/incidents/map")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert good.id in ids
    assert bad_lat.id not in ids
    assert bad_lng.id not in ids


def test_map_endpoint_returns_empty_list_when_no_incidents(client):
    resp = client.get("/api/incidents/map")
    assert resp.status_code == 200
    assert resp.json() == []
