"""Сервис для лайков рецензий."""

from datetime import datetime
from typing import Any
from uuid import UUID

from src.repositories.review_likes import ReviewLikeRepository
from src.repositories.reviews import ReviewRepository


class ReviewLikeService:
    """Сервис для работы с лайками рецензий."""

    def __init__(
        self,
        repository: ReviewLikeRepository, 
        review_repository: ReviewRepository | None = None
    ):
        self.repo = repository
        self.review_repo = review_repository or ReviewRepository()

    async def create_or_update_review_like(
        self, user_id: UUID, review_id: UUID, is_like: bool
    ) -> dict[str, Any]:
        """Создать или обновить лайк рецензии."""

        if not await self.review_repo.exists_by_id(review_id):
            raise ValueError(f"Review {review_id} not found")

        existing = await self.repo.get_by_user_and_review(user_id, review_id)
        now = datetime.utcnow()

        if existing:
            updated = await self.repo.update(
                existing["id"], {"is_like": is_like, "updated_at": now}
            )
            if updated:
                return dict(updated)
            return existing

        data = {
            "user_id": user_id,
            "review_id": review_id,
            "is_like": is_like,
            "created_at": now,
            "updated_at": now,
        }
        doc_id = await self.repo.create(data)
        return {
            "id": str(doc_id),
            "user_id": user_id,
            "review_id": review_id,
            "is_like": is_like,
            "created_at": now,
            "updated_at": now,
        }

    async def get_review_like(self, user_id: UUID, review_id: UUID) -> dict[str, Any] | None:
        """Получить лайк пользователя для рецензии."""
        return await self.repo.get_by_user_and_review(user_id, review_id)

    async def delete_review_like(self, user_id: UUID, review_id: UUID) -> bool:
        """Удалить лайк пользователя для рецензии."""
        return await self.repo.delete_by_user_and_review(user_id, review_id)

    async def get_review_likes(self, review_id: UUID) -> list[dict[str, Any]]:
        """Получить все лайки для рецензии."""
        return await self.repo.get_review_likes(review_id)

    async def get_review_stats(self, review_id: UUID) -> dict[str, Any]:
        """Получить статистику лайков для рецензии."""
        return await self.repo.get_review_stats(review_id)

    async def get_reviews_stats(self, review_ids: list[UUID]) -> dict[UUID, dict[str, Any]]:
        """Получить статистику лайков для списка рецензий."""
        return await self.repo.get_reviews_stats(review_ids)
