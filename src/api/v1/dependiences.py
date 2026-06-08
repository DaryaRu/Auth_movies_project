from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from src.databases.pg import async_session_maker
from src.exceptions import (
    DecodeTokenException,
    DecodeTokenHTTPException,
    TokenKeysException,
    TokenKeysHTTPException,
)
from src.services.auth import AuthService
from src.utils.db_manager import DBManager
from src.utils.hashes import HashArgon2Service
from src.utils.tokens import JWTTokenService


def get_token(request: Request) -> str:
    token = request.cookies.get("access_token")
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Токен доступа не обнаружен"},
        )
    return token


def get_refresh_token(request: Request) -> str:
    token = request.cookies.get("refresh_token")
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Refresh-токен не обнаружен"},
        )
    return token


def get_db_manager():
    return DBManager(session_factory=async_session_maker)


async def get_db():
    async with get_db_manager() as db:
        yield db


DBDep = Annotated[DBManager, Depends(get_db)]


def get_auth_service(db: DBDep) -> AuthService:
    return AuthService(HashArgon2Service(), JWTTokenService(), db)


def get_current_user_id(
        token: str = Depends(get_token),
        auth_service: AuthService = Depends(get_auth_service)) -> UUID:
    try:
        data = auth_service.decode_token(token)
    except DecodeTokenException as exc:
        raise DecodeTokenHTTPException(detail=exc.detail)
    except TokenKeysException as exc:
        raise TokenKeysHTTPException(detail=exc.detail)
    return UUID(data.get("sub"))


UserIDDep = Annotated[UUID, Depends(get_current_user_id)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
RefreshTokenDep = Annotated[str, Depends(get_refresh_token)]
