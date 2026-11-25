from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StreetProof API"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    database_url: str = "sqlite:///./data/streetproof.db"
    upload_dir: str = "./uploads"

    # Phase 3: semantic matching / embeddings
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
    secret_key: str = "change-me-in-production"
    admin_username: str = "admin"
    admin_password: str = "changeme"
    admin_session_expire_minutes: int = 60
    admin_login_rate_limit: int = 5  # attempts per window
    admin_login_rate_window_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
