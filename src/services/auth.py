from typing import Any
from uuid import UUID

from src.exceptions import UserAlreadyexistsException, UserNotFoundError, VerifyPasswordError
from src.schemas.users import UserRequestScheme
from src.services.base import BaseService
from src.models.users import UserORM
from src.utils.db_manager import DBManager
from src.utils.tokens import JWTTokenService
from src.utils.hashes import BaseHashService


class AuthService(BaseService):
    """
    Сервис для работы с пользователями.
    Инкапсулирует бизнес-логику, связанную с пользователями:
    - добавление нового пользователя с хэшированием пароля;
    - поиск пользователя по email;
    - аутентификация пользователя.
    """
    def __init__(self, hash_service: BaseHashService, token_service: JWTTokenService, db: DBManager) -> None:
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
        await self.add_one(user, is_staff=True)

    async def add_one(self, user: UserRequestScheme, is_staff: bool = False) -> UserORM:
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
        new_user = await self._db.users.create_user(email=user.email, hashed_password=hash_password, is_staff=is_staff)
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

    async def authenticate_user(self, auth_user: UserRequestScheme) -> tuple[str, str]:
        """
        Аутентифицирует пользователя по email и паролю.
        - Проверяет, существует ли пользователь.
        - Сравнивает хэшированный пароль с введённым.
        - В случае ошибок выбрасывает исключения.
        Args:
            auth_user (UserRequestScheme): Данные для входа (email и пароль).
        Returns:
            tuple[str, str]: Токены доступа.
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
        access_token, refresh_token = self._token_service.create_access_and_refresh_tokens(
            {"sub": str(user.id)}
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
        return self._token_service.decode_jwt_token(token)
