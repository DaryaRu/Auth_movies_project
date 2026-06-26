"""Схемы подписок пользователей."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.subscriptions import SubscriptionResponseScheme

USER_SUBSCRIPTION_EXAMPLE = {
    "subscription_code": "premium",
    "expires_at": "2027-01-01",
}


class UserSubscriptionCreateScheme(BaseModel):
    """Схема для назначения подписки пользователю.

    Атрибуты:
        subscription_code (str): Код типа подписки, например, "free", "premium".
        expires_at (date): Дата окончания подписки.
    """

    model_config = ConfigDict(
        json_schema_extra={"example": USER_SUBSCRIPTION_EXAMPLE}
    )

    subscription_code: str = Field(..., description="Код типа подписки, например, premium")
    expires_at: date = Field(..., description="Дата окончания подписки")


class UserSubscriptionResponseScheme(BaseModel):
    """Схема ответа с данными подписки пользователя.

    Атрибуты:
        id (UUID): Уникальный идентификатор записи.
        user_id (UUID): Идентификатор пользователя.
        subscription (SubscriptionResponseScheme): Данные типа подписки.
        started_at (datetime): Дата и время начала подписки.
        expires_at (datetime): Дата и время окончания подписки.
        is_active (bool): Активна ли подписка.
    """

    id: UUID
    user_id: UUID
    subscription: SubscriptionResponseScheme
    started_at: datetime
    expires_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
