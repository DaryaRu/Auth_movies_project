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

    @classmethod
    async def execute_query(
        cls,
        query: str,
        *args,
        fetch: bool = False,
        fetchone: bool = False,
    ) -> list[asyncpg.Record] | asyncpg.Record | None | int:
        """Выполнить SQL запрос."""
        assert cls.pool is not None
        async with cls.pool.acquire() as conn:
            if fetch:
                return await conn.fetch(query, *args)
            elif fetchone:
                return await conn.fetchrow(query, *args)
            else:
                result = await conn.execute(query, *args)
                # parse result string like "1" for affected rows
                return int(result.split()[-1]) if result else 0

    @classmethod
    async def execute_many(
        cls,
        query: str,
        args: list[tuple],
    ) -> None:
        """Выполнить SQL запрос с несколькими наборами аргументов."""
        assert cls.pool is not None
        async with cls.pool.acquire() as conn:
            await conn.executemany(query, args)
