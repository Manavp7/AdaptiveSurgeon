"""Application configuration.

All settings are environment-driven so the same code runs on SQLite (default,
offline) or PostgreSQL (set DATABASE_URL), with local object storage (default)
or an S3/MinIO-compatible backend later.

The platform MUST remain fully runnable offline with no external API dependency,
so every "enable real model" flag defaults to off and has a synthetic fallback.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo layout:  <root>/backend/app/config.py  ->  BACKEND_DIR = <root>/backend
BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ADAPTIVE_",
        env_file=".env",
        extra="ignore",
    )

    # --- Core ---
    app_name: str = "AdaptiveSurgeon"
    environment: str = "development"
    api_prefix: str = "/api"

    # --- Database ---
    # SQLite by default (no external services). Postgres-ready: set
    # ADAPTIVE_DATABASE_URL=postgresql+psycopg2://user:pass@host/db
    database_url: str = f"sqlite:///{DEFAULT_DATA_DIR / 'adaptivesurgeon.db'}"

    # --- Object storage ---
    # "local" filesystem adapter today; S3/MinIO-compatible interface later.
    storage_backend: str = "local"  # local | s3
    storage_dir: Path = DEFAULT_DATA_DIR / "storage"
    s3_endpoint_url: str | None = None
    s3_bucket: str = "adaptivesurgeon"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None

    # --- Auth (minimal RBAC) ---
    auth_secret: str = "dev-insecure-secret-change-me"
    token_ttl_seconds: int = 60 * 60 * 12  # 12h

    # --- AI providers (synthetic defaults; real models are opt-in) ---
    instrument_provider: str = "synthetic"  # synthetic | yolo
    anatomy_provider: str = "synthetic"     # synthetic | sam
    phase_provider: str = "heuristic"       # heuristic | model
    risk_provider: str = "rules"            # rules | model
    copilot_provider: str = "rules"         # rules | llm
    embedding_provider: str = "hashing"     # hashing | sentence_transformer

    # --- Video processing ---
    analysis_sample_fps: float = 5.0  # frames/sec sampled during analysis
    # Assumed scale: laparoscopic field of view ~7 cm wide -> ~9000 px/m.
    pixels_per_meter: float = 9000.0

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    def ensure_dirs(self) -> None:
        DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
