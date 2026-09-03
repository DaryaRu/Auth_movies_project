from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Request, Response, status
from fastapi_cache.decorator import cache

from src.api.v1.dependencies import (
    AuthServiceDep,
    CurrentUserDep,
    DBDep,
    InternalServiceDep,
    RefreshTokenDep,
    RoleServiceDep,
    SessionServiceDep,
    TokenPayloadDep,
)
from src.core.config import settings
from src.core.limiter import limiter
from src.exceptions import (
    DecodeTokenException,
    InvalidTokenHTTPException,
    InvalidTwoFactorCodeException,
    InvalidTwoFactorCodeHTTPException,
    PasswordAlreadySetException,
    PasswordAlreadySetHTTPException,
    PasswordNotSetException,
    PasswordNotSetHTTPException,
    SendCooldownException,
    TokenExeption,
    TokenKeysException,
    TokenTypeExeption,
    TooManyAttemptsException,
    TooManyAttemptsHTTPException,
    TwoFactorRequiredException,
    UserAlreadyexistsException,
    UserAlreadyexistsHTTPException,
    UserNotFoundException,
    UserNotFoundHTTPException,
    VerifyPasswordException,
    VerifyPasswordHTTPException,
)
from src.schemas.permissions import PermissionResponseScheme
from src.schemas.sessions import UserSessionResponse
from src.schemas.tokens import JWTAccessToken, TwoFactorRequiredScheme
from src.schemas.users import (
    ChangeEmailRequestScheme,
    ChangePasswordRequestScheme,
    ConfirmEmailRequestScheme,
    SetPasswordRequestScheme,
    UpdateFullNameRequestScheme,
    UserContactScheme,
    UserRequestScheme,
    UserResponseScheme,
    UserSearchScheme,
    VerifyTwoFactorRequestScheme,
)

router = APIRouter(tags=["Auth"])


@router.post(
    "/confirm-email/",
    summary="Подтверждение email через короткую ссылку",
    response_model=UserResponseScheme,
)
async def confirm_email(
    data: ConfirmEmailRequestScheme,
    auth_service: AuthServiceDep,
    _: InternalServiceDep,
):
    """Подтверждает email пользователя после перехода по короткой ссылке."""
    try:
        confirmed_user = await auth_service.confirm_email(data.user_id)
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail) from exc
    return confirmed_user


@router.post(
    "/registration/",
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    response_model=UserResponseScheme,
)
@limiter.limit(settings.LIMIT_VALUE)
async def create_user(
    user: UserRequestScheme,
    auth_service: AuthServiceDep,
    request: Request,
):
    """Регистрация нового пользователя. Хэширует пароль и сохраняет в БД."""
    try:
        created_user = await auth_service.register_user(user)
    except UserAlreadyexistsException as exc:
        raise UserAlreadyexistsHTTPException(detail=exc.detail) from exc
    return created_user


@router.post(
    "/login/",
    summary="Вход в аккаунт",
    response_model=JWTAccessToken | TwoFactorRequiredScheme,
)
@limiter.limit(settings.LIMIT_VALUE)
async def login(
    response: Response,
    request: Request,
    user: UserRequestScheme,
    auth_service: AuthServiceDep,
):
    """Аутентификация по email и паролю. Если у пользователя есть телефон,
    вместо токенов возвращает {"two_fa_required": true}, код уходит в СМС,
    вход завершается через /login/verify-phone/. Если не указан номер, возвращает
    access-токен, refresh-токен сохраняется в cookie."""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    try:
        access_token, refresh_token = await auth_service.authenticate_user(
            user, ip_address=ip_address, user_agent=user_agent
        )
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail) from exc
    except VerifyPasswordException as exc:
        raise VerifyPasswordHTTPException(detail=exc.detail) from exc
    except PasswordNotSetException as exc:
        raise PasswordNotSetHTTPException(detail=exc.detail) from exc
    except TooManyAttemptsException as exc:
        raise TooManyAttemptsHTTPException(detail=exc.detail) from exc
    except SendCooldownException as exc:
        raise TooManyAttemptsHTTPException(detail=exc.detail) from exc
    except TwoFactorRequiredException:
        return TwoFactorRequiredScheme()

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


@router.post(
    "/login/verify-phone/",
    summary="Подтверждение кода из СМС при входе",
    response_model=JWTAccessToken,
)
@limiter.limit(settings.LIMIT_VALUE)
async def verify_phone_login(
    response: Response,
    request: Request,
    data: VerifyTwoFactorRequestScheme,
    auth_service: AuthServiceDep,
):
    """Второй шаг входа для пользователей с указанным телефоном.
    Проверяет код из СМС, выданный после /login/, завершает вход тем же способом, что и обычный логин."""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    try:
        (
            access_token,
            refresh_token,
        ) = await auth_service.verify_two_factor_login(
            email=data.email,
            phone=data.phone,
            code=data.code,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail) from exc
    except InvalidTwoFactorCodeException as exc:
        raise InvalidTwoFactorCodeHTTPException(detail=exc.detail) from exc
    except TooManyAttemptsException as exc:
        raise TooManyAttemptsHTTPException(detail=exc.detail) from exc

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
@cache(expire=settings.CACHE_EXPIRE * 6)
async def get_public_key() -> dict[str, str]:
    """Публичный ключ RS256 для верификации JWT другими сервисами. Кэшируется на 1 час."""
    return {"public_key": settings.PUBLIC_KEY}


@router.post(
    "/refresh/", summary="Обновление токенов", response_model=JWTAccessToken
)
@limiter.limit(settings.LIMIT_VALUE)
async def refresh_token(
    refresh_token: RefreshTokenDep,
    response: Response,
    auth_service: AuthServiceDep,
    request: Request,
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
        raise InvalidTokenHTTPException(detail=exc.detail) from exc

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
@limiter.limit(settings.LIMIT_VALUE)
async def get_user_active_sessions(
    token_payload: TokenPayloadDep,
    current_user: CurrentUserDep,
    session_service: SessionServiceDep,
    request: Request,
):
    return await session_service.get_active_sessions(
        user_id=current_user.id,
        current_sid=token_payload["sid"],
    )


@router.get(
    "/users/me/permissions/",
    summary="Права текущего пользователя",
    response_model=list[PermissionResponseScheme],
)
@limiter.limit(settings.LIMIT_VALUE)
async def get_my_permissions(
    current_user: CurrentUserDep,
    role_service: RoleServiceDep,
    request: Request,
):
    """Возвращает список прав доступа, назначенных текущему пользователю через его роли."""
    return await role_service.get_user_permissions(
        user_id=current_user.id,
        is_superuser=current_user.is_superuser,
    )


@router.get(
    "/internal/users/{user_id}/",
    summary="Email пользователя по ID",
    response_model=UserContactScheme,
)
async def get_user_contact(user_id: UUID, db: DBDep, _: InternalServiceDep):
    """Получение контактов пользователя между сервисами."""
    user = await db.users.get_one_or_none_by_id(id=user_id)
    if user is None:
        raise UserNotFoundHTTPException()
    return UserContactScheme(user_id=user.id, email=user.email)


@router.post(
    "/internal/users/search/",
    summary="Поиск пользователей по audience_filter (для рассылок)",
    response_model=list[UUID],
)
async def search_users(
    data: UserSearchScheme, db: DBDep, _: InternalServiceDep
):
    """Используется notifications-service (воркер). Возвращает id активных пользователей,
    подходящих под фильтр."""
    min_level = (
        data.subscription_level.gte
        if data.subscription_level is not None
        else None
    )
    return await db.users.search_by_min_subscription_level(
        min_level, timezone_filter=data.timezone
    )


@router.post(
    "/internal/users/search/timezones/",
    summary="Уникальные таймзоны пользователей (для рассылок)",
    response_model=list[str],
)
async def search_user_timezones(data: UserSearchScheme, db: DBDep):
    """Используется notifications-service для разбивки рассылок по таймзонам.
    Возвращает уникальные таймзоны активных пользователей.
    Пользователи без заданной таймзоны считаются 'UTC'."""
    min_level = (
        data.subscription_level.gte
        if data.subscription_level is not None
        else None
    )
    return await db.users.search_distinct_timezones(
        min_level, timezone_filter=data.timezone
    )


@router.get(
    "/users/me/",
    response_model=UserResponseScheme,
    summary="Получить данные профиля",
)
@limiter.limit(settings.LIMIT_VALUE)
async def get_me_profile(user: CurrentUserDep, request: Request):
    """Данные текущего пользователя: email, телефон, ФИО, таймзона, статус верификации email."""
    return user


@router.patch(
    "/users/me/full-name/",
    response_model=UserResponseScheme,
    summary="Обновить ФИО",
)
@limiter.limit(settings.LIMIT_VALUE)
async def update_full_name(
    data: UpdateFullNameRequestScheme,
    auth_service: AuthServiceDep,
    user: CurrentUserDep,
    request: Request,
):
    """Обновление ФИО текущего пользователя."""
    return await auth_service.update_user_full_name(user_id=user.id, data=data)


@router.patch(
    "/change-email/",
    response_model=UserResponseScheme,
    summary="Смена email",
)
@limiter.limit(settings.LIMIT_VALUE)
async def change_email(
    data: ChangeEmailRequestScheme,
    auth_service: AuthServiceDep,
    user: CurrentUserDep,
    request: Request,
):
    """Смена email с подтверждением текущего пароля. Новый email должен быть уникальным."""
    try:
        updated_user = await auth_service.change_user_email(
            user_id=user.id, data=data
        )
        return updated_user
    except UserAlreadyexistsException as exc:
        raise UserAlreadyexistsHTTPException(detail=exc.detail) from exc
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail) from exc
    except VerifyPasswordException as exc:
        raise VerifyPasswordHTTPException(detail=exc.detail) from exc


@router.patch(
    "/change-password/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Смена пароля",
)
@limiter.limit(settings.LIMIT_VALUE)
async def change_password(
    data: ChangePasswordRequestScheme,
    response: Response,
    auth_service: AuthServiceDep,
    user: CurrentUserDep,
    request: Request,
):
    """Смена пароля с подтверждением текущего. Сбрасывает все активные сессии."""
    try:
        await auth_service.change_user_password(user_id=user.id, data=data)

        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            path="/",
        )

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail) from exc
    except VerifyPasswordException as exc:
        raise VerifyPasswordHTTPException(detail=exc.detail) from exc


@router.post(
    "/set-password/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Установка пароля для OAuth-пользователя",
)
async def set_password(
    data: SetPasswordRequestScheme,
    auth_service: AuthServiceDep,
    user: CurrentUserDep,
):
    """Устанавливает пароль для пользователя, вошедшего через OAuth (без пароля).
    Если пароль уже установлен — использовать /change-password/.
    """
    try:
        await auth_service.set_password(user_id=user.id, data=data)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail) from exc
    except PasswordAlreadySetException as exc:
        raise PasswordAlreadySetHTTPException(detail=exc.detail) from exc
