from io import BytesIO

import httpx
from PIL import Image
from sqlalchemy import select

from app.models import MatchingJob, Report
from app.services import image_service
from app.services.image_service import read_image_bytes, save_image
from app.services.matching_worker import MatchingWorker
from app.services.storage import SupabaseStorageService


def _jpeg_bytes(color=(200, 30, 30)) -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class _FakeUploadFile:
    def __init__(self, content: bytes, filename="test.jpg", content_type="image/jpeg"):
        self._content = content
        self.filename = filename
        self.content_type = content_type

    async def read(self):
        return self._content


class _MockResponse:
    def __init__(self, status_code=200, content=b"", json_data=None):
        self.status_code = status_code
        self.content = content
        self._json = json_data

    def json(self):
        return self._json


class _MockHttpxClient:
    def __init__(self, *args, **kwargs):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, content=None, headers=None):
        self.calls.append(("POST", url, headers, content))
        return _MockResponse(200, json_data={"Key": "reports/test.jpg"})

    def get(self, url, headers=None):
        self.calls.append(("GET", url, headers, None))
        return _MockResponse(200, content=b"image-bytes")

    def delete(self, url, headers=None):
        self.calls.append(("DELETE", url, headers, None))
        return _MockResponse(200, json_data=[])


def _configure_supabase(monkeypatch):
    import app.config as config_mod

    monkeypatch.setattr(config_mod.settings, "storage_backend", "supabase")
    monkeypatch.setattr(config_mod.settings, "supabase_url", "https://example-project.supabase.co")
    monkeypatch.setattr(config_mod.settings, "supabase_service_role_key", "service-role-test-key")
    monkeypatch.setattr(config_mod.settings, "supabase_storage_bucket", "report-images")
    monkeypatch.setattr(config_mod.settings, "environment", "development")


async def _noop():
    return None


def test_supabase_upload_returns_public_url(monkeypatch):
    _configure_supabase(monkeypatch)
    calls = {}

    class CaptureClient(_MockHttpxClient):
        def post(self, url, content=None, headers=None):
            calls["url"] = url
            calls["headers"] = headers
            calls["content"] = content
            return _MockResponse(200, json_data={"Key": "reports/x.jpg"})

    monkeypatch.setattr(httpx, "Client", CaptureClient)
    svc = SupabaseStorageService()
    result = svc.upload_bytes(content=b"abc", filename="abc.jpg", content_type="image/jpeg")
    assert result.image_path.startswith(
        "https://example-project.supabase.co/storage/v1/object/public/report-images/reports/"
    )
    assert calls["headers"]["Authorization"] == "Bearer service-role-test-key"
    assert "apikey" in calls["headers"]


def test_supabase_upload_failure_does_not_break_report_creation(client, session_factory, monkeypatch):
    _configure_supabase(monkeypatch)

    class FailingClient(_MockHttpxClient):
        def post(self, url, content=None, headers=None):
            return _MockResponse(503, json_data={"error": "boom"})

    monkeypatch.setattr(httpx, "Client", FailingClient)

    content = _jpeg_bytes()
    res = client.post(
        "/api/reports",
        data={
            "description": "Large pothole near school gate needs repair",
            "category": "pothole",
            "latitude": "26.7271",
            "longitude": "88.3953",
        },
        files={"image": ("pothole.jpg", content, "image/jpeg")},
    )
    assert res.status_code == 503
    assert "Failed to store image" in res.json()["detail"]

    db = session_factory()
    try:
        assert db.scalar(select(Report).limit(1)) is None
        assert db.scalar(select(MatchingJob).limit(1)) is None
    finally:
        db.close()


def test_report_creation_persists_supabase_url(client, session_factory, monkeypatch):
    _configure_supabase(monkeypatch)

    class OkClient(_MockHttpxClient):
        def post(self, url, content=None, headers=None):
            return _MockResponse(200, json_data={"ok": True})

    monkeypatch.setattr(httpx, "Client", OkClient)

    content = _jpeg_bytes((10, 120, 10))
    res = client.post(
        "/api/reports",
        data={
            "description": "Broken streetlight making the road dark at night",
            "category": "streetlight",
            "latitude": "26.7271",
            "longitude": "88.3953",
        },
        files={"image": ("light.jpg", content, "image/jpeg")},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["image_path"].startswith(
        "https://example-project.supabase.co/storage/v1/object/public/report-images/reports/"
    )
    assert body["image_path"].endswith(".jpg")

    db = session_factory()
    try:
        report = db.get(Report, body["id"])
        assert report is not None
        assert report.image_path == body["image_path"]
    finally:
        db.close()


def test_local_storage_compatibility(monkeypatch, tmp_path):
    import app.config as config_mod

    monkeypatch.setattr(config_mod.settings, "storage_backend", "local")
    monkeypatch.setattr(config_mod.settings, "upload_dir", str(tmp_path / "uploads"))

    content = _jpeg_bytes((1, 2, 3))
    import asyncio

    image_path, sha256_hash, phash_hex, phash_size = asyncio.run(
        save_image(_FakeUploadFile(content, filename="local.jpg", content_type="image/jpeg"))
    )
    assert image_path.startswith("uploads/")
    assert len(sha256_hash) == 64
    assert phash_hex
    assert phash_size == 8
    assert read_image_bytes(image_path) == content


def test_read_image_bytes_from_supabase_url(monkeypatch):
    _configure_supabase(monkeypatch)

    class ReadClient(_MockHttpxClient):
        def get(self, url, headers=None):
            return _MockResponse(200, content=b"supabase-image-bytes")

    monkeypatch.setattr(httpx, "Client", ReadClient)
    url = "https://example-project.supabase.co/storage/v1/object/public/report-images/reports/a.jpg"
    assert read_image_bytes(url) == b"supabase-image-bytes"


def test_matching_worker_reads_supabase_image_bytes(monkeypatch, session_factory, db_session):
    _configure_supabase(monkeypatch)
    report = Report(
        description="Pothole near school gate",
        category="pothole",
        latitude=26.7271,
        longitude=88.3953,
        image_path="https://example-project.supabase.co/storage/v1/object/public/report-images/reports/a.jpg",
        sha256_hash=None,
        phash="0" * 16,
        phash_size=8,
        incident_id="incident-id",
    )
    # Build minimal incident/report through SQLAlchemy models directly by creating incident first.
    from app.models import CategoryEnum, Incident, StatusEnum

    incident = Incident(
        title="Pothole",
        description="desc",
        category=CategoryEnum.POTHOLE,
        latitude=26.7271,
        longitude=88.3953,
        status=StatusEnum.OPEN,
    )
    db_session.add(incident)
    db_session.flush()
    report.incident_id = incident.id
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)

    monkeypatch.setattr(image_service, "read_image_bytes", lambda path: _jpeg_bytes())
    worker = MatchingWorker()
    changed = worker._ensure_fingerprints(report)
    assert changed is True
    assert report.sha256_hash
