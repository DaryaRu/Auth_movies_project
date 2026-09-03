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
FULL_NAME_REGEX = re.compile(r"^[А-ЯЁа-яёA-Za-z'\- ]+$")
_VALID_TIMEZONES = available_timezones()


def _validate_full_name(v: str | None) -> str | None:
    if v is None:
        return v

    v = " ".join(v.split())
    if not v:
        return None

    if not (4 <= len(v) <= 255):
        raise ValueError("ФИО должно быть от 4 до 255 символов")

    if not FULL_NAME_REGEX.match(v):
        raise ValueError(
            "ФИО может содержать только буквы, пробел, дефис и апостроф"
        )

    return v


class UserRequestScheme(BaseModel):
    """
    Схема запроса для создания или аутентификации пользователя.
    Атрибуты:
        email (EmailStr): Электронная почта пользователя.
        phone (str): Номер телефона пользователя.
        password (str): Пароль пользователя.
        timezone (str): IANA-имя таймзоны (например Europe/Moscow).
        full_name (str): ФИО пользователя.
    """

    email: EmailStr | None = None
    phone: str | None = None
    password: str
    timezone: str | None = None
    full_name: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "test@example.com",
                "phone": "+79123456789",
                "password": "12345TestPassword",
                "timezone": "Europe/Moscow",
                "full_name": "Иванов Иван Иванович",
            }
        }
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None):
        if v is None:
            return v

        if not PHONE_REGEX.match(v):
            raise ValueError("Некорректный формат телефона")

        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None):
        return _validate_full_name(v)

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
    full_name: str | None = None
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


class UpdateFullNameRequestScheme(BaseModel):
    """Схема для обновления ФИО."""

    full_name: str | None = None

    model_config = ConfigDict(
        json_schema_extra={"example": {"full_name": "Иванов Иван Иванович"}}
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None):
        return _validate_full_name(v)


class VerifyTwoFactorRequestScheme(BaseModel):
    """Схема для подтверждения кода из СМС на втором шаге логина."""

    email: EmailStr | None = None
    phone: str | None = None
    code: str = Field(..., description="Код подтверждения из СМС")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "test@example.com", "code": "482913"}
        }
    )

    @model_validator(mode="after")
    def validate_login_method(self):
        if not self.email and not self.phone:
            raise ValueError("Необходимо указать email или телефон")

        return self


class ChangeEmailRequestScheme(BaseModel):
    """Схема для смены email."""

    new_email: EmailStr
    password: str = Field(..., description="Текущий пароль для подтверждения")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "new_email": "newtest@example.com",
                "password": "12345TestPassword",
            }
        }
    )


class ChangePasswordRequestScheme(BaseModel):
    """Схема для смены пароля."""

    current_password: str = Field(..., description="Текущий пароль")
    new_password: str = Field(..., description="Новый пароль")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "12345TestPassword",
                "new_password": "NewTestPassword12345",
            }
        }
    )


class SetPasswordRequestScheme(BaseModel):
    """Схема для установки пароля OAuth-пользователем без пароля."""

    password: str = Field(..., description="Новый пароль")

    model_config = ConfigDict(
        json_schema_extra={"example": {"password": "12345TestPassword"}}
    )


class ConfirmEmailRequestScheme(BaseModel):
    """Схема для подтверждения email через внутренний вызов."""

    user_id: UUID = Field(..., description="Идентификатор пользователя")
