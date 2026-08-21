"""Настройки воркера уведомлений."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки воркера."""

    model_config = SettingsConfigDict(
        env_file=f"{str(Path(__file__).resolve().parent.parent.parent.parent) + os.sep}.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL (та же, что у notifications-service)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "notifications"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Kafka
    KAFKA_BROKERS: str = ""
    KAFKA_READY_TOPIC: str = "notification-ready"
    KAFKA_READY_BULK_TOPIC: str = "notification-ready-bulk"
    KAFKA_PENDING_TOPIC: str = "notification-pending"
    KAFKA_DLQ_TOPIC: str = "notification.dlq"
    KAFKA_WORKER_GROUP_ID: str = "notifications-worker"
    KAFKA_RETRY_BACKOFF_TIME: int = 5

    # auth-service (для получения email перед отправкой)
    AUTH_API_URL: str = "http://auth-service:8000/api/v1"

    # SMTP (Mailpit в dev)
    SMTP_HOST: str = "mailpit"
    SMTP_PORT: int = 1025
    EMAIL_FROM: str = "notifications@example.com"
    EMAIL_MAX_PER_SEC: float = 10

    @property
    def kafka_brokers_list(self) -> list[str]:
        """Список брокеров для faststream.KafkaBroker."""
        return self.KAFKA_BROKERS.split(",")

    @property
    def POSTGRES_DSN(self) -> str:
        """DSN для подключения к PostgreSQL (для asyncpg)."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
