"""Test settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    """Settings for tests."""

    model_config = SettingsConfigDict(
        env_file=["/app/tests/functional/.env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

    redis_host: str = Field(alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="postgres", alias="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", alias="POSTGRES_PASSWORD")

    api_url: str = Field(default="http://test-user-actions-service:6001", alias="API_URL")
    api_prefix: str = Field(default="/api/v1/user-actions", alias="API_PREFIX")
    environment: str = Field(default="test", alias="ENVIRONMENT")
    private_key_path: str = Field(alias="PRIVATE_KEY_PATH")

    service_wait_max_attempts: int = Field(
        default=30, alias="SERVICE_WAIT_MAX_ATTEMPTS"
    )
    service_wait_delay: float = Field(
        default=1.0, alias="SERVICE_WAIT_DELAY"
    )


test_settings = TestSettings()
