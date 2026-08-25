"""Репозиторий для коротких ссылок."""

from datetime import datetime, timezone
from uuid import UUID

from asyncpg import Record

from src.db.postgres import PostgreSQL
from src.schemas.short_links import ShortLink


def _row_to_short_link(row: Record) -> ShortLink:
    """Преобразовать строку БД в модель ShortLink."""
    return ShortLink.model_validate(dict(row))


class ShortLinkRepository:
    """Репозиторий для работы с короткими ссылками."""

    async def create(
        self,
        short_key: str,
        user_id: UUID,
        expires_at: datetime,
        redirect_url: str,
    ) -> ShortLink:
        """Создать короткую ссылку."""
        query = """
            INSERT INTO short_links (short_key, user_id, expires_at, redirect_url)
            VALUES ($1, $2, $3, $4)
            RETURNING *
        """
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(query, short_key, user_id, expires_at, redirect_url)
        assert row is not None
        return _row_to_short_link(row)

    async def get_by_short_key(self, short_key: str) -> ShortLink | None:
        """Получить короткую ссылку по short_key."""
        query = "SELECT * FROM short_links WHERE short_key = $1"
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(query, short_key)
        return _row_to_short_link(row) if row else None

    async def consume_short_link(self, short_key: str) -> tuple[UUID, str] | None:
        """Атомарно отметить ссылку как использованную и вернуть данные.

        Возвращает (user_id, redirect_url), если ссылка валидна (не использована
        и не просрочена). В противном случае — None.
        """
        query = """
            UPDATE short_links
            SET is_used = TRUE
            WHERE short_key = $1
              AND NOT is_used
              AND expires_at > NOW()
            RETURNING user_id, redirect_url
        """
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(query, short_key)
        if row is None:
            return None
        return row["user_id"], row["redirect_url"]

    async def get_invalid_reason(self, short_key: str) -> str | None:
        """Определить причину невалидности ссылки (для логирования).

        Returns:
            "not_found" | "expired" | "already_used" | None (если валидна)
        """
        query = "SELECT is_used, expires_at FROM short_links WHERE short_key = $1"
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(query, short_key)
        if row is None:
            return "not_found"
        if row["is_used"]:
            return "already_used"
        if row["expires_at"] < datetime.now(timezone.utc):
            return "expired"
        return None