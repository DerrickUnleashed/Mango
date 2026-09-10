"""OrchardVision core configuration.

Settings are loaded from environment variables with a `.env` fallback.
See `.env.example` at the repository root for all available variables.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "OrchardVision API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    # Security
    secret_key: str = "dev-secret-key-change-me"  # noqa: S105
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Database
    database_url: str = "sqlite:///./data/orchardvision.db"

    # Storage
    upload_dir: Path = ROOT_DIR / "data" / "uploads"
    processed_dir: Path = ROOT_DIR / "data" / "processed"

    # Upload constraints
    max_upload_bytes: int = 2 * 1024 * 1024 * 1024  # 2 GB
    allowed_video_mime_types: list[str] = [
        "video/mp4",
        "video/quicktime",
        "video/x-msvideo",
        "video/webm",
        "video/mpeg",
    ]

    # Processing
    default_inference_mode: str = "mock"
    default_confidence_threshold: float = 0.35
    default_reid_threshold: float = 0.6
    default_memory_update_rate: float = 0.2
    auto_create_tables: bool = True

    # Job queue (leave CELERY_BROKER_URL unset for the in-process background path)
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    celery_task_always_eager: bool = False

    # CORS
    cors_allow_credentials: bool = True


settings = Settings()
