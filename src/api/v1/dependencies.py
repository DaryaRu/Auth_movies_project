from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from src.databases import redis
from src.databases.pg import async_session_maker
from src.exceptions import (
    DecodeTokenException,
    DecodeTokenHTTPException,
    InvalidTokenHTTPException,
    NotEnoughPermissionsHTTPException,
    TokenKeysException,
    TokenKeysHTTPException,
)
from src.models.users import UserORM
from src.repositories.sessions import SessionRedisRepository
from src.services.auth import AuthService
from src.services.oauth import OAuthService
from src.services.permissions import PermissionService
from src.services.roles import RoleService
from src.services.sessions import SessionService
from src.utils.db_manager import DBManager
from src.utils.hashes import HashArgon2Service
from src.utils.security import CustomHTTPBearer
from src.utils.tokens import JWTTokenService

security = CustomHTTPBearer(auto_error=False)


def get_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return credentials.credentials


def get_refresh_token(request: Request) -> str:
    token = request.cookies.get("refresh_token")
    if token is None:
        raise InvalidTokenHTTPException(detail="Токен не обнаружен")
    return token


def get_db_manager():
    return DBManager(session_factory=async_session_maker)


async def get_db():
    async with get_db_manager() as db:
        yield db
        
        
def get_session_service() -> SessionService:
    return SessionService(
        SessionRedisRepository(redis.redis)
    )


def get_auth_service(db: "DBDep", session_service: "SessionServiceDep") -> AuthService:
    return AuthService(
        HashArgon2Service(),
        JWTTokenService(),
        session_service,
        db
    )


def get_role_service(db: "DBDep") -> RoleService:
    return RoleService(db)


def get_permission_service(db: "DBDep") -> PermissionService:
    return PermissionService(db)


def get_oauth_service(db: "DBDep", session_service: "SessionServiceDep") -> OAuthService:
    return OAuthService(
        JWTTokenService(),
        session_service,
        db,
    )


async def get_token_payload(
    session_service: "SessionServiceDep",
    token: str = Depends(get_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    try:
        data = auth_service.decode_token(token)
    except DecodeTokenException as exc:
        raise DecodeTokenHTTPException(detail=exc.detail)
    except TokenKeysException as exc:
        raise TokenKeysHTTPException(detail=exc.detail)
    session = await session_service.get_session(data["sid"])
    if not session:
        raise InvalidTokenHTTPException(detail="Невалидный токен")
    return data


async def get_current_user(
    db: "DBDep",
    token_payload: dict[str, Any] = Depends(get_token_payload),
) -> UserORM:
    """Возвращает текущего пользователя по id из токена. Выбрасывает 401, если пользователь не найден."""
    user = await db.users.get_one_or_none_by_id(UUID(token_payload.get("sub")))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Пользователь не найден"},
        )
    return user


async def get_current_staff_user(
    user: UserORM = Depends(get_current_user),
) -> UserORM:
    """Проверяет, что текущий пользователь является суперпользователем. Выбрасывает 403, если нет."""
    if not user.is_superuser:
        raise NotEnoughPermissionsHTTPException()
    return user


OAuthServiceDep = Annotated[OAuthService, Depends(get_oauth_service)]
CurrentUserDep = Annotated[UserORM, Depends(get_current_user)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
RefreshTokenDep = Annotated[str, Depends(get_refresh_token)]
RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]
PermissionServiceDep = Annotated[PermissionService, Depends(get_permission_service)]
StaffUserDep = Annotated[UserORM, Depends(get_current_staff_user)]
TokenPayloadDep = Annotated[dict[str, Any], Depends(get_token_payload)]
DBDep = Annotated[DBManager, Depends(get_db)]
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
