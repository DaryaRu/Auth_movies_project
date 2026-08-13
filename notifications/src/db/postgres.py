"""Подключение к PostgreSQL."""

import asyncpg
from asyncpg import Pool

from src.core.config import settings


class PostgreSQL:
    """Класс для управления подключением к PostgreSQL."""

    pool: Pool | None = None

    @classmethod
    async def connect(cls) -> None:
        """Подключение к PostgreSQL с использованием пула соединений."""
        if cls.pool is None:
            cls.pool = await asyncpg.create_pool(
                dsn=settings.POSTGRES_DSN,
                min_size=5,
                max_size=20,
                command_timeout=60,
            )

    @classmethod
    async def disconnect(cls) -> None:
        """Отключение от PostgreSQL."""
        if cls.pool:
            await cls.pool.close()
            cls.pool = None
