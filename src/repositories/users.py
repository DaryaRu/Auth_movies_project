from abc import ABC, abstractmethod
from uuid import UUID

from src.models.users import UserORM
from src.repositories.base import BasePostgreSQLRepository


class UsersAbstractRepository(ABC):
    """
    Абстрактный репозиторий для работы с пользователями.

    Определяет базовые методы для:
    - добавления пользователя,
    - получения пользователя по email.
    """

    @abstractmethod
    async def create_user(self, email: str, hashed_password: str, is_staff: bool = False) -> UserORM:
        """
        Добавляет нового пользователя.
        Args:
            email (str): Электронная почта пользователя.
            hashed_password (str): Хэшированный пароль
            is_staff (bool): Есть ли права суперпользователя
        Returns:
            User: Созданный пользователь.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_email(self, email: str) -> UserORM | None:
        """
        Получает пользователя по email.
        Args:
            email (str): Электронная почта пользователя.
        Returns:
            Optional[User]: Пользователь или None, если не найден.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_id(self, id: UUID) -> UserORM | None:
        """
        Получает пользователя по его идентификатору.
        Args:
            id (UUID): Идентификатор пользователя.
        Returns:
            Optional[User]: Пользователь или None, если не найден.
        """
        raise NotImplementedError


class UsersPostgreSQLRepository(UsersAbstractRepository, BasePostgreSQLRepository):
    """
    Репозиторий пользователей с использованием PostgreSQL и SQLAlchemy Async.
    """
    model = UserORM
    
    async def create_user(self, email: str, hashed_password: str, is_staff: bool = False) -> UserORM:
        return await self.add_one(email=email, hashed_password=hashed_password, is_staff=is_staff)

    async def get_one_or_none_by_email(self, email: str) -> UserORM | None:
        return await self.get_one_or_none(email=email)
    
    async def get_one_or_none_by_id(self, id: UUID) -> UserORM | None:
        return await self.get_one_or_none(id=id)
    