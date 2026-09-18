"""Схемы для рецензий."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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
    """Публичная (внешняя) схема ответа рецензии.

    Это публичная схема, по которой рецензия отдаётся клиентам. Она намеренно
    отделена от внутренней модели (записи в БД): внутри сервиса идентификатор
    автора `user_id` сохраняется и используется для проверки владельца и
    обработки голосов (лайков/дизлайков), однако в публичном ответе для
    анонимных рецензий (`author_visibility='anonymous'`) он скрыт
    (`user_id=None`), чтобы нельзя было связать анонимную рецензию с другими
    рецензиями того же автора, опубликованными с ФИО.
    """

    id: UUID = Field(..., description="ID рецензии")
    user_id: UUID | None = Field(
        default=None,
        description="ID пользователя-автора; для анонимных рецензий (author_visibility='anonymous') скрыт (None)",
    )
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    likes_count: int = Field(default=0, description="Количество лайков рецензии")
    dislikes_count: int = Field(default=0, description="Количество дизлайков рецензии")
    score: int = Field(default=0, description="Разница между лайками и дизлайками")
    author_name: str = Field(default="Аноним", description="Имя автора (snapshot из auth-сервиса для author_visibility='real_name' — ФИО, для 'nickname' — никнейм, иначе 'Аноним')")
    author_visibility: str = Field(default='real_name', description="Видимость имени автора: 'real_name', 'nickname' или 'anonymous'")

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def hide_anonymous_author_id(self) -> "ReviewResponse":
        """Скрыть идентификатор автора в публичном ответе анонимной рецензии.

        `user_id` остаётся внутри сервиса (запись БД, проверка владельца,
        обработка лайков/дизлайков), но клиенту для анонимных рецензий не
        передаётся: это исключает возможность связать анонимную рецензию с
        другими рецензиями того же автора, опубликованными с ФИО.
        """
        if self.author_visibility == "anonymous":
            self.user_id = None
        return self


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
