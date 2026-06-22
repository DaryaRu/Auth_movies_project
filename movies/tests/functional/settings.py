"""Test settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    """Settings for tests."""

    model_config = SettingsConfigDict(env_file=".env")

    elastic_host: str = Field(alias="ELASTIC_HOST")
    elastic_port: int = Field(default=9200, alias="ELASTIC_PORT")
    elastic_movies_index: str = Field(
        default="movies", alias="ELASTIC_FILM_INDEX"
    )
    elastic_genres_index: str = Field(
        default="genres", alias="ELASTIC_GENRE_INDEX"
    )
    elastic_persons_index: str = Field(
        default="persons", alias="ELASTIC_PERSON_INDEX"
    )

    redis_host: str = Field(alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    api_url: str = Field(default="http://localhost:7000", alias="API_URL")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")

    service_wait_max_attempts: int = Field(
        default=30, alias="SERVICE_WAIT_MAX_ATTEMPTS"
    )
    service_wait_delay: float = Field(
        default=1.0, alias="SERVICE_WAIT_DELAY"
    )
    pagination_default_page_size: int = Field(
        alias="PAGINATION_DEFAULT_PAGE_SIZE"
    )
    pagination_max_page_size: int = Field(alias="PAGINATION_MAX_PAGE_SIZE")


test_settings = TestSettings()
