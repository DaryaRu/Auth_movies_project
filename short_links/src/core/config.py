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

    PROJECT_NAME: str = "short-links-service"
    API_V1_PREFIX: str = "/api/v1"
    OPENAPI_URL: str = "/api/short-links/openapi"
    OPENAPI_SCHEMA_URL: str = "/api/short-links/openapi.json"

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "short_links"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # URL для публичного доступа (редирект)
    SHORT_LINK_BASE_URL: str = "http://localhost/c"

    # Срок действия ссылки по умолчанию (в часах)
    DEFAULT_LINK_TTL_HOURS: int = 24

    # URL auth-сервиса для подтверждения email
    AUTH_API_URL: str = "http://auth-service:8000/api/v1"

    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    @property
    def POSTGRES_DSN(self) -> str:
        """DSN для подключения к PostgreSQL (для asyncpg)."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()