"""Настройки приложения."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=f"{str(Path(__file__).resolve().parent.parent.parent) + os.sep}.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "user-actions-service"
    API_V1_PREFIX: str = "/api/v1"
    OPENAPI_URL: str = "/api/user-actions/openapi"
    OPENAPI_SCHEMA_URL: str = "/api/user-actions/openapi.json"

    # PostgreSQL настройки
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "user_actions"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Redis настройки
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # JWT настройки
    AUTH_API_PUBLIC_KEY_URL: str = ""
    JWT_ALGORITHM: str = "RS256"
    PUBLIC_KEY_CACHE_TTL: int = 3600

    # Rate limiting
    EVENTS_RATE_LIMIT: str = "100/minute"
    BOOKMARKS_RATE_LIMIT: str = "100/minute"
    LIKES_RATE_LIMIT: str = "100/minute"
    REVIEWS_RATE_LIMIT: str = "50/minute"

    # CORS
    ALLOWED_HOSTS: str = "*"
    ORIGINS: str = "*"

    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_SERVICE_NAME: str = "user_actions"
    ENVIRONMENT: str = "local"
    OTEL_PYTHON_FASTAPI_EXCLUDED_URLS: str = ""
    DEBUG: bool = False

    # Pagination
    PAGINATION_DEFAULT_PAGE_SIZE: int = 20
    PAGINATION_MAX_PAGE_SIZE: int = 100

    @property
    def POSTGRES_URL(self) -> str:
        """Возвращает URL подключения к PostgreSQL."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def POSTGRES_DSN(self) -> str:
        """Возвращает DSN для подключения к PostgreSQL (для asyncpg)."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def REDIS_URL(self) -> str:
        """Возвращает URL подключения к Redis."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()