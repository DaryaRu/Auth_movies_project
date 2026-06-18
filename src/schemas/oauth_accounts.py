from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
