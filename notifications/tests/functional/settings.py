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

    auth_api_url: str = Field(
        default="http://auth-service:8000/api/v1", alias="AUTH_API_URL"
    )

    auth_postgres_host: str = Field(
        default="auth-db", alias="AUTH_POSTGRES_HOST"
    )
    auth_postgres_port: int = Field(
        default=5432, alias="AUTH_POSTGRES_PORT"
    )
    auth_postgres_db: str = Field(
        default="auth_db", alias="AUTH_POSTGRES_DB"
    )
    auth_postgres_user: str = Field(
        default="postgres", alias="AUTH_POSTGRES_USER"
    )
    auth_postgres_password: str = Field(
        default="postgres", alias="AUTH_POSTGRES_PASSWORD"
    )

    hash_time_cost: int = Field(default=2, alias="HASH_TIME_COST")
    hash_memory_cost: int = Field(default=65536, alias="HASH_MEMORY_COST")
    hash_parallelism: int = Field(default=1, alias="HASH_PARALLELISM")

    internal_service_secret: str = Field(
        default="service-secret", alias="INTERNAL_SERVICE_SECRET"
    )

    kafka_brokers: str = Field(default="kafka:9092", alias="KAFKA_BROKERS")
    kafka_pending_topic: str = Field(
        default="notification-pending", alias="KAFKA_PENDING_TOPIC"
    )
    kafka_ready_topic: str = Field(
        default="notification-ready", alias="KAFKA_READY_TOPIC"
    )
    kafka_consumer_timeout_sec: float = Field(
        default=15.0, alias="KAFKA_CONSUMER_TIMEOUT_SEC"
    )

    service_wait_max_attempts: int = Field(
        default=30, alias="SERVICE_WAIT_MAX_ATTEMPTS"
    )
    service_wait_delay: float = Field(default=1.0, alias="SERVICE_WAIT_DELAY")


test_settings = TestSettings()
