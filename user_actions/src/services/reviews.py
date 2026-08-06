"""Сервис для рецензий."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.repositories.reviews import (
    ReviewRepository,
    ReviewSortField,
    ReviewSortOrder,
)


class ReviewService:
    """Сервис для работы с рецензиями."""

    def __init__(self, repository: ReviewRepository):
        """Инициализация сервиса рецензий."""
        self.repo = repository

    async def create_review(
        self, user_id: UUID, movie_id: UUID, text: str, rating: int
    ) -> dict[str, Any]:
        """Создать рецензию."""
        existing = await self.repo.get_by_user_and_movie(user_id, movie_id)
        if existing:
            raise ValueError("User already has a review for this movie")

        data = {
            "user_id": user_id,
            "movie_id": movie_id,
            "text": text,
            "rating": rating,
        }

        new_review = await self.repo.create(data, returning="*")
        return new_review

    async def update_review(
        self, user_id: UUID, movie_id: UUID, text: str | None = None, rating: int | None = None
    ) -> dict[str, Any] | None:
        """Обновить рецензию."""
        existing = await self.repo.get_by_user_and_movie(user_id, movie_id)
        if not existing:
            return None

        update_data: dict[str, Any] = {}
        if text is not None:
            update_data["text"] = text
        if rating is not None:
            update_data["rating"] = rating
        update_data["updated_at"] = datetime.now(timezone.utc)

        updated = await self.repo.update(existing["id"], update_data)
        return dict(updated) if updated else None

    async def get_review(self, user_id: UUID, movie_id: UUID) -> dict[str, Any] | None:
        """Получить рецензию."""
        return await self.repo.get_by_user_and_movie(user_id, movie_id)

    async def delete_review(self, user_id: UUID, movie_id: UUID) -> bool:
        """Удалить рецензию."""
        return await self.repo.delete_by_user_and_movie(user_id, movie_id)

    async def get_user_reviews(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        sort_by: ReviewSortField = "created_at",
        sort_order: ReviewSortOrder = "DESC",
    ) -> dict[str, Any]:
        """Получить все рецензии пользователя с сортировкой."""
        skip = (page - 1) * page_size
        items, total = await self.repo.get_user_reviews(
            user_id, skip=skip, limit=page_size, sort_by=sort_by, sort_order=sort_order
        )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_movie_reviews(
        self,
        movie_id: UUID,
        page: int = 1,
        page_size: int = 20,
        sort_by: ReviewSortField = "created_at",
        sort_order: ReviewSortOrder = "DESC",
    ) -> dict[str, Any]:
        """Получить все рецензии для фильма с сортировкой."""
        skip = (page - 1) * page_size
        items, total = await self.repo.get_movie_reviews(
            movie_id, skip=skip, limit=page_size, sort_by=sort_by, sort_order=sort_order
        )
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_movie_stats(self, movie_id: UUID) -> dict[str, Any]:
        """Получить статистику рецензий для фильма."""
        return await self.repo.get_movie_stats(movie_id)

    async def get_all_reviews(
        self,
        skip: int = 0,
        limit: int = 10,
        sort_by: ReviewSortField = "created_at",
        sort_order: ReviewSortOrder = "DESC",
    ) -> dict[str, Any]:
        """Получить все рецензии с сортировкой (без фильтрации)."""
        items, total = await self.repo.get_all_reviews(
            skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order
        )
        return {
            "items": items,
            "total": total,
            "page": 1,
            "page_size": limit,
        }
