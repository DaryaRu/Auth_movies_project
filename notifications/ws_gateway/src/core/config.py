"""Настройки ws-gateway."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки ws-gateway."""

    model_config = SettingsConfigDict(
        env_file=f"{str(Path(__file__).resolve().parent.parent.parent.parent) + os.sep}.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "ws-gateway"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # auth-service (для верификации JWT)
    AUTH_API_PUBLIC_KEY_URL: str = ""
    JWT_ALGORITHM: str = "RS256"

    # WS
    WS_PING_INTERVAL_SEC: int = 30
    WS_PING_TIMEOUT_SEC: int = 60
    WS_MAX_CONNECTIONS_PER_USER: int = 5

settings = Settings()