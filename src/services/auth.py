from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.exceptions import (
    UserAlreadyexistsException,
    UserNotFoundError,
    VerifyPasswordError,
    InvalidTokenError,
    TokenExpiredError,
)
from src.models.users import UserORM
from src.schemas.users import (
    UserRequestScheme,
    ChangeEmailRequestScheme,
    ChangePasswordRequestScheme
)
from src.services.base import BaseService
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
    def __init__(self, hash_service: BaseHashService,
                 token_service: JWTTokenService,
                 db: DBManager
                 ) -> None:
        super().__init__(db)
        self._hash_service: BaseHashService = hash_service
        self._token_service: JWTTokenService = token_service
        
    async def register_user(self, user: UserRequestScheme) -> UserORM:
        is_exsist_user = await self._db.users.get_one_or_none_by_email(user.email)
        if is_exsist_user:
            raise UserAlreadyexistsException()
        new_user = await self.add_one(user)
        return new_user
    
    async def create_admin(self, user: UserRequestScheme) -> None:
        is_exsist_user = await self._db.users.get_one_or_none_by_email(user.email)
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
            email=user.email,
            hashed_password=hash_password,
            is_superuser=is_superuser,
        )
        return new_user

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
            raise UserNotFoundError()
        return user

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
            UserNotFoundError: Если пользователь с указанным email не найден.
            VerifyPasswordError: Если пароль введён неверно.
        """
        user = await self.get_one_by_email(email=auth_user.email)
        if user is None:
            raise UserNotFoundError()
        if not self._hash_service.verify_password(
            auth_user.password, user.hashed_password
        ):
            raise VerifyPasswordError()
        access_token, refresh_token = (
            self._token_service.create_access_and_refresh_tokens(
                {"sub": str(user.id), "is_superuser": user.is_superuser}
            )
        )
        payload = self.decode_token(refresh_token)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        await self._db.refresh_tokens.create_refresh_token(
            token=refresh_token,
            user_id=user.id,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return access_token, refresh_token

    async def get_one(self, id: UUID) -> UserORM:
        """
        Получает пользователя по id.
        Args:
            id (str): Идентификатор пользователя.
        Returns:
            UserORM: Пользователь.
        Raises:
            UserNotFoundError: Если пользователь с указанным id не найден.
        """
        user = await self._db.users.get_one_or_none_by_id(id=id)
        if user is None:
            raise UserNotFoundError()
        return user

    def decode_token(self, token: str) -> dict[str, Any]:
        """Декодировать JWT токен."""
        return self._token_service.decode_jwt_token(token)

    async def refresh_tokens(self, old_refresh_token: str) -> tuple[str, str]:
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

            if payload.get("type") != "refresh":
                raise InvalidTokenError()

        except Exception:
            await self._db.refresh_tokens.delete_refresh_token(
                token=old_refresh_token
                )
            raise InvalidTokenError()

        db_token = await self._db.refresh_tokens.get_one_or_none_by_token(
            token=old_refresh_token
        )
        if not db_token:
            raise InvalidTokenError()

        if (
            db_token.expires_at.replace(tzinfo=None)
            < datetime.now(timezone.utc).replace(tzinfo=None)
        ):
            await self._db.refresh_tokens.delete_refresh_token(
                token=old_refresh_token
            )
            raise TokenExpiredError()

        is_superuser = payload.get("is_superuser", False)

        new_access_token, new_refresh_token = (
            self._token_service.create_access_and_refresh_tokens(
                {
                    "sub": str(db_token.user_id),
                    "is_superuser": is_superuser
                }
            )
        )

        new_payload = self.decode_token(new_refresh_token)
        new_expires_at = datetime.fromtimestamp(
            new_payload["exp"], tz=timezone.utc
            )

        await self._db.refresh_tokens.delete_refresh_token(
            token=old_refresh_token
            )
        await self._db.refresh_tokens.create_refresh_token(
            token=new_refresh_token,
            user_id=db_token.user_id,
            expires_at=new_expires_at,
            ip_address=getattr(db_token, "ip_address", None),
            user_agent=getattr(db_token, "user_agent", None),
        )

        return new_access_token, new_refresh_token

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        """
        Отзывает (удаляет) refresh-токен из базы данных.
        Используется при выходе пользователя из системы
        (logout) для инвалидации сессии.

        Args:
            refresh_token (str): Токен, который необходимо отозвать.
        """
        await self._db.refresh_tokens.delete_refresh_token(token=refresh_token)

    async def get_user_history(self, user_id: UUID) -> list[Any]:
        """
        Возвращает историю активных сессий (refresh-токенов) пользователя.
        Перед получением истории проверяет
        существование пользователя в системе.

        Args:
            user_id (UUID): Уникальный идентификатор пользователя.

        Returns:
            list[Any]: Список объектов активных сессий
            пользователя из базы данных.
        """
        await self.get_one(id=user_id)

        return await self._db.refresh_tokens.get_all_by_user_id(
            user_id=user_id
            )

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
            UserNotFoundError: Если пользователь не найден.
            UserAlreadyexistsException: Если новый email уже занят.
            VerifyPasswordError: Если пароль введен неверно.

        Returns:
            UserORM: Обновленный объект пользователя из базы данных.
        """
        user = await self._db.users.get_one_or_none_by_id(id=user_id)
        if not user:
            raise UserNotFoundError()

        email_exists = await self._db.users.get_one_or_none_by_email(
            data.new_email
            )
        if email_exists:
            raise UserAlreadyexistsException()

        if not self._hash_service.verify_password(
            data.password,
            user.hashed_password
        ):
            raise VerifyPasswordError()

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
            UserNotFoundError: Если пользователь не найден.
            VerifyPasswordError: Если текущий старый пароль введен неверно.
        """
        user = await self._db.users.get_one_or_none_by_id(id=user_id)
        if not user:
            raise UserNotFoundError()

        if not self._hash_service.verify_password(
            data.current_password,
            user.hashed_password
        ):
            raise VerifyPasswordError()

        new_hash = self._hash_service.create_hash_password(data.new_password)

        await self._db.users.update_user_credentials(
            user_id=user_id,
            hashed_password=new_hash
        )

        await self._db.refresh_tokens.delete_all_by_user_id(user_id=user_id)
