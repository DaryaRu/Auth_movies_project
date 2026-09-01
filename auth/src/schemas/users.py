import re
from datetime import datetime
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

PHONE_REGEX = re.compile(r"^\+[1-9]\d{7,14}$")
_VALID_TIMEZONES = available_timezones()


class UserRequestScheme(BaseModel):
    """
    Схема запроса для создания или аутентификации пользователя.
    Атрибуты:
        email (EmailStr): Электронная почта пользователя.
        password (str): Пароль пользователя.
        timezone (str): IANA-имя таймзоны (например Europe/Moscow).
    """

    email: EmailStr | None = None
    phone: str | None = None
    password: str
    timezone: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None):
        if v is None:
            return v

        if not PHONE_REGEX.match(v):
            raise ValueError("Некорректный формат телефона")

        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None):
        if v is None:
            return v

        if v not in _VALID_TIMEZONES:
            raise ValueError(f"Неизвестная таймзона: {v}")

        return v

    @model_validator(mode="after")
    def validate_login_method(self):
        if not self.email and not self.phone:
            raise ValueError("Необходимо указать email или телефон")

        return self


class UserResponseScheme(BaseModel):
    """
    Схема ответа при возвращении данных пользователя.
    Атрибуты:
        id (int): Уникальный идентификатор пользователя.
        email (EmailStr): Электронная почта пользователя.
    """

    id: UUID
    email: EmailStr | None
    phone: str | None
    is_superuser: bool
    is_active: bool
    email_verified: bool = False
    timezone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserContactScheme(BaseModel):
    """Данные пользователя для нотификации."""

    user_id: UUID
    email: EmailStr | None


class SubscriptionLevelFilter(BaseModel):
    """Условие фильтрации по уровню подписки."""

    gte: int = Field(
        ..., description="Минимальный уровень подписки (включительно)"
    )


class UserSearchScheme(BaseModel):
    """Фильтр аудитории для поиска пользователей (audience_filter из notifications-service).

    Пользователи без активной подписки считаются имеющими уровень 0 (free).
    """

    subscription_level: SubscriptionLevelFilter | None = Field(
        default=None,
        description="Без фильтра. Все активные пользователи",
    )
    timezone: str | None = Field(
        default=None,
        description="Точное совпадение по IANA-таймзоне. Без фильтра — любая (включая не заданную).",
    )


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


class ChangeEmailRequestScheme(BaseModel):
    """Схема для смены email."""

    new_email: EmailStr
    password: str = Field(..., description="Текущий пароль для подтверждения")


class ChangePasswordRequestScheme(BaseModel):
    """Схема для смены пароля."""

    current_password: str = Field(..., description="Текущий пароль")
    new_password: str = Field(..., description="Новый пароль")


class SetPasswordRequestScheme(BaseModel):
    """Схема для установки пароля OAuth-пользователем без пароля."""

    password: str = Field(..., description="Новый пароль")


class ConfirmEmailRequestScheme(BaseModel):
    """Схема для подтверждения email через внутренний вызов."""

    user_id: UUID = Field(..., description="Идентификатор пользователя")

class ChangeTimezoneRequestScheme(BaseModel):
    """Схема для смены таймзоны."""
    
    timezone: str = Field(..., description='IANA-имя таймзоны (например, Europe/Moscow)')

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in _VALID_TIMEZONES:
            raise ValueError(f'Неизвестная таймзона: {v}')
        return v
