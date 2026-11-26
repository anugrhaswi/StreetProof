import builtins
import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.config import Settings, validate_runtime_settings
from app.database import get_db
from app.models import MatchingJob, MatchingJobStatusEnum, MatchSuggestion
from app.services.embeddings import EmbeddingService
from app.services.matching_worker import MatchingWorker


REAL_IMPORT = builtins.__import__


def _block_heavy_ai_imports(name, globals=None, locals=None, fromlist=(), level=0):
    if name == "torch" or name.startswith("torch.") or name == "sentence_transformers" or name.startswith("sentence_transformers."):
        raise ModuleNotFoundError(f"Blocked heavy AI import: {name}")
    return REAL_IMPORT(name, globals, locals, fromlist, level)


def _reset_embedding_singleton():
    EmbeddingService._instance = None


@pytest.fixture
def lightweight_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("SECRET_KEY", "a-very-strong-production-secret-key-123456")
    monkeypatch.setenv("ADMIN_USERNAME", "streetproof_admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "strong-password-123")
    monkeypatch.setenv("CORS_ORIGINS", '["https://example.com"]')
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'prod-light.db').as_posix()}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("EMBEDDING_CACHE_DIR", str(tmp_path / "model_cache"))
    monkeypatch.setenv("SEMANTIC_MATCHING_ENABLED", "false")
    monkeypatch.setenv("STORAGE_BACKEND", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example-project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-test-key")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "report-images")
    return Settings()


@pytest.fixture
def lightweight_client(db_engine, upload_dir, monkeypatch):
    monkeypatch.setenv("SEMANTIC_MATCHING_ENABLED", "false")
    # Patch global settings object used by app modules
    import app.config as config_mod
    old_enabled = config_mod.settings.semantic_matching_enabled
    old_upload = config_mod.settings.upload_dir
    config_mod.settings.semantic_matching_enabled = False
    config_mod.settings.upload_dir = str(upload_dir)
    _reset_embedding_singleton()

    from app.api.health import router as health_router
    from app.api.incidents import router as incidents_router
    from app.api.matching import router as matching_router
    from app.api.reports import router as reports_router
    from app.api.admin_dashboard import router as admin_dashboard_router
    from app.api.admin_incidents import router as admin_incidents_router
    from app.api.admin_matches import router as admin_matches_router
    from app.api.admin_merges import router as admin_merges_router
    from app.api.admin_reports import router as admin_reports_router
    from app.auth.router import router as admin_auth_router

    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, future=True)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def test_lifespan(_app: FastAPI):
        yield

    test_app = FastAPI(title="Test StreetProof Lightweight", lifespan=test_lifespan)
    test_app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    test_app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")
    test_app.dependency_overrides[get_db] = override_get_db
    for r in [health_router, reports_router, incidents_router, matching_router, admin_auth_router, admin_dashboard_router, admin_incidents_router, admin_matches_router, admin_reports_router, admin_merges_router]:
        test_app.include_router(r)

    with TestClient(test_app) as c:
        yield c, TestingSessionLocal

    config_mod.settings.semantic_matching_enabled = old_enabled
    config_mod.settings.upload_dir = old_upload
    _reset_embedding_singleton()


def _submit_report(client, description, category, lat, lng):
    from io import BytesIO
    from PIL import Image
    img = Image.new("RGB", (64, 64), color=(120, 20, 20))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return client.post(
        "/api/reports",
        data={"description": description, "category": category, "latitude": str(lat), "longitude": str(lng)},
        files={"image": ("test.jpg", buf.getvalue(), "image/jpeg")},
    )


def test_semantic_disabled_does_not_import_or_initialize_model(monkeypatch):
    import app.config as config_mod
    old_enabled = config_mod.settings.semantic_matching_enabled
    old_env = config_mod.settings.environment
    config_mod.settings.semantic_matching_enabled = False
    config_mod.settings.environment = "production"
    _reset_embedding_singleton()
    try:
        with patch("builtins.__import__", side_effect=_block_heavy_ai_imports):
            svc = EmbeddingService()  # direct instance avoids patched singleton in full suite
            svc.initialize_background()
            status = svc.get_status()
        assert status["semantic_matching_enabled"] is False
        assert status["status"] == "disabled"
        assert svc.is_ready() is False
        assert svc.encode("anything") is None
    finally:
        config_mod.settings.semantic_matching_enabled = old_enabled
        config_mod.settings.environment = old_env
        _reset_embedding_singleton()


def test_ai_health_reports_disabled(lightweight_client):
    client, _ = lightweight_client
    # Ensure real disabled service, not a mock leaked from another test
    _reset_embedding_singleton()
    svc = EmbeddingService()
    svc.initialize_background()
    with patch("app.api.health.EmbeddingService.get_instance", return_value=svc):
        resp = client.get("/api/health/ai")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "disabled"
    assert data["semantic_matching_enabled"] is False


def test_report_submission_works_without_semantic_ai(lightweight_client):
    client, SessionLocal = lightweight_client
    resp = _submit_report(client, "Large pothole causing traffic hazard", "pothole", 26.7271, 88.3953)
    assert resp.status_code == 201
    report_id = resp.json()["id"]
    db = SessionLocal()
    try:
        job = db.scalar(select(MatchingJob).where(MatchingJob.report_id == report_id))
        assert job is not None
        assert job.status == MatchingJobStatusEnum.PENDING
    finally:
        db.close()


def test_lightweight_matching_works_and_job_completes_without_embeddings(lightweight_client):
    client, SessionLocal = lightweight_client
    # Two same-category reports nearby with same image content produce strong lightweight signals
    from io import BytesIO
    from PIL import Image
    img = Image.new("RGB", (64, 64), color=(200, 30, 30))
    buf = BytesIO(); img.save(buf, format="JPEG"); content = buf.getvalue()

    r1 = client.post("/api/reports", data={"description": "Pothole near school gate needs fix", "category": "pothole", "latitude": "26.7271", "longitude": "88.3953"}, files={"image": ("a.jpg", content, "image/jpeg")})
    r2 = client.post("/api/reports", data={"description": "Road damage near school entrance", "category": "pothole", "latitude": "26.7272", "longitude": "88.3954"}, files={"image": ("b.jpg", content, "image/jpeg")})
    assert r1.status_code == 201 and r2.status_code == 201

    worker = MatchingWorker()
    with patch("app.services.matching_worker.SessionLocal", SessionLocal), patch("builtins.__import__", side_effect=_block_heavy_ai_imports):
        # process available jobs; lightweight mode should not block on embeddings
        for _ in range(5):
            worker._process_next_job()

    db = SessionLocal()
    try:
        jobs = list(db.scalars(select(MatchingJob)).all())
        assert len(jobs) == 2
        assert all(j.status == MatchingJobStatusEnum.COMPLETED for j in jobs)
        suggestions = list(db.scalars(select(MatchSuggestion)).all())
        assert len(suggestions) >= 1
        # No fabricated semantic score
        assert all(s.text_similarity is None for s in suggestions)
    finally:
        db.close()


def test_missing_ai_dependencies_do_not_crash_production_startup(lightweight_settings):
    import app.config as config_mod
    old_enabled = config_mod.settings.semantic_matching_enabled
    old_env = config_mod.settings.environment
    old_debug = config_mod.settings.debug
    config_mod.settings.semantic_matching_enabled = False
    config_mod.settings.environment = "production"
    config_mod.settings.debug = False
    _reset_embedding_singleton()
    try:
        with patch("builtins.__import__", side_effect=_block_heavy_ai_imports):
            validate_runtime_settings(lightweight_settings)
            svc = EmbeddingService()  # direct instance avoids patched singleton in full suite
            svc.initialize_background()
            status = svc.get_status()
            assert status["semantic_matching_enabled"] is False
            assert status["status"] == "disabled"
    finally:
        config_mod.settings.semantic_matching_enabled = old_enabled
        config_mod.settings.environment = old_env
        config_mod.settings.debug = old_debug
        _reset_embedding_singleton()


def test_existing_semantic_matching_still_works_when_enabled(client, session_factory, mock_embedding_service):
    """Preserve semantic path: when enabled and model ready, worker generates embeddings and text similarity."""
    import app.config as config_mod
    old = config_mod.settings.semantic_matching_enabled
    config_mod.settings.semantic_matching_enabled = True
    try:
        r1 = _submit_report(client, "Large pothole on main street causing damage", "pothole", 26.7271, 88.3953)
        r2 = _submit_report(client, "Big hole in road near main street", "pothole", 26.7272, 88.3954)
        assert r1.status_code == 201 and r2.status_code == 201

        worker = MatchingWorker()
        with patch("app.services.matching_worker.SessionLocal", session_factory):
            for _ in range(5):
                worker._process_next_job()

        db = session_factory()
        try:
            jobs = list(db.scalars(select(MatchingJob)).all())
            assert all(j.status == MatchingJobStatusEnum.COMPLETED for j in jobs)
            suggestions = list(db.scalars(select(MatchSuggestion)).all())
            assert len(suggestions) >= 1
            # Semantic-enabled path should compute text similarity with mock embeddings
            assert any(s.text_similarity is not None for s in suggestions)
        finally:
            db.close()
    finally:
        config_mod.settings.semantic_matching_enabled = old
