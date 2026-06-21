from typing import Any
from uuid import UUID, uuid4

from src.exceptions import (
    DecodeTokenException,
    LastAuthMethodRestrictionException,
    OAuthAccountNotLinkedException,
    PasswordAlreadySetException,
    PasswordNotSetException,
    ProviderException,
    TokenExeption,
    TokenKeysException,
    TokenTypeExeption,
    UserAlreadyexistsException,
    UserNotFoundException,
    VerifyPasswordException,
)
from src.models.users import UserORM
from src.schemas.oauth import OAuthUserInfoScheme
from src.schemas.users import (
    ChangeEmailRequestScheme,
    ChangePasswordRequestScheme,
    SetPasswordRequestScheme,
    UserRequestScheme,
)
from src.services.base import BaseService
from src.services.sessions import SessionService
from src.utils.db_manager import DBManager
from src.utils.hashes import BaseHashService
from src.utils.tokens import JWTTokenService


class AuthService(BaseService):
    """
    Сервис для работы с пользователями.
    Инкапсулирует бизнес-логику, связанную с пользователями:
    - добавление нового пользователя с хэшированием пароля;
    - поиск пользователя по email;
    - аутентификация пользователя.
    """
    def __init__(
        self,
        hash_service: BaseHashService,
        token_service: JWTTokenService,
        session_service: SessionService,
        db: DBManager
    ) -> None:
        super().__init__(db)
        self._hash_service: BaseHashService = hash_service
        self._token_service: JWTTokenService = token_service
        self._session_service: SessionService = session_service
        
    async def register_user(self, user: UserRequestScheme) -> UserORM:
        is_exsist_user = await self._db.users.get_one_or_none_by_email_or_phone(user.email, user.phone)
        if is_exsist_user:
            raise UserAlreadyexistsException()
        new_user = await self.add_one(user)
        return new_user
    
    async def create_admin(self, user: UserRequestScheme) -> None:
        is_exsist_user = await self._db.users.get_one_or_none_by_email_or_phone(user.email, user.phone)
        if is_exsist_user:
            raise UserAlreadyexistsException()
        await self.add_one(user, is_superuser=True)

    async def add_one(self, user: UserRequestScheme, is_superuser: bool = False) -> UserORM:
        """
        Добавляет нового пользователя.
        - Пароль пользователя хэшируется.
        - Оригинальный пароль удаляется перед сохранением.
        - Пользователь сохраняется в БД.
        Args:
            user (UserRequestScheme): Данные пользователя.
        Returns:
            UserORM: Пользователь.
        """
        hash_password = self._hash_service.create_hash_password(
            user.password
        )
        new_user = await self._db.users.create_user(
            phone=user.phone,
            email=user.email,
            hashed_password=hash_password,
            is_superuser=is_superuser,
        )
        return new_user

    async def _get_permission_codes(self, user_id: UUID) -> list[str]:
        permissions = await self._db.roles.get_user_permissions(user_id)
        return [p.code for p in permissions]

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
        permission_codes = await self._get_permission_codes(UUID(payload["sub"]))

        new_access_token, new_refresh_token = (
            self._token_service.create_access_and_refresh_tokens(
                {
                    "sub": str(payload["sub"]),
                    "is_superuser": is_superuser,
                    "sid": str(payload["sid"]),
                    "permissions": permission_codes,
                }
            )
        )
        
        await self._session_service.rotate_refresh_token(
            sid=sid,
            refresh_token=new_refresh_token,
        )

        return new_access_token, new_refresh_token

    async def change_user_email(
        self, user_id: UUID, data: ChangeEmailRequestScheme
    ) -> UserORM:
        """
        Смена email пользователя после проверки пароля.
        Проверяет существование пользователя, уникальность нового email
        и корректность текущего пароля.

        Args:
            user_id (UUID): Уникальный идентификатор пользователя.
            data (ChangeEmailRequestScheme): Данные для смены email.

        Raises:
            UserNotFoundException: Если пользователь не найден.
            UserAlreadyexistsException: Если новый email уже занят.
            VerifyPasswordError: Если пароль введен неверно.

        Returns:
            UserORM: Обновленный объект пользователя из базы данных.
        """
        user = await self._db.users.get_one_or_none_by_id(id=user_id)
        if not user:
            raise UserNotFoundException()

        email_exists = await self._db.users.get_one_or_none_by_email(
            data.new_email
        )
        if email_exists:
            raise UserAlreadyexistsException()

        if not self._hash_service.verify_password(
            data.password,
            user.hashed_password
        ):
            raise VerifyPasswordException()

        updated_user = await self._db.users.update_user_credentials(
            user_id=user_id,
            email=data.new_email
        )
        return updated_user

    async def change_user_password(
        self, user_id: UUID, data: ChangePasswordRequestScheme
    ) -> None:
        """
        Смена пароля пользователя и отзыв всех его текущих сессий.
        Проверяет существование пользователя, корректность старого пароля,
        после чего хэширует новый пароль и удаляет все токены.

        Args:
            user_id (UUID): Уникальный идентификатор пользователя.
            data (ChangePasswordRequestScheme): Данные для смены пароля.

        Raises:
            UserNotFoundException: Если пользователь не найден.
            VerifyPasswordException: Если текущий старый пароль введен неверно.
        """
        user = await self._db.users.get_one_or_none_by_id(id=user_id)
        if not user:
            raise UserNotFoundException()

        if not self._hash_service.verify_password(
            data.current_password,
            user.hashed_password
        ):
            raise VerifyPasswordException()

        new_hash = self._hash_service.create_hash_password(data.new_password)

        await self._db.users.update_user_credentials(
            user_id=user_id,
            hashed_password=new_hash
        )

        await self._session_service.delete_all_sessions(str(user_id))

    async def authenticate_user(
            self,
            auth_user: UserRequestScheme,
            ip_address: str,
            user_agent: str
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
        """
        user = await self._db.users.get_one_or_none_by_email_or_phone(email=auth_user.email, phone=auth_user.phone)
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
        return await self._create_user_session(
            user,
            ip_address,
            user_agent,
            auth_method="password"
        )
    
    async def _create_user_session(
        self,
        user: UserORM,
        ip_address: str,
        user_agent: str,
        auth_method: str,
    ) -> tuple[str, str]:
        sid = uuid4()

        permission_codes = await self._get_permission_codes(user.id)

        access_token, refresh_token = (
            self._token_service.create_access_and_refresh_tokens(
                {
                    "sub": str(user.id),
                    "is_superuser": user.is_superuser,
                    "sid": str(sid),
                    "permissions": permission_codes,
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
            return await self.get_one(
                oauth_account.user_id
            )
        if not user_info.email and not user_info.phone:
            raise ProviderException()
        user = await self._db.users.get_one_or_none_by_email_or_phone(email=user_info.email, phone=user_info.phone)
        if not user:
            user = await self._db.users.create_user(
                email=user_info.email,
                phone=user_info.phone,
                hashed_password=None,
            )
            
        await self._db.oauth_accounts.create_oauth_account(
            user_id=user.id,
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
        )
        return user
    
    async def authenticate_oauth_user(
            self,
            user_info: OAuthUserInfoScheme,
            ip_address: str,
            user_agent: str
    ) -> tuple[str, str]:
        user = await self._get_or_create_oauth_user(user_info)
        return await self._create_user_session(
            user,
            ip_address,
            user_agent,
            auth_method=user_info.provider
        )
        
    async def set_password(self, user_id: UUID, data: SetPasswordRequestScheme) -> None:
        """Устанавливает пароль для OAuth-пользователя без пароля.

        Raises:
            UserNotFoundException: Если пользователь не найден.
            PasswordAlreadySetException: Если пароль уже установлен (использовать change-password).
        """
        user = await self._db.users.get_one_or_none_by_id(id=user_id)
        if not user:
            raise UserNotFoundException()

        if user.hashed_password is not None:
            raise PasswordAlreadySetException()

        new_hash = self._hash_service.create_hash_password(data.password)
        await self._db.users.update_user_credentials(
            user_id=user_id,
            hashed_password=new_hash,
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
            user_id=user_id,
            current_sid=None
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

            session_auth_method = full_session.get("auth_method") if isinstance(full_session, dict) else getattr(full_session, "auth_method", None)

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
    ) -> tuple[list[str], str | None, bool]:
        """
        Отвязывает аккаунт внешнего провайдера
        от личного кабинета пользователя.

        Выполняет комплексную проверку:
        - Запрет удаления единственного способа входа
        - Каскадное удаление связи в базе данных
        - Возврат access_token для фонового отзыва

        Args:
            user_id (UUID): Идентификатор пользователя в системе.
            provider (str): Название провайдера (google, yandex, vk).
            current_sid (str): Идентификатор текущей активной сессии.

        Returns:
            tuple[list[str], str | None, bool]: Кортеж, содержащий:
                - list[str]: Список названий привязанных провайдеров.
                - str | None: Access_token для отзыва (если есть).
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
                (acc for acc in all_accounts if acc.provider == provider),
                None
            )
            if not target_account:
                raise OAuthAccountNotLinkedException()

            has_password = bool(user.hashed_password)
            remaining_oauth_count = len(all_accounts) - 1

            if not has_password and remaining_oauth_count == 0:
                raise LastAuthMethodRestrictionException()

            access_token = getattr(target_account, "access_token", None)

            await db.oauth_accounts.delete_oauth_account(target_account.id)

            remaining_providers = [
                acc.provider for acc in all_accounts
                if acc.provider != provider
            ]

        current_session_deleted = await self._delete_sessions_by_auth_method(
            user_id=user_id,
            auth_method=provider,
            current_sid=current_sid,
        )

        return remaining_providers, access_token, current_session_deleted
