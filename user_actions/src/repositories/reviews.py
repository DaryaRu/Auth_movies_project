"""Репозиторий для рецензий."""

from typing import Any, Literal
from uuid import UUID

from src.db.postgres import PostgreSQL
from src.repositories.base import BaseRepository

ReviewSortField = Literal["created_at", "rating", "likes", "score"]
ReviewSortOrder = Literal["ASC", "DESC"]


class ReviewRepository(BaseRepository):
    """Репозиторий для работы с рецензиями."""

    table_name = "reviews"

    async def get_by_user_and_movie(self, user_id: UUID, movie_id: UUID) -> dict[str, Any] | None:
        """Получить рецензию по user_id и movie_id."""
        return await self.find_one({"user_id": user_id, "movie_id": movie_id})

    async def exists_by_id(self, review_id: UUID) -> bool:
        """Проверить существование рецензии по ID."""
        conn = await PostgreSQL.get_connection()
        try:
            row = await conn.fetchrow("SELECT 1 FROM reviews WHERE id = $1 LIMIT 1", review_id)
            return row is not None
        finally:
            await PostgreSQL.release_connection(conn)

    async def delete_by_user_and_movie(self, user_id: UUID, movie_id: UUID) -> bool:
        """Удалить рецензию по user_id и movie_id."""
        return await self.delete_by_filters({"user_id": user_id, "movie_id": movie_id})

    async def get_user_reviews(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 10,
        sort_by: ReviewSortField = "created_at",
        sort_order: ReviewSortOrder = "DESC",
    ) -> tuple[list[dict[str, Any]], int]:
        """Получить все рецензии пользователя с сортировкой."""
        return await self._get_reviews(
            filters={"user_id": user_id},
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def get_movie_reviews(
        self,
        movie_id: UUID,
        skip: int = 0,
        limit: int = 10,
        sort_by: ReviewSortField = "created_at",
        sort_order: ReviewSortOrder = "DESC",
    ) -> tuple[list[dict[str, Any]], int]:
        """Получить все рецензии для фильма с сортировкой."""
        return await self._get_reviews(
            filters={"movie_id": movie_id},
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def get_all_reviews(
        self,
        skip: int = 0,
        limit: int = 10,
        sort_by: ReviewSortField = "created_at",
        sort_order: ReviewSortOrder = "DESC",
    ) -> tuple[list[dict[str, Any]], int]:
        """Получить все рецензии с сортировкой (без фильтрации)."""
        return await self._get_reviews(
            filters=None,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def _build_order_clause(
        self,
        sort_by: ReviewSortField,
        sort_order: ReviewSortOrder
    ) -> str:
        """Построить ORDER BY clause."""
        if sort_by in ("likes", "score"):
            return f"""
                (SELECT COUNT(*) FROM review_likes rl 
                WHERE rl.review_id = {self.table_name}.id AND rl.is_like = true) {sort_order}
            """
        return f"{sort_by} {sort_order}"

    async def _get_reviews(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 10,
        sort_by: ReviewSortField = "created_at",
        sort_order: ReviewSortOrder = "DESC",
    ) -> tuple[list[dict[str, Any]], int]:
        """Получить рецензии с фильтрацией и сортировкой."""

        order_clause = self._build_order_clause(sort_by, sort_order)

        return await self._get_all(
            skip=skip,
            limit=limit,
            filters=filters,
            order_by=order_clause
        )

    async def get_movie_stats(self, movie_id: UUID) -> dict[str, Any]:
        """Получить статистику рецензий для фильма."""
        conn = await PostgreSQL.get_connection()
        try:
            row = await conn.fetchrow(
                """
                SELECT 
                    COALESCE(AVG(rating), 0) as avg_rating,
                    COUNT(*) as count
                FROM reviews
                WHERE movie_id = $1
                """,
                movie_id,
            )
            if row and row["count"] > 0:
                return {
                    "avg_rating": round(float(row["avg_rating"]), 2),
                    "count": row["count"],
                }
            return {"avg_rating": 0, "count": 0}
        finally:
            await PostgreSQL.release_connection(conn)