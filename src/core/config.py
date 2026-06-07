import os
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

    @property
    def DB_URL(self):
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def PRIVATE_KEY(self):
        with open(self.PRIVATE_KEY_PATH) as file:
            return file.read()

    @property
    def PUBLIC_KEY(self):
        with open(self.PUBLIC_KEY_PATH) as file:
            return file.read()


settings = Settings()
