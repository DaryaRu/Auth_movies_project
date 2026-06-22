"""Test settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    """Settings for tests."""

    model_config = SettingsConfigDict(env_file=".env")
    redis_host: str = Field(alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="postgres", alias="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    
    hash_time_cost: int = Field(default=3, alias="HASH_TIME_COST")
    hash_memory_cost: int = Field(default=65536, alias="HASH_MEMORY_COST")
    hash_parallelism: int = Field(default=2, alias="HASH_PARALLELISM")

    api_url: str = Field(default="http://localhost:7000", alias="API_URL")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")

    service_wait_max_attempts: int = Field(
        default=30, alias="SERVICE_WAIT_MAX_ATTEMPTS"
    )
    service_wait_delay: float = Field(
        default=1.0, alias="SERVICE_WAIT_DELAY"
    )


test_settings = TestSettings()