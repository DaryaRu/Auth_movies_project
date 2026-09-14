"""Схемы для рецензий."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewBase(BaseModel):
    """Базовая схема рецензии.
    
    Рецензия состоит из трёх составляющих:
    1. Текст рецензии — пользовательское мнение о фильме
    2. Дополнительные данные — дата публикации, автор (user_id)
    3. Данные из смежных таблиц — лайки/дизлайки рецензии, оценка фильма
    """

    movie_id: UUID = Field(..., description="UUID фильма")
    text: str = Field(..., min_length=10, max_length=5000, description="Текст рецензии")
    rating: int = Field(
        ...,
        ge=1,
        le=10,
        description="Оценка фильма пользователем (привязана к рецензии). Шкала от 1 (худший фильм) до 10 (лучший фильм)"
    )


class ReviewCreate(ReviewBase):
    """Схема для создания рецензии."""

    author_visibility: Literal['real_name', 'nickname', 'anonymous'] = Field(
        default='real_name',
        description="Видимость имени автора: 'real_name' (по умолчанию) — показать ФИО, 'nickname' — показать никнейм, 'anonymous' — скрыть"
    )


class ReviewUpdate(BaseModel):
    """Схема для обновления рецензии."""
    text: str | None = Field(default=None, min_length=10, max_length=5000, description="Текст рецензии")
    rating: int | None = Field(default=None, ge=1, le=10, description="Оценка от 1 до 10")


class ReviewResponse(ReviewBase):
    """Схема ответа рецензии."""

    id: UUID = Field(..., description="ID рецензии")
    user_id: UUID = Field(..., description="ID пользователя")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    likes_count: int = Field(default=0, description="Количество лайков рецензии")
    dislikes_count: int = Field(default=0, description="Количество дизлайков рецензии")
    score: int = Field(default=0, description="Разница между лайками и дизлайками")
    author_name: str = Field(default="Аноним", description="Имя автора (snapshot из auth-сервиса для author_visibility='real_name' — ФИО, для 'nickname' — никнейм, иначе 'Аноним')")
    author_visibility: str = Field(default='real_name', description="Видимость имени автора: 'real_name', 'nickname' или 'anonymous'")

    model_config = {"from_attributes": True}


class ReviewsListResponse(BaseModel):
    """Схема ответа списка рецензий."""

    items: list[ReviewResponse]
    total: int
    page: int
    page_size: int


class ReviewStatsResponse(BaseModel):
    """Схема ответа статистики рецензий фильма."""

    avg_rating: float = Field(..., description="Средняя оценка фильма по рецензиям")
    count: int = Field(..., description="Количество рецензий")
