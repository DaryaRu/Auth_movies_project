from datetime import datetime

from pydantic import BaseModel


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
