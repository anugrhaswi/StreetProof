from __future__ import annotations

import json
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_SECRET_KEY = "change-me-in-production"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "changeme"
DEFAULT_DEV_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
DEFAULT_SQLITE_DATABASE_URL = "sqlite:///./data/streetproof.db"
DEV_LAN_CORS_REGEX = (
    r"http://(localhost|127\.0\.0\.1|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?"
)




def normalize_database_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return raw
    lower = raw.lower()
    if lower.startswith("postgres://"):
        return "postgresql+psycopg://" + raw[len("postgres://"):]
    if lower.startswith("postgresql+psycopg://"):
        return raw
    if lower.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw[len("postgresql://"):]
    return raw


def is_sqlite_database_url(url: str) -> bool:
    return (url or "").strip().lower().startswith("sqlite")


def is_postgresql_database_url(url: str) -> bool:
    lower = (url or "").strip().lower()
    return lower.startswith("postgresql://") or lower.startswith("postgresql+psycopg://") or lower.startswith("postgres://")
class Settings(BaseSettings):
    app_name: str = "StreetProof API"
    environment: Literal["development", "production", "test"] = "development"
    debug: bool = True
    cors_origins: list[str] | str = DEFAULT_DEV_CORS_ORIGINS.copy()
    database_url: str = DEFAULT_SQLITE_DATABASE_URL
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout_seconds: int = 30
    database_pool_recycle_seconds: int = 1800
    database_pool_pre_ping: bool = True
    upload_dir: str = "./uploads"

    # Phase 3: semantic matching / embeddings
    semantic_matching_enabled: bool | None = None
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_model_revision: str = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
    embedding_cache_dir: str = "./model_cache"
    matching_threshold: float = 0.30
    max_candidates: int = 10
    matching_worker_interval_seconds: int = 5
    matching_max_retries: int = 3

    # Phase D1: multisignal duplicate detection
    phash_hash_size: int = 8
    phash_similarity_threshold: float = 0.85
    phash_review_threshold: float = 0.65
    matching_radius_meters: int = 500
    auto_merge_radius_meters: int = 50
    text_similarity_threshold: float = 0.75
    auto_merge_text_threshold: float = 0.85

    # Phase D2: automatic merge (disabled by default)
    auto_merge_enabled: bool = False
    auto_merge_min_score_margin: float = 0.15
    auto_merge_require_geo: bool = True
    auto_merge_require_category: bool = True
    auto_merge_require_text_support: bool = True
    merge_max_retries: int = 3
    merge_retry_base_delay_seconds: int = 30
    merge_retry_max_delay_seconds: int = 300

    # Phase A: admin authentication
    secret_key: str = DEFAULT_SECRET_KEY
    admin_username: str = DEFAULT_ADMIN_USERNAME
    admin_password: str = DEFAULT_ADMIN_PASSWORD
    admin_session_expire_minutes: int = 60
    admin_login_rate_limit: int = 5  # attempts per window
    admin_login_rate_window_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("environment", mode="before")
    @classmethod
    def _normalize_environment(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_database_url(value)
        return value

    @field_validator("semantic_matching_enabled", mode="before")
    @classmethod
    def _normalize_semantic_matching_enabled(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            raw = value.strip().lower()
            if raw == "":
                return None
            if raw in {"1", "true", "yes", "on"}:
                return True
            if raw in {"0", "false", "no", "off"}:
                return False
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError("CORS_ORIGINS must be a JSON array or comma-separated list of origins.") from exc
                return parsed
            return [item.strip() for item in raw.split(",") if item.strip()]
        if isinstance(value, tuple):
            return list(value)
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_sqlite(self) -> bool:
        return is_sqlite_database_url(self.database_url)

    @property
    def is_postgresql(self) -> bool:
        return is_postgresql_database_url(self.database_url)

    def semantic_matching_is_enabled(self) -> bool:
        """Resolve effective semantic matching mode.

        - Explicit SEMANTIC_MATCHING_ENABLED wins.
        - Default: disabled in production, enabled in development/test.
        """
        if self.semantic_matching_enabled is not None:
            return bool(self.semantic_matching_enabled)
        return not self.is_production

    def normalized_cors_origins(self) -> list[str]:
        origins = self.cors_origins
        if isinstance(origins, str):
            origins = Settings._parse_cors_origins(origins)
        if not isinstance(origins, list):
            raise ValueError("CORS_ORIGINS must be a list of origin strings.")

        normalized: list[str] = []
        for origin in origins:
            if not isinstance(origin, str):
                raise ValueError("CORS_ORIGINS entries must be strings.")
            cleaned = origin.strip()
            if not cleaned:
                continue
            if cleaned.endswith("/") and cleaned != "*":
                cleaned = cleaned.rstrip("/")
            normalized.append(cleaned)
        return normalized

    def cors_origin_regex(self) -> str | None:
        # Keep local/LAN development convenience only in explicit development debug mode.
        if self.is_development and self.debug:
            return DEV_LAN_CORS_REGEX
        return None

    def cookie_secure(self) -> bool:
        # Production cookies must be Secure. Development/test keep HTTP local workflows working.
        return self.is_production

    def validate_runtime_settings(self) -> None:
        errors: list[str] = []
        origins = self._validate_cors_settings(errors)
        self._validate_database_settings(errors)
        self._validate_production_settings(errors, origins)
        if errors:
            raise RuntimeError("Invalid application configuration:\n- " + "\n- ".join(errors))

    def _validate_database_settings(self, errors: list[str]) -> None:
        url = (self.database_url or "").strip()
        if not url:
            errors.append("DATABASE_URL must be configured.")
            return
        if self.is_sqlite or self.is_postgresql:
            return
        errors.append(
            "DATABASE_URL must use a supported scheme (sqlite or postgresql). "
            "For Supabase/PostgreSQL use postgresql+psycopg://..."
        )

    def _validate_cors_settings(self, errors: list[str]) -> list[str]:
        try:
            origins = self.normalized_cors_origins()
        except ValueError as exc:
            errors.append(str(exc))
            return []

        if any(origin == "*" for origin in origins):
            errors.append(
                "CORS_ORIGINS must not include '*' when credentials are enabled; configure an explicit allowlist."
            )

        if self.is_production and not origins:
            errors.append("CORS_ORIGINS must be explicitly configured in production.")

        if self.is_production and self.cors_origin_regex() is not None:
            errors.append("CORS origin regex must be disabled in production.")

        return origins

    def _validate_production_settings(self, errors: list[str], _origins: list[str]) -> None:
        if not self.is_production:
            return

        if self.debug:
            errors.append("DEBUG must be false in production.")

        secret = (self.secret_key or "").strip()
        if not secret:
            errors.append("SECRET_KEY must be set in production.")
        elif secret == DEFAULT_SECRET_KEY:
            errors.append("SECRET_KEY must not use the default placeholder in production.")
        elif len(secret) < 32:
            errors.append("SECRET_KEY must be at least 32 characters in production.")

        username = (self.admin_username or "").strip()
        if not username:
            errors.append("ADMIN_USERNAME must be set in production.")
        elif username == DEFAULT_ADMIN_USERNAME:
            errors.append("ADMIN_USERNAME must not use the default value in production.")

        password = self.admin_password or ""
        if not password.strip():
            errors.append("ADMIN_PASSWORD must be set in production.")
        elif password == DEFAULT_ADMIN_PASSWORD:
            errors.append("ADMIN_PASSWORD must not use the default value in production.")
        elif len(password) < 12:
            errors.append("ADMIN_PASSWORD must be at least 12 characters in production.")


def validate_runtime_settings(settings_obj: Settings | None = None) -> Settings:
    resolved = settings_obj or settings
    resolved.validate_runtime_settings()
    return resolved


settings = Settings()
