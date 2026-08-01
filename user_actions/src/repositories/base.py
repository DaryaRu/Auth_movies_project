"""Базовый репозиторий для PostgreSQL."""

from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

from src.db.postgres import PostgreSQL

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """Базовый репозиторий для работы с PostgreSQL."""

    table_name: str = ""

    async def create(self, data: dict[str, Any], returning: str = "id") -> UUID:
        """Создать запись и вернуть её ID."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f"${i + 1}" for i in range(len(data)))
        values = list(data.values())

        query = f"""
            INSERT INTO {self.table_name} ({columns})
            VALUES ({placeholders})
            RETURNING {returning}
        """
        conn = await PostgreSQL.get_connection()
        try:
            row = await conn.fetchrow(query, *values)
            return row[returning] if row else UUID(int=0)
        finally:
            await PostgreSQL.release_connection(conn)

    async def update(self, doc_id: UUID, update_data: dict[str, Any]) -> dict[str, Any] | None:
        """Обновить запись."""
        set_clause = ", ".join(f"{key} = ${i + 1}" for i, key in enumerate(update_data.keys()))
        values = list(update_data.values()) + [doc_id]

        query = f"""
            UPDATE {self.table_name}
            SET {set_clause}
            WHERE id = ${len(values)}
            RETURNING *
        """
        conn = await PostgreSQL.get_connection()
        try:
            row = await conn.fetchrow(query, *values)
            if row:
                return dict(row)
            return None
        finally:
            await PostgreSQL.release_connection(conn)

    async def find_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        """Найти записи по user_id."""
        return await self._get_all(skip=skip, limit=limit, filters={"user_id": user_id})

    async def find_by_movie(
        self,
        movie_id: UUID,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        """Найти записи по movie_id."""
        return await self._get_all(skip=skip, limit=limit, filters={"movie_id": movie_id})

    async def _get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        order_by: str = "created_at DESC",
    ) -> tuple[list[dict[str, Any]], int]:
        """Получить все записи с пагинацией (внутренний метод)."""
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

        count_query = f"SELECT COUNT(*) FROM {self.table_name} {where_clause}"
        conn = await PostgreSQL.get_connection()
        try:
            count_row = await conn.fetchrow(count_query, *values)
            total = count_row[0] if count_row else 0

            data_query = f"""
                SELECT * FROM {self.table_name}
                {where_clause}
                ORDER BY {order_by}
                LIMIT ${param_index} OFFSET ${param_index + 1}
            """
            values.extend([limit, skip])
            rows = await conn.fetch(data_query, *values)

            return [dict(row) for row in rows], total
        finally:
            await PostgreSQL.release_connection(conn)

    async def find_one(
        self,
        filters: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Найти одну запись по фильтрам."""
        where_parts = []
        values = []
        for i, (key, value) in enumerate(filters.items()):
            where_parts.append(f"{key} = ${i + 1}")
            values.append(value)

        where_clause = "WHERE " + " AND ".join(where_parts)
        query = f"SELECT * FROM {self.table_name} {where_clause} LIMIT 1"

        conn = await PostgreSQL.get_connection()
        try:
            row = await conn.fetchrow(query, *values)
            if row:
                return dict(row)
            return None
        finally:
            await PostgreSQL.release_connection(conn)

    async def delete_by_filters(self, filters: dict[str, Any]) -> bool:
        """Удалить запись по фильтрам."""
        where_parts = []
        values = []
        for i, (key, value) in enumerate(filters.items()):
            where_parts.append(f"{key} = ${i + 1}")
            values.append(value)

        where_clause = "WHERE " + " AND ".join(where_parts)
        query = f"DELETE FROM {self.table_name} {where_clause}"

        conn = await PostgreSQL.get_connection()
        try:
            result = await conn.execute(query, *values)
            return result == "DELETE 1"
        finally:
            await PostgreSQL.release_connection(conn)
