"""Репозиторий для настройки url редиректа."""

from src.db.postgres import PostgreSQL


class SettingsRepository:
    """Репозиторий для работы с настройками."""

    async def get(self, key: str) -> str | None:
        """Получить значение настройки по ключу."""
        query = "SELECT value FROM settings WHERE key = $1"
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(query, key)
        return row["value"] if row else None

    async def set(self, key: str, value: str) -> None:
        """Установить значение настройки."""
        query = """
            INSERT INTO settings (key, value)
            VALUES ($1, $2)
            ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()
        """
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            await conn.execute(query, key, value)