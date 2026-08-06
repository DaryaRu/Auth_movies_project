"""Репозиторий для лайков."""

from typing import Any
from uuid import UUID

from src.db.postgres import PostgreSQL
from src.repositories.base import BaseRepository


class LikeRepository(BaseRepository):
    """Репозиторий для работы с лайками."""

    table_name = "likes"

    async def get_by_user_and_movie(self, user_id: UUID, movie_id: UUID) -> dict[str, Any] | None:
        """Получить оценку пользователя для фильма."""
        return await self.find_one({"user_id": user_id, "movie_id": movie_id})

    async def delete_by_user_and_movie(self, user_id: UUID, movie_id: UUID) -> bool:
        """Удалить оценку пользователя для фильма."""
        return await self.delete_by_filters({"user_id": user_id, "movie_id": movie_id})

    async def get_user_likes(
            self,
            user_id: UUID,
            limit: int = 10,
            skip: int = 0
        ) -> tuple[list[dict[str, Any]], int]:
        """Получить все оценки пользователя."""
        return await self.find_by_user(user_id, limit=limit, skip=skip)


    async def get_movie_likes(
            self,
            movie_id: UUID,
            limit: int = 10,
            skip: int = 0
        ) -> tuple[list[dict[str, Any]], int]:
        """Получить все оценки для фильма."""
        return await self.find_by_movie(movie_id, limit=limit, skip=skip)

    async def get_movie_stats(self, movie_id: UUID) -> dict[str, Any]:
        """Получить статистику оценок для фильма.
        
        Возвращает:
            - likes: количество лайков (оценка 10)
            - dislikes: количество дизлайков (оценка 0)
            - total: общее количество оценок
            - average_rating: средняя оценка
        """
        conn = await PostgreSQL.get_connection()
        try:
            # Count likes (rating = 10)
            likes_row = await conn.fetchrow(
                "SELECT COUNT(*) FROM likes WHERE movie_id = $1 AND rating = 10",
                movie_id,
            )
            # Count dislikes (rating = 0)
            dislikes_row = await conn.fetchrow(
                "SELECT COUNT(*) FROM likes WHERE movie_id = $1 AND rating = 0",
                movie_id,
            )
            # Count total and average rating
            stats_row = await conn.fetchrow(
                "SELECT COUNT(*) as total, COALESCE(AVG(rating), 0) as avg FROM likes WHERE movie_id = $1",
                movie_id,
            )
            likes = likes_row[0] if likes_row else 0
            dislikes = dislikes_row[0] if dislikes_row else 0
            total = stats_row[0] if stats_row else 0
            average_rating = float(stats_row[1]) if stats_row and stats_row[1] else 0.0
            return {
                "likes": likes,
                "dislikes": dislikes,
                "total": total,
                "average_rating": average_rating,
            }
        finally:
            await PostgreSQL.release_connection(conn)
