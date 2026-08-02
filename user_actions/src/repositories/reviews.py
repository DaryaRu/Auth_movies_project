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

    async def _get_reviews(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 10,
        sort_by: ReviewSortField = "created_at",
        sort_order: ReviewSortOrder = "DESC",
    ) -> tuple[list[dict[str, Any]], int]:
        """Получить рецензии с фильтрацией и сортировкой.
        
        Args:
            filters: Фильтры для WHERE clause
            skip: Количество пропускаемых записей
            limit: Количество записей
            sort_by: Поле для сортировки (created_at, rating, likes, score)
            sort_order: Порядок сортировки (ASC, DESC)
        """
        where_clause = ""
        values: list[Any] = []
        param_index = 1

        if filters:
            where_parts = []
            for key, value in filters.items():
                where_parts.append(f"{key} = ${param_index}")
                values.append(value)
                param_index += 1
            where_clause = "WHERE " + " AND ".join(where_parts)

        # Считаем total
        count_query = f"SELECT COUNT(*) FROM {self.table_name} {where_clause}"
        conn = await PostgreSQL.get_connection()
        try:
            count_row = await conn.fetchrow(count_query, *values)
            total = count_row[0] if count_row else 0

            # Формируем ORDER BY в зависимости от sort_by
            if sort_by == "created_at":
                order_clause = f"r.created_at {sort_order}"
            elif sort_by == "rating":
                order_clause = f"r.rating {sort_order}"
            elif sort_by in ("likes", "score"):
                # Для сортировки по лайкам используем подзапрос
                order_clause = f"""
                    (SELECT COUNT(*) FROM review_likes rl 
                     WHERE rl.review_id = r.id AND rl.is_like = true) {sort_order}
                """
            else:
                order_clause = f"r.created_at {sort_order}"

            data_query = f"""
                SELECT r.* FROM {self.table_name} r
                {where_clause}
                ORDER BY {order_clause}
                LIMIT ${param_index} OFFSET ${param_index + 1}
            """
            values.extend([limit, skip])
            rows = await conn.fetch(data_query, *values)

            return [dict(row) for row in rows], total
        finally:
            await PostgreSQL.release_connection(conn)

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