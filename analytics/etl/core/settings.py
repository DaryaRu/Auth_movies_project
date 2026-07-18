import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=f"{str(Path(__file__).resolve().parent.parent.parent.parent) + os.sep}.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    KAFKA_BROKERS: str
    KAFKA_TOPIC: str = "user-activity"
    KAFKA_DLQ_TOPIC: str = "user-activity.dlq"
    CLICKHOUSE_URL: str
    CLICKHOUSE_USER: str
    CLICKHOUSE_PASSWORD: str
    CLICKHOUSE_DB: str
    ANALITYCS_ETL_BATCH_SIZE: int = 1000
    ANALITYCS_ETL_FLUSH_INTERVAL: int = 5
    ANALITYCS_ETL_MAX_BUFFER_SIZE: int = 100_000
    
    @property
    def kafka_brokers_list(self) -> list[str]:
        return self.KAFKA_BROKERS.split(",")

settings = Settings()
