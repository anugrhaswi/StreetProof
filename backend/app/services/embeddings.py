"""Embedding service: singleton model loader with background warm-up and status tracking.

Model inference is CPU-bound; callers should run encode() via run_in_executor
when called from async contexts to avoid blocking the event loop.

When semantic matching is disabled, this service acts as a lightweight no-op:
no torch/sentence-transformers imports, no model load, no background thread.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    _instance: "EmbeddingService | None" = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._model: Any = None
        self._status: str = "not_loaded"
        self._error: str | None = None
        self._init_lock = threading.Lock()
        self._enabled: bool = settings.semantic_matching_is_enabled()

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def status(self) -> str:
        return self._status

    def is_enabled(self) -> bool:
        return bool(self._enabled)

    def get_status(self) -> dict[str, str | bool | None]:
        enabled = self.is_enabled()
        # Keep status explicit when semantic matching is disabled.
        status = "disabled" if not enabled else self._status
        return {
            "status": status,
            "model_name": settings.embedding_model_name,
            "error": self._error,
            "semantic_matching_enabled": enabled,
        }

    def is_ready(self) -> bool:
        return self.is_enabled() and self._status == "ready" and self._model is not None

    def initialize_background(self) -> None:
        """Start model initialization in a daemon thread when enabled.

        Disabled mode is a deliberate no-op: no imports, no model, no thread.
        """
        if not self.is_enabled():
            with self._init_lock:
                self._model = None
                self._status = "disabled"
                self._error = None
            logger.info("Semantic matching disabled; skipping embedding model initialization")
            return

        with self._init_lock:
            if self._status in ("loading", "ready"):
                return
            self._status = "loading"
            self._error = None

        thread = threading.Thread(target=self._initialize, daemon=True, name="embedding-init")
        thread.start()

    def _initialize(self) -> None:
        if not self.is_enabled():
            with self._init_lock:
                self._model = None
                self._status = "disabled"
                self._error = None
            return
        try:
            # Limit torch threads to reduce CPU contention on small instances.
            try:
                import torch

                torch.set_num_threads(1)
            except Exception:
                pass

            from pathlib import Path

            from sentence_transformers import SentenceTransformer

            cache_dir = Path(settings.embedding_cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)

            logger.info(
                "Loading embedding model %s (rev=%s)",
                settings.embedding_model_name,
                settings.embedding_model_revision,
            )
            model = SentenceTransformer(
                settings.embedding_model_name,
                revision=settings.embedding_model_revision,
                cache_folder=str(cache_dir),
            )
            # Warm-up encode to ensure model is fully loaded.
            model.encode("warmup", convert_to_numpy=True, show_progress_bar=False)

            with self._init_lock:
                self._model = model
                self._status = "ready"
                self._error = None
            logger.info("Embedding model ready")
        except Exception as exc:
            logger.exception("Embedding model initialization failed")
            with self._init_lock:
                self._model = None
                self._status = "failed"
                self._error = str(exc)[:500]

    def encode(self, text: str) -> list[float] | None:
        """Encode text into an embedding vector.

        Returns None when disabled/unavailable. Callers must handle None safely.
        """
        if not self.is_ready():
            return None
        try:
            # Normalize whitespace for stable embeddings.
            cleaned = " ".join(text.split())
            if not cleaned:
                return None
            vector = self._model.encode(cleaned, convert_to_numpy=True, show_progress_bar=False)
            return [float(x) for x in vector.tolist()]
        except Exception:
            logger.exception("Embedding encode failed")
            return None

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors. Returns 0.0 on invalid input."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for x, y in zip(a, b):
            dot += x * y
            norm_a += x * x
            norm_b += y * y
        if norm_a <= 0.0 or norm_b <= 0.0:
            return 0.0
        return dot / ((norm_a ** 0.5) * (norm_b ** 0.5))
