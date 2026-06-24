from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OAuthRedirectURLScheme(BaseModel):
    """Схема ответа с URL авторизации провайдера."""

    url: str


class OAuthAccountResponseScheme(BaseModel):
    """Схема ответа с данными OAuth-аккаунта.

    Атрибуты:
        id (UUID): Уникальный идентификатор.
        user_id (UUID): Идентификатор пользователя в системе.
        provider (str): Название провайдера (google, yandex, vk).
        provider_user_id (str): Идентификатор пользователя на стороне провайдера.
    """

    id: UUID
    user_id: UUID
    provider: str
    provider_user_id: str

    model_config = ConfigDict(from_attributes=True)


class OAuthUnlinkResponseScheme(BaseModel):
    """Схема ответа после успешной отвязки OAuth-аккаунта."""

    status: str = "success"
    message: str
    linked_providers: list[str] = Field(
        description="Список оставшихся привязанных к личному кабинету провайдеров"
    )
