"""Настройки шедулера уведомлений."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки шедулера."""

    model_config = SettingsConfigDict(
        env_file=f"{str(Path(__file__).resolve().parent.parent.parent.parent) + os.sep}.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL (как у notifications-service и notifications-worker)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "notifications"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Kafka
    KAFKA_BROKERS: str = ""
    KAFKA_PENDING_TOPIC: str = "notification-pending"
    KAFKA_ACKS: str = "all"
    KAFKA_RETRY_INTERVAL_SEC: int = 5

    # Как часто проверять notification_triggers и admin_mailings.
    POLL_INTERVAL_SEC: int = 30

    @property
    def POSTGRES_DSN(self) -> str:
        """DSN для подключения к PostgreSQL (для asyncpg)."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
