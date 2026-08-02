"""Вспомогательные функции для функциональных тестов."""
from typing import Any, Collection, Iterable

import asyncpg


async def delete_data(pg_client: asyncpg.Connection, table: str) -> None:
    """Delete all data from table."""
    query = f'''
    DELETE FROM {table};
    '''
    await pg_client.execute(query)


async def create_data(
    pg_client: asyncpg.Connection,
    table: str,
    columns: Collection[str],
    data: Iterable[Any]
) -> None:
    """Insert data into table."""
    column_names = ', '.join(columns)
    values_part = ', '.join(f'${i}' for i in range(1, len(columns) + 1))
    query = f'''
    INSERT INTO {table} ({column_names})
    VALUES ({values_part}) ON CONFLICT (id) DO NOTHING;
    '''
    await pg_client.execute(query, *data)
