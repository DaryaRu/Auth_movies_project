"""Настройки функциональных тестов notifications-service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    """Настройки для функциональных тестов."""

    model_config = SettingsConfigDict(
        env_file=["/app/tests/functional/.env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="notifications", alias="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(
        default="postgres", alias="POSTGRES_PASSWORD"
    )

    api_url: str = Field(
        default="http://test-notifications-service:8000", alias="API_URL"
    )
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    service_wait_max_attempts: int = Field(
        default=30, alias="SERVICE_WAIT_MAX_ATTEMPTS"
    )
    service_wait_delay: float = Field(default=1.0, alias="SERVICE_WAIT_DELAY")


test_settings = TestSettings()
