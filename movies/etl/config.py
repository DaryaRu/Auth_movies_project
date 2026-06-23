"""Store and validate ETL application settings."""

from pathlib import Path

from load.es_schema import (
    GENRE_INDEX_SCHEMA,
    MOVIES_INDEX_SCHEMA,
    PERSON_INDEX_SCHEMA,
)
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings."""

    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    elastic_host: str = Field(alias="ELASTIC_HOST")
    elastic_port: int = Field(default=9200, alias="ELASTIC_PORT")
    elastic_movies_index: str = Field(
        default="movies", alias="ELASTIC_MOVIES_INDEX"
    )
    elastic_genres_index: str = Field(
        default="genres", alias="ELASTIC_GENRES_INDEX"
    )
    elastic_persons_index: str = Field(
        default="persons", alias="ELASTIC_PERSONS_INDEX"
    )
    state_file: Path = Field(default=Path("./state.json"), alias="STATE_FILE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    etl_chunk_size: int = Field(default=100, alias="ETL_CHUNK_SIZE")
    etl_poll_interval: int = Field(default=1, alias="ETL_POLL_INTERVAL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def postgres_dsn(self) -> str:
        """Build a PostgreSQL DSN from app settings."""
        return (
            f"dbname={self.postgres_db} "
            f"user={self.postgres_user} "
            f"password={self.postgres_password} "
            f"host={self.postgres_host} "
            f"port={self.postgres_port}"
        )

    @property
    def elastic_map(self) -> dict:
        return {
            self.elastic_movies_index: MOVIES_INDEX_SCHEMA,
            self.elastic_genres_index: GENRE_INDEX_SCHEMA,
            self.elastic_persons_index: PERSON_INDEX_SCHEMA,
        }
