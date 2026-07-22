"""Test settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    """Settings for tests."""

    model_config = SettingsConfigDict(
        env_file=[".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

    redis_host: str = Field(alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    api_url: str = Field(default="http://test-analytics-service:6000", alias="API_URL")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    environment: str = Field(default="test", alias="ENVIRONMENT")
    private_key_path: str = Field(alias="PRIVATE_KEY_PATH")
    kafka_buffer_size: int = Field(alias="KAFKA_BUFFER_SIZE")


    service_wait_max_attempts: int = Field(
        default=30, alias="SERVICE_WAIT_MAX_ATTEMPTS"
    )
    service_wait_delay: float = Field(
        default=1.0, alias="SERVICE_WAIT_DELAY"
    )


test_settings = TestSettings()
