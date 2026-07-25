"""Centralized runtime configuration for MT Oil API.

All values are read from environment variables so the application can be
configured for local development, CI/CD, and Cloud Run without code changes.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


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


def _split_cors(raw: Optional[str]) -> List[str]:
    """Parse CORS origins from a comma-separated env string."""
    if not raw:
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


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
        cors_origins=_split_cors(os.getenv("CORS_ORIGINS")),
        skip_data_load=os.getenv("SKIP_DATA_LOAD", "false").lower()
        in ("1", "true", "yes"),
    )


settings = load_settings()
