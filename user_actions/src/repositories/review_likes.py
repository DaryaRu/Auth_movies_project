"""Репозиторий для лайков рецензий."""

from typing import Any
from uuid import UUID

from src.db.postgres import PostgreSQL
from src.repositories.base import BaseRepository


class ReviewLikeRepository(BaseRepository):
    """Репозиторий для работы с лайками рецензий."""

    table_name = "review_likes"

    async def get_by_user_and_review(self, user_id: UUID, review_id: UUID) -> dict[str, Any] | None:
        """Получить лайк пользователя для рецензии."""
        return await self.find_one({"user_id": user_id, "review_id": review_id})

    async def delete_by_user_and_review(self, user_id: UUID, review_id: UUID) -> bool:
        """Удалить лайк пользователя для рецензии."""
        return await self.delete_by_filters({"user_id": user_id, "review_id": review_id})

    async def get_review_likes(self, review_id: UUID) -> list[dict[str, Any]]:
        """Получить все лайки для рецензии."""
        return await self.find_by_review(review_id)

    async def find_by_review(
        self,
        review_id: UUID,
    ) -> list[dict[str, Any]]:
        """Найти записи по review_id."""
        items, _ = await self._get_all(filters={"review_id": review_id})
        return items

    async def get_review_stats(self, review_id: UUID) -> dict[str, Any]:
        """Получить статистику лайков для рецензии.
        
        Возвращает:
            - likes: количество лайков (is_like = true)
            - dislikes: количество дизлайков (is_like = false)
            - total: общее количество голосов
            - score: разница между лайками и дизлайками
        """
        conn = await PostgreSQL.get_connection()
        try:
            # Count likes (is_like = true)
            likes_row = await conn.fetchrow(
                "SELECT COUNT(*) FROM review_likes WHERE review_id = $1 AND is_like = true",
                review_id,
            )
            # Count dislikes (is_like = false)
            dislikes_row = await conn.fetchrow(
                "SELECT COUNT(*) FROM review_likes WHERE review_id = $1 AND is_like = false",
                review_id,
            )
            # Count total
            total_row = await conn.fetchrow(
                "SELECT COUNT(*) FROM review_likes WHERE review_id = $1",
                review_id,
            )
            likes = likes_row[0] if likes_row else 0
            dislikes = dislikes_row[0] if dislikes_row else 0
            total = total_row[0] if total_row else 0
            return {
                "likes": likes,
                "dislikes": dislikes,
                "total": total,
                "score": likes - dislikes,
            }
        finally:
            await PostgreSQL.release_connection(conn)

    async def get_reviews_stats(self, review_ids: list[UUID]) -> dict[UUID, dict[str, Any]]:
        """Получить статистику лайков для списка рецензий.
        
        Возвращает словарь {review_id: stats}.
        """
        if not review_ids:
            return {}

        conn = await PostgreSQL.get_connection()
        try:
            rows = await conn.fetch("""
                SELECT 
                    review_id,
                    COUNT(*) FILTER (WHERE is_like = true) as likes,
                    COUNT(*) FILTER (WHERE is_like = false) as dislikes,
                    COUNT(*) as total
                FROM review_likes
                WHERE review_id = ANY($1)
                GROUP BY review_id
            """, review_ids)

            result = {}
            for row in rows:
                review_id = row["review_id"]
                likes = row["likes"] or 0
                dislikes = row["dislikes"] or 0
                total = row["total"] or 0
                result[review_id] = {
                    "likes": likes,
                    "dislikes": dislikes,
                    "total": total,
                    "score": likes - dislikes,
                }

            for review_id in review_ids:
                if review_id not in result:
                    result[review_id] = {"likes": 0, "dislikes": 0, "total": 0, "score": 0}

            return result
        finally:
            await PostgreSQL.release_connection(conn)
