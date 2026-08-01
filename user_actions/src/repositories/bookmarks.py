"""Репозиторий для закладок."""

from typing import Any
from uuid import UUID

from src.repositories.base import BaseRepository


class BookmarkRepository(BaseRepository):
    """Репозиторий для работы с закладками."""

    table_name = "bookmarks"

    async def get_by_user_and_movie(self, user_id: UUID, movie_id: UUID) -> dict[str, Any] | None:
        """Получить закладку по user_id и movie_id."""
        return await self.find_one({"user_id": user_id, "movie_id": movie_id})

    async def delete_by_user_and_movie(self, user_id: UUID, movie_id: UUID) -> bool:
        """Удалить закладку по user_id и movie_id."""
        return await self.delete_by_filters({"user_id": user_id, "movie_id": movie_id})

    async def get_user_bookmarks(self, user_id: UUID) -> list[dict[str, Any]]:
        """Получить все закладки пользователя."""
        return await self.find_by_user(user_id)
