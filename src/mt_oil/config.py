"""Centralized runtime configuration for MT Oil API.

All values are read from environment variables so the application can be
configured for local development, CI/CD, and Cloud Run without code changes.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


def configure_logging(level: Optional[str] = None) -> logging.Logger:
    """Configure structured logging for the application."""
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    """Runtime settings populated from environment variables."""

    environment: str
    gcp_project_id: str
    gcs_data_bucket: str
    bigquery_dataset: str
    model_path: str
    enable_local_data: bool
    frontend_url: str
    log_level: str
    port: int
    cors_origins: List[str]
    skip_data_load: bool


def _split_cors(raw: Optional[str], frontend_url: Optional[str]) -> List[str]:
    """Parse CORS origins from a comma-separated env string.

    Falls back to the configured FRONTEND_URL, and only uses a wildcard
    when neither value is provided. This keeps deployed CORS locked to the
    known static frontend origin while preserving simple local development.
    """
    origins: List[str] = []
    if raw:
        origins = [
            origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()
        ]
    elif frontend_url:
        origins = [frontend_url.strip().rstrip("/")]
    return origins if origins else ["*"]


def load_settings() -> Settings:
    """Load settings from environment variables."""
    # Optional .env file for local development; ignored in Cloud Run.
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if env_path.exists() and "PORT" not in os.environ:
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path)
        except ImportError:  # pragma: no cover
            pass

    return Settings(
        environment=os.getenv("ENVIRONMENT", "local"),
        gcp_project_id=os.getenv("GCP_PROJECT_ID", ""),
        gcs_data_bucket=os.getenv("GCS_DATA_BUCKET", ""),
        bigquery_dataset=os.getenv("BIGQUERY_DATASET", ""),
        model_path=os.getenv("MODEL_PATH", "rf_model.joblib"),
        enable_local_data=os.getenv("ENABLE_LOCAL_DATA", "true").lower()
        in ("1", "true", "yes"),
        frontend_url=os.getenv("FRONTEND_URL", "http://localhost:5173"),
        log_level=os.getenv("LOG_LEVEL", "info"),
        port=int(os.getenv("PORT", "8000")),
        cors_origins=_split_cors(os.getenv("CORS_ORIGINS"), os.getenv("FRONTEND_URL")),
        skip_data_load=os.getenv("SKIP_DATA_LOAD", "false").lower()
        in ("1", "true", "yes"),
    )


settings = load_settings()
logger = configure_logging(settings.log_level)
