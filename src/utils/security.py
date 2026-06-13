from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param

from src.exceptions import InvalidTokenHTTPException


class CustomHTTPBearer(HTTPBearer):
    async def __call__(
        self,
        request: Request,
    ) -> HTTPAuthorizationCredentials:
        authorization = request.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)

        if not authorization or not credentials:
            raise InvalidTokenHTTPException(detail="Токен не обнаружен")

        if scheme.lower() != "bearer":
            raise InvalidTokenHTTPException(detail="Некорректный тип авторизации")

        return HTTPAuthorizationCredentials(
            scheme=scheme,
            credentials=credentials,
        )
