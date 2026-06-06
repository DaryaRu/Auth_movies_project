from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, BaseModel, ConfigDict


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
    is_staff: bool
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class JWTAccessToken(BaseModel):
    """
    Схема ответа при успешной авторизации пользователя.
    Атрибуты:
        access_token (str): JWT access токен.
        access_token_expire (datetime): Дата и время истечения срока действия токена.
        token_type (str): Тип токена. По умолчанию "bearer".
    """

    access_token: str
    access_token_expire: datetime
    token_type: str = "bearer"
