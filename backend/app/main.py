from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.incidents import router as incidents_router
from app.api.matching import router as matching_router
from app.api.reports import router as reports_router
from app.auth.router import router as admin_auth_router
from app.api.admin_dashboard import router as admin_dashboard_router
from app.api.admin_matches import router as admin_matches_router
from app.api.admin_merges import router as admin_merges_router
from app.api.admin_reports import router as admin_reports_router
from app.config import settings
from app.services.embeddings import EmbeddingService
from app.services.matching_worker import MatchingWorker

matching_worker = MatchingWorker()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Ensure runtime directories exist.
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path("./data").mkdir(parents=True, exist_ok=True)
    Path(settings.embedding_cache_dir).mkdir(parents=True, exist_ok=True)

    # Background model warm-up; API becomes available immediately.
    EmbeddingService.get_instance().initialize_background()
    await matching_worker.start()
    try:
        yield
    finally:
        await matching_worker.stop()


app = FastAPI(
    title=settings.app_name,
    version="0.3.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?" if settings.debug else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists before mount (mount requires existing dir in some envs).
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(health_router)
app.include_router(reports_router)
app.include_router(incidents_router)
app.include_router(matching_router)
app.include_router(admin_auth_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_matches_router)
app.include_router(admin_merges_router)
app.include_router(admin_reports_router)
