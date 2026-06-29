"""Схемы типов подписок."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SUBSCRIPTION_EXAMPLE = {
    "code": "free",
    "description": "Свободный доступ к фильмам",
    "level": 0,
    "is_active": True,
}


class SubscriptionCreateScheme(BaseModel):
    """Схема для создания подписки.

    Атрибуты:
        code (str): Уникальный код подписки, например, "free", "base", "premium".
        description (str | None): Описание подписки.
        level (int): Числовое значение для сравнения доступа (0 - free, 1 - base, 2 - premium).
        is_active (bool): Активна ли подписка (по умолчанию — True).
    """

    model_config = ConfigDict(
        json_schema_extra={"example": SUBSCRIPTION_EXAMPLE}
    )

    code: str = Field(
        ...,
        description="Код подписки, например, premium",
        max_length=50,
    )
    description: str | None = Field(None, description="Описание подписки")
    level: int = Field(
        ..., description="Числовое значение для сравнения доступа, например, 2"
    )
    is_active: bool = Field(True, description="Активна ли подписка")


class SubscriptionUpdateScheme(BaseModel):
    """Схема для обновления подписки.

    Атрибуты:
        code (str | None): Новый код подписки.
        description (str | None): Новое описание.
        level (int | None): Новое числовое значение.
        is_active (bool | None): Новый статус активности.
    """

    model_config = ConfigDict(
        json_schema_extra={"example": SUBSCRIPTION_EXAMPLE}
    )

    code: str | None = Field(
        None,
        description="Новый код подписки",
        max_length=50,
    )
    description: str | None = Field(
        None, description="Новое описание подписки"
    )
    level: int | None = Field(None, description="Новое числовое значение")
    is_active: bool | None = Field(None, description="Новый статус активности")


class SubscriptionResponseScheme(BaseModel):
    """Схема ответа с данными подписки.

    Атрибуты:
        id (UUID): Уникальный идентификатор подписки.
        code (str): Код подписки.
        description (str | None): Описание подписки.
        level (int): Числовое значение для сравнения доступа.
        is_active (bool): Активность подписки.
    """

    id: UUID
    code: str
    description: str | None
    level: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
