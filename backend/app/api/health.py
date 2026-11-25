from fastapi import APIRouter

from app.config import settings
from app.services.embeddings import EmbeddingService

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "streetproof-api"}


@router.get("/ai")
async def health_ai() -> dict[str, str | bool | None]:
    service = EmbeddingService.get_instance()
    status = service.get_status()
    return {
        "status": status["status"],
        "model_name": status["model_name"] or settings.embedding_model_name,
        "error": status["error"],
        "semantic_matching_enabled": bool(status.get("semantic_matching_enabled", settings.semantic_matching_is_enabled())),
    }
