from typing import Any, Collection, Iterable
from uuid import UUID

import asyncpg
from argon2 import PasswordHasher
from functional.settings import test_settings
from redis.asyncio import Redis


async def delete_data(pg_client: asyncpg.Connection, table: str) -> None:
    query = f"""
    DELETE FROM {table};
    """
    await pg_client.execute(query)


async def create_data(
    pg_client: asyncpg.Connection,
    table: str,
    columns: Collection[str],
    data: Iterable[Any],
) -> None:
    column_names = ", ".join(columns)
    values_part = ", ".join(f"${i}" for i in range(1, len(columns) + 1))
    query = f"""
    INSERT INTO {table} ({column_names})
    VALUES ({values_part}) ON CONFLICT (id) DO NOTHING;
    """
    await pg_client.execute(query, *data)


def hash_password(password: str) -> str:
    hasher = PasswordHasher(
        time_cost=test_settings.hash_time_cost,
        memory_cost=test_settings.hash_memory_cost,
        parallelism=test_settings.hash_parallelism,
    )
    return hasher.hash(password)


async def get_2fa_code(redis_client: Redis, user_id: UUID) -> str | None:
    """Читает код напрямую из Redis.

    TwoFactorService пишет его в 2fa_code:{user_id} до отправки через СМС-провайдера."""
    return await redis_client.get(f"2fa_code:{user_id}")


async def get_phone_change_code(
    redis_client: Redis, user_id: UUID
) -> str | None:
    """Читает код смены телефона напрямую из Redis.

    PhoneChangeService хранит его хешем phone_change:{user_id}, поле sms_code."""
    return await redis_client.hget(f"phone_change:{user_id}", "sms_code")  # type: ignore[misc]
