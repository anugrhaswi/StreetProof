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
from app.api.admin_incidents import router as admin_incidents_router
from app.api.admin_matches import router as admin_matches_router
from app.api.admin_merges import router as admin_merges_router
from app.api.admin_reports import router as admin_reports_router
from app.config import Settings, settings, validate_runtime_settings
from app.services.embeddings import EmbeddingService
from app.services.matching_worker import MatchingWorker

matching_worker = MatchingWorker()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Validate runtime config before starting background services.
    validate_runtime_settings(settings)
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


def create_app(app_settings: Settings | None = None) -> FastAPI:
    resolved = app_settings or settings
    # Validate eagerly for explicit app creation; lifespan also validates for runtime starts.
    validate_runtime_settings(resolved)

    application = FastAPI(
        title=resolved.app_name,
        version="0.3.0",
        debug=resolved.debug,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.normalized_cors_origins(),
        allow_origin_regex=resolved.cors_origin_regex(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Ensure upload directory exists before mount (mount requires existing dir in some envs).
    Path(resolved.upload_dir).mkdir(parents=True, exist_ok=True)
    application.mount("/uploads", StaticFiles(directory=resolved.upload_dir), name="uploads")

    application.include_router(health_router)
    application.include_router(reports_router)
    application.include_router(incidents_router)
    application.include_router(matching_router)
    application.include_router(admin_auth_router)
    application.include_router(admin_dashboard_router)
    application.include_router(admin_incidents_router)
    application.include_router(admin_matches_router)
    application.include_router(admin_merges_router)
    application.include_router(admin_reports_router)
    return application


app = create_app()
