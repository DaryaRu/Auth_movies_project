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

    PROJECT_NAME: str = "notification-service"
    API_V1_PREFIX: str = "/api/v1"
    OPENAPI_URL: str = "/api/notifications/openapi"
    OPENAPI_SCHEMA_URL: str = "/api/notifications/openapi.json"

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "notifications"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Kafka
    KAFKA_BROKERS: str = ""
    KAFKA_READY_TOPIC: str = "notification-ready"
    KAFKA_PENDING_TOPIC: str = "notification-pending"
    KAFKA_RETRY_INTERVAL_SEC: int = 5
    KAFKA_ACKS: str = "all"

    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    # Service-to-service
    INTERNAL_SERVICE_SECRET: str = ""

    @property
    def POSTGRES_DSN(self) -> str:
        """DSN для подключения к PostgreSQL (для asyncpg)."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
