from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from src.core.config import settings
from src.exceptions import DecodeTokenException, TokenExpiredException, TokenKeysException


class JWTTokenService:
    """
    Сервис для генерации и валидации JWT токенов.
    """

    def create_access_and_refresh_tokens(self, data: dict[str, Any]) -> Tuple[str, str]:
        """
        Создаёт пару токенов: access и refresh.
        Args:
            data (dict): Данные, которые будут добпавлены в payload токена.
        Returns:
            Tuple[str, str]: Кортеж, который содержит access_token и refresh_token.
        """
        access_token = self._create_jwt_token(
            data,
            "access",
            settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )
        refresh_token = self._create_jwt_token(
            data,
            "refresh",
            settings.REFRESH_TOKEN_EXPIRE_DAYS,
        )
        return access_token, refresh_token

    @staticmethod
    def _create_jwt_token(data: dict[str, Any], token_type: str, token_expire: int) -> str:
        """
        Создаёт JWT токен определённого типа.
        Args:
            data (dict): Данные для payload.
            type (str): Тип токена.
            token_expire (int): Время жизни токена.
        Returns:
            str: Сгенерированный JWT токен.
        """
        if token_type == "access":
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=token_expire
            )
        elif token_type == "refresh":
            expire = datetime.now(timezone.utc) + timedelta(days=token_expire)
        else:
            raise ValueError(
                "Неверный тип токена. Ожидается 'access' или 'refresh'."
            )

        payload = data.copy()
        payload.update({"exp": expire, "type": token_type, "iat": datetime.now(timezone.utc)})

        token = jwt.encode(
            payload, settings.PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return token

    def decode_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Декодирует и проверяет JWT токен.
        Args:
            token (str): JWT токен.
        Returns:
            [Dict[str, Any]]: словарь с расшифрованными данными, если токен валиден;
        """
        try:
            decode_token = jwt.decode(
                token,
                settings.PUBLIC_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except ExpiredSignatureError:
            raise TokenExpiredException
        except (JWTError, AttributeError):
            raise DecodeTokenException
        
        required = {"sub", "exp", "type", "iat"}
        if not required.issubset(decode_token):
            raise TokenKeysException

        return decode_token
