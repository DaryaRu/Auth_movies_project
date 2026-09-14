from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from src.exceptions import (
    DecodeTokenException,
    InvalidTwoFactorCodeException,
    LastAuthMethodRestrictionException,
    OAuthAccountNotLinkedException,
    PasswordNotSetException,
    ProviderException,
    TokenExeption,
    TokenKeysException,
    TokenTypeExeption,
    TwoFactorRequiredException,
    UserNotFoundException,
    VerifyPasswordException,
)
from src.models.users import UserORM
from src.schemas.oauth import OAuthUserInfoScheme
from src.schemas.users import (
    ChangeEmailRequestScheme,
    ChangePasswordRequestScheme,
    PhoneChangeConfirmScheme,
    PhoneChangeRequestScheme,
    SetPasswordRequestScheme,
    UserRequestScheme,
)
from src.services.account_delete import AccountDeleteService
from src.services.account_settings import AccountSettingsService
from src.services.base import BaseService
from src.services.phone_change import PhoneChangeService
from src.services.registration import RegistrationService
from src.services.sessions import SessionService
from src.services.two_factor import TwoFactorService
from src.utils.db_manager import DBManager
from src.utils.hashes import BaseHashService
from src.utils.tokens import JWTTokenService


class AuthService(BaseService):
    """
    Вход, токены, сессии, OAuth реализованы прямо здесь.
    Регистрация, изменение данных аккаунта и его удаление в RegistrationService,
    AccountSettingsService, AccountDeleteService.
    """

    def __init__(
        self,
        hash_service: BaseHashService,
        token_service: JWTTokenService,
        session_service: SessionService,
        db: DBManager,
        two_factor_service: TwoFactorService,
        phone_change_service: PhoneChangeService,
    ) -> None:
        super().__init__(db)
        self._hash_service: BaseHashService = hash_service
        self._token_service: JWTTokenService = token_service
        self._session_service: SessionService = session_service
        self._two_factor_service: TwoFactorService = two_factor_service

        self._registration = RegistrationService(hash_service, db)
        self._account_settings = AccountSettingsService(
            hash_service, db, session_service, phone_change_service
        )
        self._account_delete = AccountDeleteService(
            hash_service, db, session_service, two_factor_service
        )

    # Регистрация

    async def register_user(self, user: UserRequestScheme) -> UserORM:
        return await self._registration.register_user(user)

    async def confirm_email(self, user_id: UUID) -> UserORM:
        return await self._registration.confirm_email(user_id)

    async def create_admin(self, user: UserRequestScheme) -> None:
        await self._registration.create_admin(user)

    # Данные аккаунта

    async def change_user_email(
        self, user_id: UUID, data: ChangeEmailRequestScheme
    ) -> UserORM:
        return await self._account_settings.change_user_email(user_id, data)

    async def request_phone_change(
        self, user_id: UUID, data: PhoneChangeRequestScheme
    ) -> None:
        await self._account_settings.request_phone_change(user_id, data)

    async def confirm_phone_change(
        self, user_id: UUID, data: PhoneChangeConfirmScheme
    ) -> UserORM:
        return await self._account_settings.confirm_phone_change(user_id, data)

    async def change_user_password(
        self, user_id: UUID, data: ChangePasswordRequestScheme
    ) -> None:
        await self._account_settings.change_user_password(user_id, data)

    async def change_user_timezone(
        self, user_id: UUID, timezone_name: str
    ) -> UserORM:
        return await self._account_settings.change_user_timezone(
            user_id, timezone_name
        )

    async def set_password(
        self, user_id: UUID, data: SetPasswordRequestScheme
    ) -> None:
        await self._account_settings.set_password(user_id, data)

    # Удаление аккаунта

    async def request_account_delete(
        self, user: UserORM, password: str | None
    ) -> bool:
        return await self._account_delete.request_account_delete(
            user, password
        )

    async def confirm_account_delete(self, user_id: UUID, code: str) -> None:
        await self._account_delete.confirm_account_delete(user_id, code)

    # Вход, токены, сессии, OAuth

    async def _get_subscription_info(self, user_id: UUID) -> dict:
        """
        Возвращает код и уровень активной подписки пользователя для JWT-токена.
        Если подписка истекла — деактивирует её и возвращает дефолтные значения 'free'.
        Если активной подписки нет, возвращает дефолтные значения 'free'.

        Args:
            user_id (UUID): Идентификатор пользователя.
        """
        active = await self._db.user_subscriptions.get_active(user_id)
        if active is None:
            return {"subscription_code": "free", "subscription_level": 0}
        if active.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            await self._db.user_subscriptions.deactivate(active.id)
            return {"subscription_code": "free", "subscription_level": 0}
        return {
            "subscription_code": active.subscription.code,
            "subscription_level": active.subscription.level,
        }

    async def get_one_by_email(self, email: str) -> UserORM:
        """
        Получает пользователя по email.
        Args:
            email (str): Электронная почта пользователя.
        Returns:
            UserORM: Пользователь.
        """
        user = await self._db.users.get_one_or_none_by_email(email=email)
        if user is None:
            raise UserNotFoundException()
        return user

    async def get_one(self, id: UUID) -> UserORM:
        """
        Получает пользователя по id.
        Args:
            id (str): Идентификатор пользователя.
        Returns:
            UserORM: Пользователь.
        Raises:
            UserNotFoundException: Если пользователь с указанным id не найден.
        """
        user = await self._db.users.get_one_or_none_by_id(id=id)
        if user is None:
            raise UserNotFoundException()
        return user

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
        subscription_info = await self._get_subscription_info(user_id)

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
        if not self._hash_service.verify_password(
            auth_user.password, user.hashed_password
        ):
            raise VerifyPasswordException()

        if user.phone:
            await self._two_factor_service.send_code(user.id, user.phone)
            raise TwoFactorRequiredException()

        return await self._create_user_session(
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

        return await self._create_user_session(
            user, ip_address, user_agent, auth_method="password+sms"
        )

    async def _create_user_session(
        self,
        user: UserORM,
        ip_address: str,
        user_agent: str,
        auth_method: str,
    ) -> tuple[str, str]:
        sid = uuid4()

        subscription_info = await self._get_subscription_info(user.id)

        access_token, refresh_token = (
            self._token_service.create_access_and_refresh_tokens(
                {
                    "sub": str(user.id),
                    "is_superuser": user.is_superuser,
                    "sid": str(sid),
                    **subscription_info,
                }
            )
        )

        await self._session_service.add_session(
            user.id,
            user_agent,
            ip_address,
            refresh_token,
            sid,
            auth_method=auth_method,
        )

        return access_token, refresh_token

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

    async def _get_or_create_oauth_user(
        self,
        user_info: OAuthUserInfoScheme,
    ) -> UserORM:
        oauth_account = await self._db.oauth_accounts.get_by_provider_data(
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
        )

        if oauth_account:
            return await self.get_one(oauth_account.user_id)
        if not user_info.email and not user_info.phone:
            raise ProviderException()
        user = await self._db.users.get_one_or_none_by_email_or_phone(
            email=user_info.email, phone=user_info.phone
        )
        if not user:
            user = await self._db.users.create_user(
                email=user_info.email,
                phone=user_info.phone,
                hashed_password=None,
            )
            await self._registration.assign_free_subscription(user.id)

        await self._db.oauth_accounts.create_oauth_account(
            user_id=user.id,
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
        )
        return user

    async def authenticate_oauth_user(
        self, user_info: OAuthUserInfoScheme, ip_address: str, user_agent: str
    ) -> tuple[str, str]:
        user = await self._get_or_create_oauth_user(user_info)
        return await self._create_user_session(
            user, ip_address, user_agent, auth_method=user_info.provider
        )

    async def _delete_sessions_by_auth_method(
        self,
        user_id: UUID,
        auth_method: str,
        current_sid: str,
    ) -> bool:
        """Аннулирует в Redis все активные сессии пользователя,
        созданные через определенный метод входа."""
        sessions = await self._session_service.get_active_sessions(
            user_id=user_id, current_sid=current_sid
        )

        current_session_deleted = False

        for session_info in sessions:
            sid = (
                session_info.get("sid")
                if isinstance(session_info, dict)
                else getattr(session_info, "sid", None)
            )
            if not sid:
                continue

            full_session = await self._session_service.get_session(sid)
            if not full_session:
                continue

            session_auth_method = (
                full_session.get("auth_method")
                if isinstance(full_session, dict)
                else getattr(full_session, "auth_method", None)
            )

            if session_auth_method == auth_method:
                await self._session_service.delete_session(sid)
                if str(sid) == str(current_sid):
                    current_session_deleted = True

        return current_session_deleted

    async def unlink_account(
        self,
        user_id: UUID,
        provider: str,
        current_sid: str,
    ) -> tuple[list[str], bool]:
        """
        Отвязывает аккаунт внешнего провайдера
        от личного кабинета пользователя.

        Args:
            user_id (UUID): Идентификатор пользователя в системе.
            provider (str): Название провайдера (google, yandex, vk).
            current_sid (str): Идентификатор текущей активной сессии.

        Returns:
            tuple[list[str], bool]: Кортеж, содержащий:
                - list[str]: Список названий привязанных провайдеров.
                - bool: Флаг True, если текущая сессия была аннулирована.

        Raises:
            UserNotFoundException: Если пользователь не найден.
            OAuthAccountNotLinkedException: Если провайдер не привязан.
            LastAuthMethodRestrictionException: Если это единственный
            способ входа.
        """
        async with self._db as db:
            user = await db.users.get_by_id_for_update(user_id)
            if not user:
                raise UserNotFoundException()

            all_accounts = await db.oauth_accounts.get_all_by_user_id(user_id)

            target_account = next(
                (acc for acc in all_accounts if acc.provider == provider), None
            )
            if not target_account:
                raise OAuthAccountNotLinkedException()

            has_password = bool(user.hashed_password)
            remaining_oauth_count = len(all_accounts) - 1

            if not has_password and remaining_oauth_count == 0:
                raise LastAuthMethodRestrictionException()

            await db.oauth_accounts.delete_oauth_account(target_account.id)

            remaining_providers = [
                acc.provider
                for acc in all_accounts
                if acc.provider != provider
            ]

        current_session_deleted = await self._delete_sessions_by_auth_method(
            user_id=user_id,
            auth_method=provider,
            current_sid=current_sid,
        )

        return remaining_providers, current_session_deleted
