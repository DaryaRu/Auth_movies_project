"""Вход по паролю/2FA, обновление и отзыв токенов и сессий."""

from typing import Any
from uuid import UUID

from src.exceptions import (
    DecodeTokenException,
    InvalidTwoFactorCodeException,
    PasswordNotSetException,
    TokenExeption,
    TokenKeysException,
    TokenTypeExeption,
    TwoFactorRequiredException,
    UserNotFoundException,
    VerifyPasswordException,
)
from src.schemas.users import UserRequestScheme
from src.services.base import BaseService
from src.services.login_completion import LoginCompletionService
from src.services.sessions import SessionService
from src.services.two_factor import TwoFactorService
from src.utils.db_manager import DBManager
from src.utils.hashes import BaseHashService
from src.utils.tokens import JWTTokenService


class AuthService(BaseService):
    """Вход по паролю/2FA, обновление и отзыв токенов и сессий."""

    def __init__(
        self,
        hash_service: BaseHashService,
        token_service: JWTTokenService,
        session_service: SessionService,
        db: DBManager,
        two_factor_service: TwoFactorService,
        login_completion_service: LoginCompletionService,
    ) -> None:
        super().__init__(db)
        self._hash_service: BaseHashService = hash_service
        self._token_service: JWTTokenService = token_service
        self._session_service: SessionService = session_service
        self._two_factor_service: TwoFactorService = two_factor_service
        self._login_completion: LoginCompletionService = (
            login_completion_service
        )

    def decode_token(self, token: str) -> dict[str, Any]:
        return self._token_service.decode_jwt_token(token)

    async def refresh_token(self, old_refresh_token: str) -> tuple[str, str]:
        """
        Выполняет ротацию токенов (Token Rotation).

        - Проверяет структуру и тип старого refresh-токена.
        - Ищет токен в базе данных и проверяет срок его действия.
        - Удаляет старый токен, генерирует и сохраняет новую пару токенов.
        - Сохраняет метаданные сессии (IP, User-Agent) при обновлении.

        Args:
            old_refresh_token (str): Текущий refresh-токен пользователя из кук.

        Raises:
            InvalidTokenError: Если токен невалиден или отсутствует в БД.
            TokenExpiredError: Если срок действия токена истек.

        Returns:
            tuple[str, str]: Кортеж из нового
            (access_token, new_refresh_token).
        """
        try:
            payload = self.decode_token(old_refresh_token)
        except (DecodeTokenException, TokenKeysException):
            raise
        if payload.get("type") != "refresh":
            raise TokenTypeExeption()
        sid = payload["sid"]
        try:
            await self._session_service.verify_session(sid, old_refresh_token)
        except TokenExeption:
            raise

        is_superuser = payload.get("is_superuser", False)
        user_id = UUID(payload["sub"])
        subscription_info = await self._login_completion.get_subscription_info(
            user_id
        )

        new_access_token, new_refresh_token = (
            self._token_service.create_access_and_refresh_tokens(
                {
                    "sub": str(payload["sub"]),
                    "is_superuser": is_superuser,
                    "sid": str(payload["sid"]),
                    **subscription_info,
                }
            )
        )

        await self._session_service.rotate_refresh_token(
            sid=sid,
            refresh_token=new_refresh_token,
        )

        return new_access_token, new_refresh_token

    async def authenticate_user(
        self, auth_user: UserRequestScheme, ip_address: str, user_agent: str
    ) -> tuple[str, str]:
        """
        Аутентифицирует пользователя по email и паролю.
        - Проверяет, существует ли пользователь.
        - Сравнивает хэшированный пароль с введённым.
        - В случае ошибок выбрасывает исключения.
        Args:
            auth_user (UserRequestScheme): Данные для входа (email и пароль).
            ip_address (str): IP-адрес клиента.
            user_agent (str): Строка User-Agent клиентского устройства.

        Raises:
            UserNotFoundException: Если пользователь с указанным email не найден.
            VerifyPasswordException: Если пароль введён неверно.
            TwoFactorRequiredException: Если у пользователя указан телефон и пароль верный,
                но вход завершится только после подтверждения кода.
        """
        user = await self._db.users.get_one_or_none_by_email_or_phone(
            email=auth_user.email, phone=auth_user.phone
        )
        if user is None:
            raise UserNotFoundException()
        if not user.is_active:
            raise UserNotFoundException()
        if not user.hashed_password:
            raise PasswordNotSetException()
        if not await self._hash_service.verify_password(
            auth_user.password, user.hashed_password
        ):
            raise VerifyPasswordException()

        if user.phone:
            await self._two_factor_service.send_code(user.id, user.phone)
            raise TwoFactorRequiredException()

        return await self._login_completion.create_session(
            user, ip_address, user_agent, auth_method="password"
        )

    async def verify_two_factor_login(
        self,
        email: str | None,
        phone: str | None,
        code: str,
        ip_address: str,
        user_agent: str,
    ) -> tuple[str, str]:
        """
        Завершает вход после подтверждения кода из authenticate_user.

        Args:
            email (str | None): Email, использованный на первом шаге логина.
            phone (str | None): Телефон, использованный на первом шаге логина.
            code (str): Код подтверждения из СМС.
            ip_address (str): IP-адрес клиента.
            user_agent (str): Строка User-Agent клиентского устройства.

        Raises:
            UserNotFoundException: Если пользователь не найден.
            InvalidTwoFactorCodeException: Если код неверный или истек.
            TooManyAttemptsException: Если исчерпан лимит попыток для текущего кода.
        """
        user = await self._db.users.get_one_or_none_by_email_or_phone(
            email=email, phone=phone
        )
        if user is None:
            raise UserNotFoundException()

        if not await self._two_factor_service.verify_code(user.id, code):
            raise InvalidTwoFactorCodeException()

        return await self._login_completion.create_session(
            user, ip_address, user_agent, auth_method="password+sms"
        )

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        try:
            payload = self.decode_token(refresh_token)
        except (DecodeTokenException, TokenKeysException):
            return
        sid = payload["sid"]
        await self._session_service.delete_session(sid)

    async def revoke_all_refresh_tokens(self, refresh_token: str) -> None:
        try:
            payload = self.decode_token(refresh_token)
        except (DecodeTokenException, TokenKeysException):
            return
        user_id = payload["sub"]
        await self._session_service.delete_all_sessions(user_id)
