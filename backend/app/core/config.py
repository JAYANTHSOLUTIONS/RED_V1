"""Centralized application configuration.

All configuration is loaded from environment variables (12-factor app
principle). Nothing here is ever hard-coded: not passwords, API keys, JWT
secrets, database credentials, or storage credentials.

Business modules must import `get_settings()` rather than reading
`os.environ` directly, so every setting has a single, validated source of
truth.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "Real-Estate Consultant API"
    APP_ENV: str = Field(default="local", pattern="^(local|staging|production)$")
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    # Required: no default, so the app fails fast at boot if unset.
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # --- Auth / JWT ---
    # Infrastructure only in this phase; not yet wired to any route.
    # Required: no default, so a missing secret fails fast at boot rather
    # than silently running with a weak/known key.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 20
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # --- CORS ---
    # No wildcard default: authenticated routes must never allow "*".
    # Store as comma-separated string (prevents JSON parsing by Pydantic Settings)
    CORS_ALLOWED_ORIGINS_STR: str = Field(default="", alias="CORS_ALLOWED_ORIGINS")

    # --- Storage ---
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    LOCAL_DOCUMENTS_DIR: str = "storage/documents"
    STORAGE_PROVIDER: str = "s3"
    STORAGE_BUCKET: str = ""
    STORAGE_REGION: str = ""
    STORAGE_ENDPOINT_URL: str = ""
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""

    # --- Uploads ---
    MAX_UPLOAD_SIZE_MB: int = 15
    MAX_DOCUMENT_SIZE_MB: int = 15

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "text"

    # --- SMTP / Email Notifications (Phase 12) ---
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@redconsultant.com"
    SMTP_USE_TLS: bool = True
    SMTP_TIMEOUT_SECONDS: int = 10

    @property
    def CORS_ALLOWED_ORIGINS(self) -> List[str]:
        """Parse CORS_ALLOWED_ORIGINS from comma-separated string."""
        if not self.CORS_ALLOWED_ORIGINS_STR:
            return []
        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS_STR.split(",")
            if origin.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance.

    Cached so environment parsing/validation happens once per process
    rather than on every request.
    """
    return Settings()
