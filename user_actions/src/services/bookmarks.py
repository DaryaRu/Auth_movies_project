"""Сервис для закладок."""

from datetime import datetime
from typing import Any
from uuid import UUID

from src.repositories.bookmarks import BookmarkRepository


class BookmarkService:
    """Сервис для работы с закладками."""

    def __init__(self, repository: BookmarkRepository):
        """Инициализация сервиса закладок."""
        self.repo = repository

    async def create_bookmark(self, user_id: UUID, movie_id: UUID) -> dict[str, Any]:
        """Создать закладку."""
        existing = await self.repo.get_by_user_and_movie(user_id, movie_id)
        if existing:
            return existing

        data = {
            "user_id": user_id,
            "movie_id": movie_id,
        }
        doc_id = await self.repo.create(data)
        now = datetime.utcnow()
        return {
            "id": str(doc_id),
            "user_id": user_id,
            "movie_id": movie_id,
            "created_at": now,
        }

    async def get_bookmark(self, user_id: UUID, movie_id: UUID) -> dict[str, Any] | None:
        """Получить закладку."""
        return await self.repo.get_by_user_and_movie(user_id, movie_id)

    async def delete_bookmark(self, user_id: UUID, movie_id: UUID) -> bool:
        """Удалить закладку."""
        return await self.repo.delete_by_user_and_movie(user_id, movie_id)

    async def get_user_bookmarks(self, user_id: UUID) -> tuple[list[dict[str, Any]], int]:
        """Получить все закладки пользователя."""
        return await self.repo.get_user_bookmarks(user_id)
