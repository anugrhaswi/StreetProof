import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend is on path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
os.environ.setdefault("EMBEDDING_CACHE_DIR", "./test_model_cache")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ.setdefault("ADMIN_SESSION_EXPIRE_MINUTES", "60")


def _make_deterministic_vec(seed_val: int) -> list[float]:
    # Simple deterministic 384-dim unit vector without numpy dependency in fixture
    import math
    v = [0.0] * 384
    for i in range(384):
        # deterministic pseudo-random based on seed and index
        x = math.sin(seed_val * 1000 + i * 0.7) + math.cos(seed_val * 0.3 + i * 1.1)
        v[i] = x
    norm = math.sqrt(sum(x * x for x in v))
    if norm == 0:
        v[0] = 1.0
        norm = 1.0
    return [x / norm for x in v]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@pytest.fixture(scope="function")
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        if os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def upload_dir(tmp_path):
    d = tmp_path / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture(scope="function")
def db_engine(temp_db_path):
    from app.database import Base
    import app.models  # noqa: F401

    from sqlalchemy import event

    engine = create_engine(
        f"sqlite:///{temp_db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, future=True)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def mock_embedding_service():
    mock_service = MagicMock()
    mock_service.is_ready.return_value = True
    mock_service.is_enabled.return_value = True
    mock_service.get_status.return_value = {
        "status": "ready",
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "error": None,
        "semantic_matching_enabled": True,
    }

    # Predefined vectors for semantic categories
    vec_pothole = _make_deterministic_vec(1)
    vec_streetlight = _make_deterministic_vec(2)
    vec_garbage = _make_deterministic_vec(3)

    def encode_side_effect(text: str):
        t = text.lower()
        if any(k in t for k in ["pothole", "hole", "road", "asphalt"]):
            return list(vec_pothole)
        if any(k in t for k in ["streetlight", "light", "lamp", "dark"]):
            return list(vec_streetlight)
        if any(k in t for k in ["garbage", "trash", "waste", "litter"]):
            return list(vec_garbage)
        return _make_deterministic_vec(abs(hash(t)) % 10000)

    mock_service.encode.side_effect = encode_side_effect
    mock_service.cosine_similarity.side_effect = _cosine
    return mock_service


@pytest.fixture(scope="function")
def app(db_engine, mock_embedding_service, upload_dir):
    from contextlib import asynccontextmanager

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
    from app.database import get_db
    import app.models  # noqa: F401

    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, future=True)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    @asynccontextmanager
    async def test_lifespan(_app: FastAPI):
        yield

    from app.config import settings as app_settings
    old_upload_dir = app_settings.upload_dir
    old_cors_origins = app_settings.cors_origins
    old_storage_backend = app_settings.storage_backend
    old_supabase_url = app_settings.supabase_url
    old_supabase_service_role_key = app_settings.supabase_service_role_key
    old_supabase_storage_bucket = app_settings.supabase_storage_bucket
    app_settings.upload_dir = str(upload_dir)
    app_settings.storage_backend = "local"
    app_settings.supabase_url = ""
    app_settings.supabase_service_role_key = ""
    app_settings.supabase_storage_bucket = "report-images"
    # Isolated test app keeps explicit local origins; production CORS validation
    # is covered by dedicated config tests.
    app_settings.cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

    test_app = FastAPI(title="Test StreetProof", lifespan=test_lifespan)
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.normalized_cors_origins(),
        allow_origin_regex=app_settings.cors_origin_regex(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    test_app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")
    test_app.dependency_overrides[get_db] = override_get_db
    test_app.include_router(health_router)
    test_app.include_router(reports_router)
    test_app.include_router(incidents_router)
    test_app.include_router(matching_router)
    test_app.include_router(admin_auth_router)
    test_app.include_router(admin_dashboard_router)
    test_app.include_router(admin_incidents_router)
    test_app.include_router(admin_matches_router)
    test_app.include_router(admin_reports_router)
    test_app.include_router(admin_merges_router)

    # Patch EmbeddingService.get_instance everywhere it's used
    patches = [
        patch("app.services.embeddings.EmbeddingService.get_instance", return_value=mock_embedding_service),
        patch("app.api.health.EmbeddingService.get_instance", return_value=mock_embedding_service),
        patch("app.services.matching_worker.EmbeddingService.get_instance", return_value=mock_embedding_service),
    ]
    started = [p.start() for p in patches]
    try:
        yield test_app
    finally:
        for p in patches:
            p.stop()
        app_settings.upload_dir = old_upload_dir
        app_settings.cors_origins = old_cors_origins
        app_settings.storage_backend = old_storage_backend
        app_settings.supabase_url = old_supabase_url
        app_settings.supabase_service_role_key = old_supabase_service_role_key
        app_settings.supabase_storage_bucket = old_supabase_storage_bucket


@pytest.fixture(scope="function")
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(autouse=True)
def reset_admin_auth_state():
    from app.auth.dependencies import login_rate_limiter
    import app.auth.router as auth_router

    login_rate_limiter.reset()
    auth_router._CONFIGURED_PASSWORD_HASH = None
    yield
    login_rate_limiter.reset()
    auth_router._CONFIGURED_PASSWORD_HASH = None