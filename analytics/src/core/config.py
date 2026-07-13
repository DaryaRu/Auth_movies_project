import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=f"{str(Path(__file__).resolve().parent.parent.parent) + os.sep}.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "analytics-service"
    API_V1_PREFIX: str = "/api/v1"
    OPENAPI_URL: str = "/api/analytics/openapi"
    OPENAPI_SCHEMA_URL: str = "/api/analytics/openapi.json"

    KAFKA_BROKERS: str
    KAFKA_TOPIC: str = "user-activity"

    REDIS_HOST: str
    REDIS_PORT: int
    PUBLIC_KEY_CACHE_TTL: int = 3600

    AUTH_API_PUBLIC_KEY_URL: str
    JWT_ALGORITHM: str

    ALLOWED_HOSTS: str = "*"
    ORIGINS: str = "*"

    OTEL_EXPORTER_OTLP_ENDPOINT: str
    OTEL_SERVICE_NAME: str
    ENVIRONMENT: str
    OTEL_PYTHON_FASTAPI_EXCLUDED_URLS: str = ""
    DEBUG: bool = False

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/2"


settings = Settings()
