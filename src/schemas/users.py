from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRequestScheme(BaseModel):
    """
    Схема запроса для создания или аутентификации пользователя.
    Атрибуты:
        email (EmailStr): Электронная почта пользователя.
        password (str): Пароль пользователя.
    """

    email: EmailStr
    password: str


class UserResponseScheme(BaseModel):
    """
    Схема ответа при возвращении данных пользователя.
    Атрибуты:
        id (int): Уникальный идентификатор пользователя.
        email (EmailStr): Электронная почта пользователя.
    """

    id: UUID
    email: EmailStr
    is_superuser: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class RefreshTokenCreate(BaseModel):
    """Схема для валидации данных при создании записи о refresh-токене в БД.

    Атрибуты:
        token (str): Refresh-токен.
        user_id (UUID): Идентификатор пользователя.
        expires_at (datetime): Время истечения срока действия.
    """

    token: str
    user_id: UUID
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginHistoryResponseScheme(BaseModel):
    """Схема ответа для элемента истории входов (активной сессии)."""
    id: UUID
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)
