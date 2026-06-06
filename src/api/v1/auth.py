from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Response, status

from src.api.v1.dependiences import AuthServiceDep
from src.core.config import settings
from src.schemas.users import JWTAccessToken, UserRequestScheme, UserResponseScheme
from src.exceptions import UserAlreadyexistsException, UserAlreadyexistsHTTPException, UserNotFoundError, UserNotFoundHTTPException, VerifyPasswordError, VerifyPasswordHTTPException

router = APIRouter(prefix="/api/v1", tags=["Auth"])


@router.post(
    "/registration/",
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user: UserRequestScheme,
    user_service: AuthServiceDep,
) -> UserResponseScheme:
    """
    Регистрация нового пользователя.
    Проверяет, существует ли пользователь с таким email.
    Хэширует пароль и сохраняет пользователя в базе данных.
    Args:
        user (UserRequestScheme): Данные пользователя (email, password).
        user_service (UserService): Сервис для работы с пользователями.
    Raises:
        HTTPException: Если пользователь с таким email уже существует.
    Returns:
        UserResponseScheme: Данные пользователя.
    """
    try:
        created_user = await user_service.register_user(user)
    except UserAlreadyexistsException as exc:
        raise UserAlreadyexistsHTTPException(detail=exc.detail)
    return created_user


@router.post("/login/")
async def login(
    response: Response,
    user: UserRequestScheme,
    auth_service: AuthServiceDep,
) -> JWTAccessToken:
    """
    Аутентификация пользователя.
    - Проверяет корректность email и пароля.
    - Создаёт access и refresh токены.
    - Сохраняет refresh token в cookie `refresh_token`.
    Args:
        response (Response): Объект FastAPI Response для установки cookie.
        user (UserRequestScheme): Данные пользователя.
        auth_service (AuthService): Сервис пользователей.
    Raises:
        HTTPException: Если email или пароль некорректны.
    Returns:
        JWTAccessToken: Access токен с временем жизни.
    """
    try:
        access_token, refresh_token = await auth_service.authenticate_user(user)
    except UserNotFoundError as exc:
        raise UserNotFoundHTTPException(detail=exc.detail)
    except VerifyPasswordError as exc:
        raise VerifyPasswordHTTPException(detail=exc.detail)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        secure=True,
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


@router.get("/jwt.key")
def get_public_key():
    """
    Получение публичного ключа для верификации JWT.

    Returns:
        dict: Словарь с публичным ключом {"public_key": str}.
    """
    return {"public_key": settings.PUBLIC_KEY}
