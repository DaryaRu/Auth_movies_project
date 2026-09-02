import os
from functools import cached_property
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Настройки сервиса
    """

    model_config = SettingsConfigDict(
        env_file=f"{str(Path(__file__).resolve().parent.parent.parent) + os.sep}.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    JWT_ALGORITHM: str
    PRIVATE_KEY_PATH: str
    PUBLIC_KEY_PATH: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    ALLOWED_HOSTS: str
    ORIGINS: str
    PROJECT_NAME: str
    REDIS_HOST: str
    REDIS_PORT: int
    HASH_TIME_COST: int
    HASH_MEMORY_COST: int
    HASH_PARALLELISM: int
    API_V1_PREFIX: str = "/api/v1"
    OPENAPI_URL: str = "/api/auth/openapi"
    OPENAPI_SCHEMA_URL: str = "/api/auth/openapi.json"
    CACHE_EXPIRE: int = 600
    COOKIE_SECURE: bool = False
    OAUTH_REDIRECT_BASE_URL: str = "http://localhost"
    OAUTH_STATE_EXPIRE_SECONDS: int = 300
    CODE_2FA_EXPIRE_SECONDS: int = 300
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    OTEL_EXPORTER_OTLP_ENDPOINT: str
    DEBUG: bool = False
    OTEL_SERVICE_NAME: str
    ENVIRONMENT: str
    OTEL_PYTHON_FASTAPI_EXCLUDED_URLS: str
    SENTRY_DSN: str = ""
    YANDEX_CLIENT_ID: str = ""
    YANDEX_CLIENT_SECRET: str = ""
    DEFAULT_LIMIT_VALUE: int = 100
    VK_CLIENT_ID: str = ""
    VK_CLIENT_SECRET: str = ""
    SMSC_LOGIN: str = ""
    SMSC_PASSWORD: str = ""
    # Для реальной отправки: указать SMSC_LOGIN/SMSC_PASSWORD и выставить SMSC_TEST_MODE=False.
    SMSC_TEST_MODE: bool = True
    LIMIT_VALUE: str = "5/minute"
    NOTIFICATIONS_API_URL: str = ""
    NOTIFICATIONS_TEMPLATE_ID_CACHE_TTL: int = 3600
    SHORT_LINKS_API_URL: str = "http://localhost:8000"
    INTERNAL_SERVICE_SECRET: str = ""
    DEFAULT_REDIRECT_HOST: str = "localhost"
    ALLOWED_REDIRECT_HOSTS: str = ""

    @property
    def EMAIL_CONFIRMATION_URL(self) -> str:
        """URL endpoint подтверждения email (собственный endpoint auth-сервиса)."""
        return f"{self.OAUTH_REDIRECT_BASE_URL}{self.API_V1_PREFIX}/confirm-email/"

    @property
    def DB_URL(self):
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @cached_property
    def PRIVATE_KEY(self):
        return Path(self.PRIVATE_KEY_PATH).read_text()

    @cached_property
    def PUBLIC_KEY(self):
        return Path(self.PUBLIC_KEY_PATH).read_text()

    @property
    def REDIS_LIMITER_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


settings = Settings()
