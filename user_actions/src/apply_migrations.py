#!/usr/bin/env python3
"""Скрипт для применения SQL миграций при старте приложения."""

import asyncio
import os
from pathlib import Path

import asyncpg


async def apply_migrations():
    """Применить все SQL миграции из папки migrations."""
    dsn = (
        f"postgresql://{os.environ['POSTGRES_USER']}:"
        f"{os.environ['POSTGRES_PASSWORD']}@"
        f"{os.environ['POSTGRES_HOST']}:"
        f"{os.environ['POSTGRES_PORT']}/"
        f"{os.environ['POSTGRES_DB']}"
    )
    
    conn = await asyncpg.connect(dsn)
    migrations_dir = Path('/app/migrations')
    
    for migration_file in sorted(migrations_dir.glob('*.sql')):
        with open(migration_file, 'r') as f:
            sql = f.read()
            await conn.execute(sql)
            print(f'Applied migration: {migration_file.name}')
    
    await conn.close()
    print('All migrations applied successfully')


if __name__ == '__main__':
    asyncio.run(apply_migrations())