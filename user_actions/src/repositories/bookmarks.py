"""Репозиторий для закладок."""

from typing import Any
from uuid import UUID

from src.db.postgres import PostgreSQL
from src.repositories.base import BaseRepository


class BookmarkRepository(BaseRepository):
    """Репозиторий для работы с закладками."""

    table_name = "bookmarks"

    async def get_by_user_and_movie(
        self, user_id: UUID, movie_id: UUID
    ) -> dict[str, Any] | None:
        """Получить закладку по user_id и movie_id."""
        return await self.find_one({"user_id": user_id, "movie_id": movie_id})

    async def get_movie_bookmark_user_ids(self, movie_id: UUID) -> list[UUID]:
        """Получить id всех пользователей, добавивших movie_id в закладки."""
        query = f"SELECT user_id FROM {self.table_name} WHERE movie_id = $1"
        async with PostgreSQL.pool.acquire() as conn:
            rows = await conn.fetch(query, movie_id)
        return [row["user_id"] for row in rows]

    async def delete_by_user_and_movie(
        self, user_id: UUID, movie_id: UUID
    ) -> bool:
        """Удалить закладку по user_id и movie_id."""
        return await self.delete_by_filters(
            {"user_id": user_id, "movie_id": movie_id}
        )

    async def get_user_bookmarks(
        self, user_id: UUID, limit: int = 10, skip: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        """Получить все закладки пользователя."""
        return await self.find_by_user(user_id, limit=limit, skip=skip)
