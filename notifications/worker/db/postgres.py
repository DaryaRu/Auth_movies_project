"""Подключение к PostgreSQL."""

import json

import asyncpg
from asyncpg import Connection, Pool
from core.settings import settings


async def _init_connection(conn: Connection) -> None:
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
        format="text",
    )


class PostgreSQL:
    """Класс для управления подключением к PostgreSQL."""

    pool: Pool | None = None

    @classmethod
    async def connect(cls) -> None:
        """Подключение к PostgreSQL с использованием пула соединений."""
        if cls.pool is None:
            cls.pool = await asyncpg.create_pool(
                dsn=settings.POSTGRES_DSN,
                min_size=2,
                max_size=10,
                command_timeout=60,
                init=_init_connection,
            )

    @classmethod
    async def disconnect(cls) -> None:
        """Отключение от PostgreSQL."""
        if cls.pool:
            await cls.pool.close()
            cls.pool = None
