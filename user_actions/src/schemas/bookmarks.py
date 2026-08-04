"""Схемы для закладок."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BookmarkBase(BaseModel):
    """Базовая схема закладки."""

    movie_id: UUID = Field(..., description="UUID фильма")


class BookmarkCreate(BookmarkBase):
    """Схема для создания закладки."""

    pass


class BookmarkResponse(BookmarkBase):
    """Схема ответа закладки."""

    id: UUID = Field(..., description="ID закладки")
    user_id: UUID = Field(..., description="ID пользователя")
    created_at: datetime = Field(..., description="Дата создания")

    model_config = {"from_attributes": True}


class BookmarksListResponse(BaseModel):
    """Схема ответа списка закладок."""

    items: list[BookmarkResponse]
    total: int
