from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Response,  Request, status

from src.api.v1.dependiences import AuthServiceDep, CurrentUserDep, RefreshTokenDep, RoleServiceDep, SessionServiceDep, TokenPayloadDep
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
    response_model=UserResponseScheme
)
async def create_user(
    user: UserRequestScheme,
    auth_service: AuthServiceDep,
):
    """
    Регистрация нового пользователя.
    Проверяет, существует ли пользователь с таким email.
    Хэширует пароль и сохраняет пользователя в базе данных.
    Args:
        user (UserRequestScheme): Данные пользователя (email, password).
        auth_service (AuthServiceDep): Сервис для работы с пользователями.
    Raises:
        HTTPException: Если пользователь с таким email уже существует.
    Returns:
        UserResponseScheme: Данные пользователя.
    """
    try:
        created_user = await auth_service.register_user(user)
    except UserAlreadyexistsException as exc:
        raise UserAlreadyexistsHTTPException(detail=exc.detail)
    return created_user


@router.post(
    "/login/",
    summary="Вход в аккаунт",
    response_model=JWTAccessToken
)
async def login(
    response: Response,
    request: Request,
    user: UserRequestScheme,
    auth_service: AuthServiceDep,
):
    """
    Аутентификация пользователя.
    - Проверяет корректность email и пароля.
    - Создаёт access и refresh токены.
    - Сохраняет refresh token в cookie `refresh_token`.
    Args:
        response (Response): Объект FastAPI Response для установки cookie.
        request (Request): Объект запроса для извлечения IP и User-Agent.
        user (UserRequestScheme): Данные пользователя.
        auth_service (AuthServiceDep): Сервис пользователей.
    Raises:
        HTTPException: Если email или пароль некорректны.
    Returns:
        JWTAccessToken: Access токен с временем жизни.
    """
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    try:
        access_token, refresh_token = await auth_service.authenticate_user(
            user,
            ip_address=ip_address,
            user_agent=user_agent
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
        access_token_expire=datetime.now(
            timezone.utc
        ) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )


@router.get(
    "/jwt.key/",
    summary="Публичный ключ JWT",
)
def get_public_key() -> dict[str, str]:
    """
    Получение публичного ключа для верификации JWT.

    Returns:
        dict: Словарь с публичным ключом {"public_key": str}.
    """
    return {"public_key": settings.PUBLIC_KEY}


@router.post(
    "/refresh/",
    summary="Обновление токенов",
    response_model=JWTAccessToken
)
async def refresh_token(
    refresh_token: RefreshTokenDep,
    response: Response,
    auth_service: AuthServiceDep,
):
    """
    Обновление пары JWT-токенов (Access и Refresh).
    - Извлекает старый refresh-токен из HTTP-кук.
    - Выполняет процедуру ротации токенов в сервисе.
    - Перезаписывает новые куки в HTTP-ответ.

    Args:
        request (Request): Объект запроса для извлечения старой куки.
        response (Response): Объект ответа для установки новых кук.
        auth_service (AuthServiceDep): Зависимость сервиса аутентификации.

    Raises:
        HTTPException: Если refresh-токен отсутствует, невалиден или протух.

    Returns:
        JWTAccessToken: Новый Access токен со временем жизни.
    """
    try:
        new_access_token, new_refresh_token = await auth_service.refresh_token(
            old_refresh_token=refresh_token
        )
    except (
        DecodeTokenException,
        TokenKeysException,
        TokenTypeExeption,
        TokenExeption
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
        access_token_expire=datetime.now(
            timezone.utc
        ) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
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
    """
    Выход пользователя из аккаунта с отзывом текущей сессии.
    - Удаляет запись о текущем refresh-токене из базы данных.
    - Стирает авторизационные куки (refresh_token) на клиенте.

    Args:
        response (Response): Объект ответа FastAPI для очистки кук.
        refresh_token (RefreshTokenDep): Зависимость,
        извлекающая текущий refresh-токен.
        auth_service (AuthServiceDep): Зависимость сервиса аутентификации.

    Returns:
        Response: Пустой ответ со статусом HTTP 204 No Content.
    """
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
    """
    Выход пользователя из всех активных устройств.
    - Удаляет все сессии пользователя.
    - Стирает авторизационные куки (refresh_token) на клиенте.

    Args:
        response (Response): Объект ответа FastAPI для очистки кук.
        refresh_token (RefreshTokenDep): Зависимость,
        извлекающая текущий refresh-токен.
        auth_service (AuthServiceDep): Зависимость сервиса аутентификации.

    Returns:
        Response: Пустой ответ со статусом HTTP 204 No Content.
    """
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
    response_model=list[UserSessionResponse]
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
    """
    Смена email пользователя после проверки пароля.

    - Проверяет существование пользователя в системе.
    - Гарантирует уникальность нового email адреса.
    - Верифицирует текущий пароль для подтверждения личности.

    Args:
        user_id (UUID): Уникальный идентификатор пользователя.
        data (ChangeEmailRequestScheme): Схема с новым email и паролем.

    Raises:
        UserNotFoundException: Если пользователь с таким ID не найден.
        UserAlreadyexistsException: Если новый email уже занят.
        VerifyPasswordException: Если текущий пароль введен неверно.

    Returns:
        UserORM: Обновленный объект пользователя из базы данных.
    """
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
    """
    Смена пароля пользователя и отзыв всех его текущих сессий.

    - Проверяет существование пользователя в системе.
    - Верифицирует старый пароль перед внесением изменений.
    - Удаляет абсолютно все активные сессии из базы данных.

    Args:
        user_id (UUID): Уникальный идентификатор пользователя.
        data (ChangePasswordRequestScheme): Схема со старым и новым паролями.

    Raises:
        UserNotFoundException: Если пользователь с таким ID не найден.
        VerifyPasswordException: Если текущий старый пароль введен неверно.
    """
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
