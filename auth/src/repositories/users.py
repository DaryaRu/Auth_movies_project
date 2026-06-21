from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy import or_, select, update

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
    async def create_user(self, email: str | None, phone: str | None, hashed_password: str, is_superuser: bool = False) -> UserORM:
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
    async def get_one_or_none_by_email_or_phone(self, email: str | None, phone: str | None) -> UserORM | None:
        """
        Получает пользователя по email.
        Args:
            email (str): Электронная почта пользователя.
            phone (str): Телефон пользователя.
        Returns:
            Optional[User]: Пользователь или None, если не найден.
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

    @abstractmethod
    async def update_user_credentials(
        self,
        user_id: UUID,
        **kwargs
    ) -> UserORM:
        """
        Получает пользователя по его идентификатору.

        Args:
            id (UUID): Идентификатор пользователя.

        Returns:
            Optional[User]: Пользователь или None, если не найден.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id_for_update(self, user_id: UUID) -> UserORM | None:
        """Блокирует строку пользователя для UPDATE."""
        raise NotImplementedError


class UsersPostgreSQLRepository(UsersAbstractRepository, BasePostgreSQLRepository):
    """
    Репозиторий пользователей с использованием PostgreSQL и SQLAlchemy Async.
    """
    model = UserORM
    
    async def create_user(self, email: str | None, phone: str | None, hashed_password: str | None, is_superuser: bool = False) -> UserORM:
        return await self.add_one(email=email, hashed_password=hashed_password, is_superuser=is_superuser, phone=phone)

    async def get_one_or_none_by_email_or_phone(self, email: str | None, phone: str | None) -> UserORM | None:
        conditions = []
        if email:
            conditions.append(UserORM.email == email)
        if phone:
            conditions.append(UserORM.phone == phone)
        if not conditions:
            return None
        query = select(UserORM).where(or_(*conditions))
        result = await self._session.execute(query)
        return result.scalars().one_or_none()
    
    async def get_one_or_none_by_email(self, email: str) -> UserORM | None:
        return await self.get_one_or_none(email=email)
    
    async def get_one_or_none_by_id(self, id: UUID) -> UserORM | None:
        return await self.get_one_or_none(id=id)

    async def update_user_credentials(
            self,
            user_id: UUID,
            **kwargs
    ) -> UserORM:
        query = (
            update(self.model)
            .where(self.model.id == user_id)
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self._session.execute(query)
        return result.scalar_one()

    async def get_by_id_for_update(self, user_id: UUID) -> UserORM | None:
        stmt = (
            select(self.model)
            .where(self.model.id == user_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
