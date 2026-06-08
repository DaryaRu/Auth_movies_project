from typing import Any, Iterable

import asyncpg
from argon2 import PasswordHasher
from functional.settings import test_settings


async def delete_data(pg_client: asyncpg.Connection, table: str) -> None:
    query = f'''
    DELETE FROM {table};
    '''
    await pg_client.execute(query)
    
    
async def create_data(pg_client: asyncpg.Connection, table: str, columns: Iterable[str], data: Iterable[Any]) -> None:
    column_names = ', '.join(columns)
    values_part = ', '.join(f'${i}' for i in range(1, len(columns) + 1))
    query = f'''
    INSERT INTO {table} ({column_names})
    VALUES ({values_part}) ON CONFLICT (id) DO NOTHING;
    '''
    await pg_client.execute(query, *data)
    
    
def hash_password(password: str) -> str:
    hasher = PasswordHasher(
        time_cost=test_settings.hash_time_cost,
        memory_cost=test_settings.hash_memory_cost,
        parallelism=test_settings.hash_parallelism,
    )
    return hasher.hash(password)
