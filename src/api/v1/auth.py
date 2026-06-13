from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request, Response, status
from fastapi_cache.decorator import cache

from src.api.v1.dependiences import (
    AuthServiceDep,
    CurrentUserDep,
    RefreshTokenDep,
    RoleServiceDep,
    SessionServiceDep,
    TokenPayloadDep,
)
from src.core.config import settings
from src.exceptions import (
    DecodeTokenException,
    InvalidTokenHTTPException,
    TokenExeption,
    TokenKeysException,
    TokenTypeExeption,
    UserAlreadyexistsException,
    UserAlreadyexistsHTTPException,
    UserNotFoundException,
    UserNotFoundHTTPException,
    VerifyPasswordException,
    VerifyPasswordHTTPException,
)
from src.schemas.permissions import PermissionResponseScheme
from src.schemas.sessions import UserSessionResponse
from src.schemas.tokens import JWTAccessToken
from src.schemas.users import (
    ChangeEmailRequestScheme,
    ChangePasswordRequestScheme,
    UserRequestScheme,
    UserResponseScheme,
)

router = APIRouter(tags=["Auth"])


@router.post(
    "/registration/",
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    response_model=UserResponseScheme,
)
async def create_user(
    user: UserRequestScheme,
    auth_service: AuthServiceDep,
):
    """Регистрация нового пользователя. Хэширует пароль и сохраняет в БД."""
    try:
        created_user = await auth_service.register_user(user)
    except UserAlreadyexistsException as exc:
        raise UserAlreadyexistsHTTPException(detail=exc.detail)
    return created_user


@router.post(
    "/login/", summary="Вход в аккаунт", response_model=JWTAccessToken
)
async def login(
    response: Response,
    request: Request,
    user: UserRequestScheme,
    auth_service: AuthServiceDep,
):
    """Аутентификация по email и паролю. Возвращает access-токен, refresh-токен сохраняется в cookie."""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    try:
        access_token, refresh_token = await auth_service.authenticate_user(
            user, ip_address=ip_address, user_agent=user_agent
        )
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail)
    except VerifyPasswordException as exc:
        raise VerifyPasswordHTTPException(detail=exc.detail)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )

    return JWTAccessToken(
        access_token=access_token,
        access_token_expire=datetime.now(timezone.utc)
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


@router.get(
    "/jwt.key/",
    summary="Публичный ключ JWT",
)
@cache(expire=3600)
async def get_public_key() -> dict[str, str]:
    """Публичный ключ RS256 для верификации JWT другими сервисами. Кэшируется на 1 час."""
    return {"public_key": settings.PUBLIC_KEY}


@router.post(
    "/refresh/", summary="Обновление токенов", response_model=JWTAccessToken
)
async def refresh_token(
    refresh_token: RefreshTokenDep,
    response: Response,
    auth_service: AuthServiceDep,
):
    """Ротация токенов: старый refresh-токен из cookie заменяется новой парой."""
    try:
        new_access_token, new_refresh_token = await auth_service.refresh_token(
            old_refresh_token=refresh_token
        )
    except (
        DecodeTokenException,
        TokenKeysException,
        TokenTypeExeption,
        TokenExeption,
    ) as exc:
        raise InvalidTokenHTTPException(detail=exc.detail)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )

    return JWTAccessToken(
        access_token=new_access_token,
        access_token_expire=datetime.now(timezone.utc)
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


@router.post(
    "/logout/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выход из аккаунта",
)
async def logout(
    response: Response,
    refresh_token: RefreshTokenDep,
    auth_service: AuthServiceDep,
) -> None:
    """Выход из текущей сессии: удаляет refresh-токен из БД и очищает cookie."""
    await auth_service.revoke_refresh_token(refresh_token=refresh_token)

    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


@router.post(
    "/logout-all/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выход из аккаунта",
)
async def logout_all(
    response: Response,
    refresh_token: RefreshTokenDep,
    auth_service: AuthServiceDep,
) -> None:
    """Выход со всех устройств: удаляет все сессии пользователя из БД и очищает cookie."""
    await auth_service.revoke_all_refresh_tokens(refresh_token=refresh_token)

    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


@router.get(
    "/active_sessions/",
    summary="Получение активных сессий пользователя",
    response_model=list[UserSessionResponse],
)
async def get_user_active_sessions(
    token_payload: TokenPayloadDep,
    current_user: CurrentUserDep,
    session_service: SessionServiceDep,
):
    return await session_service.get_active_sessions(
        user_id=current_user.id,
        current_sid=token_payload.get("sid"),
    )


@router.get(
    "/users/me/permissions/",
    summary="Права текущего пользователя",
    response_model=list[PermissionResponseScheme],
)
async def get_my_permissions(
    current_user: CurrentUserDep,
    role_service: RoleServiceDep,
):
    """Возвращает список прав доступа, назначенных текущему пользователю через его роли."""
    return await role_service.get_user_permissions(
        user_id=current_user.id,
        is_superuser=current_user.is_superuser,
    )


@router.patch(
    "/change-email/",
    response_model=UserResponseScheme,
    summary="Смена email",
)
async def change_email(
    data: ChangeEmailRequestScheme,
    auth_service: AuthServiceDep,
    user: CurrentUserDep,
):
    """Смена email с подтверждением текущего пароля. Новый email должен быть уникальным."""
    try:
        updated_user = await auth_service.change_user_email(
            user_id=user.id, data=data
        )
        return updated_user
    except UserAlreadyexistsException as exc:
        raise UserAlreadyexistsHTTPException(detail=exc.detail)
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail)
    except VerifyPasswordException as exc:
        raise VerifyPasswordHTTPException(detail=exc.detail)


@router.patch(
    "/change-password/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Смена пароля",
)
async def change_password(
    data: ChangePasswordRequestScheme,
    response: Response,
    auth_service: AuthServiceDep,
    user: CurrentUserDep,
):
    """Смена пароля с подтверждением текущего. Сбрасывает все активные сессии."""
    try:
        await auth_service.change_user_password(user_id=user.id, data=data)

        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            secure=True,
            samesite="lax",
            path="/",
        )

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail)
    except VerifyPasswordException as exc:
        raise VerifyPasswordHTTPException(detail=exc.detail)
