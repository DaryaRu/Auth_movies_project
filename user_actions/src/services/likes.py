"""Сервис для лайков."""

from datetime import datetime
from typing import Any
from uuid import UUID

from src.repositories.likes import LikeRepository


class LikeService:
    """Сервис для работы с лайками."""

    def __init__(self, repository: LikeRepository):
        """Инициализация сервиса лайков."""
        self.repo = repository

    async def create_or_update_like(
        self, user_id: UUID, movie_id: UUID, rating: int
    ) -> dict[str, Any]:
        """Создать или обновить оценку."""
        existing = await self.repo.get_by_user_and_movie(user_id, movie_id)
        now = datetime.utcnow()

        if existing:
            updated = await self.repo.update(
                existing["id"], {"rating": rating, "updated_at": now}
            )
            if updated:
                return dict(updated)
            return existing

        data = {
            "user_id": user_id,
            "movie_id": movie_id,
            "rating": rating,
            "created_at": now,
            "updated_at": now,
        }
        doc_id = await self.repo.create(data)
        return {
            "id": doc_id,  
            "user_id": user_id,
            "movie_id": movie_id,
            "rating": rating,
            "created_at": now,
            "updated_at": now,
        }

    async def get_like(self, user_id: UUID, movie_id: UUID) -> dict[str, Any] | None:
        """Получить оценку пользователя для фильма."""
        return await self.repo.get_by_user_and_movie(user_id, movie_id)

    async def delete_like(self, user_id: UUID, movie_id: UUID) -> bool:
        """Удалить оценку пользователя для фильма."""
        return await self.repo.delete_by_user_and_movie(user_id, movie_id)

    async def get_user_likes(self, user_id: UUID) -> list[dict[str, Any]]:
        """Получить все оценки пользователя."""
        return await self.repo.get_user_likes(user_id)

    async def get_movie_likes(self, movie_id: UUID) -> list[dict[str, Any]]:
        """Получить все оценки для фильма."""
        return await self.repo.get_movie_likes(movie_id)

    async def get_movie_stats(self, movie_id: UUID) -> dict[str, Any]:
        """Получить статистику оценок для фильма."""
        return await self.repo.get_movie_stats(movie_id)
