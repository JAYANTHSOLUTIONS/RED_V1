"""Centralized application configuration.

All configuration is loaded from environment variables (12-factor app
principle). Nothing here is ever hard-coded: not passwords, API keys, JWT
secrets, database credentials, or storage credentials.

Business modules must import `get_settings()` rather than reading
`os.environ` directly, so every setting has a single, validated source of
truth.
"""
from functools import lru_cache
from typing import List, Optional, Set

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_KEYS: Set[str] = {
    "test-only-secret-key-not-for-production-use",
    "secret",
    "changeme",
    "password",
    "admin",
    "123456",
    "secretkey",
    "jwtsecret",
    "development-secret-key",
    "test",
    "default",
}


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
    DB_POOL_TIMEOUT: int = 10
    DB_POOL_RECYCLE: int = 1800
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

    # --- Reliability & Resilience (Phase 15) ---
    EXTERNAL_REQUEST_TIMEOUT: int = 10
    IDEMPOTENCY_EXPIRE_HOURS: int = 24

    # --- Security & Abuse Prevention (Phase 16) ---
    RATE_LIMIT_LOGIN_ATTEMPTS: int = 10
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 60

    # --- Production Hardening & OpenAPI Docs (Phase 17) ---
    OPENAPI_DOCS_ENABLED: Optional[bool] = None

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.APP_ENV == "production":
            # 1. JWT Secret strength
            secret = (self.JWT_SECRET_KEY or "").strip()
            if not secret:
                raise ValueError("JWT_SECRET_KEY must not be empty in production")
            if secret.lower() in INSECURE_SECRET_KEYS:
                raise ValueError(
                    f"JWT_SECRET_KEY cannot use known default/insecure secret in production: '{secret}'"
                )
            if len(secret) < 32:
                raise ValueError(
                    f"JWT_SECRET_KEY must be at least 32 characters long in production (got {len(secret)})"
                )

            # 2. Debug mode must be disabled
            if self.DEBUG:
                raise ValueError("DEBUG mode must be False in production")

            # 3. CORS allowed origins must not contain wildcard '*'
            if "*" in self.CORS_ALLOWED_ORIGINS:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS must not contain wildcard '*' in production"
                )

            # 4. Storage configuration
            if self.STORAGE_BACKEND.lower() == "s3":
                if not self.STORAGE_BUCKET or not self.STORAGE_ACCESS_KEY or not self.STORAGE_SECRET_KEY:
                    raise ValueError(
                        "S3 storage backend requires STORAGE_BUCKET, STORAGE_ACCESS_KEY, and STORAGE_SECRET_KEY to be configured in production"
                    )

            # 5. SMTP configuration validation if enabled
            if self.SMTP_HOST:
                if not (1 <= self.SMTP_PORT <= 65535):
                    raise ValueError(f"Invalid SMTP_PORT: {self.SMTP_PORT}")
                if not self.SMTP_FROM or "@" not in self.SMTP_FROM:
                    raise ValueError(f"Invalid SMTP_FROM address: {self.SMTP_FROM}")

        return self

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
