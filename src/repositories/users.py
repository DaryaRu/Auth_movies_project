from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, update

from src.models.users import RefreshTokenORM, UserORM
from src.repositories.base import BasePostgreSQLRepository


class UsersAbstractRepository(ABC):
    """
    Абстрактный репозиторий для работы с пользователями.

    Определяет базовые методы для:
    - добавления пользователя,
    - получения пользователя по email.
    """

    @abstractmethod
    async def create_user(self, email: str, hashed_password: str, is_superuser: bool = False) -> UserORM:
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


class UsersPostgreSQLRepository(UsersAbstractRepository, BasePostgreSQLRepository):
    """
    Репозиторий пользователей с использованием PostgreSQL и SQLAlchemy Async.
    """
    model = UserORM
    
    async def create_user(self, email: str, hashed_password: str, is_superuser: bool = False) -> UserORM:
        return await self.add_one(email=email, hashed_password=hashed_password, is_superuser=is_superuser)

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


class RefreshTokensAbstractRepository(ABC):
    """
    Абстрактный репозиторий для работы с refresh-токенами.

    Определяет базовые методы для:
    - добавления токена с метаданными устройства,
    - получения токена,
    - удаления токена,
    - получения полной истории активных сессий пользователя.
    """

    @abstractmethod
    async def create_refresh_token(
        self,
        token: str,
        user_id: UUID,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RefreshTokenORM:
        """
        Добавляет новый refresh-токен со сведениями об IP и браузере.

        Args:
            token (str): Строковое значение токена.
            user_id (UUID): Идентификатор пользователя.
            expires_at (datetime): Дата и время истечения токена.
            ip_address (str | None): IP-адрес, с которого выполнен вход.
            user_agent (str | None): Информация об устройстве/браузере клиента.

        Returns:
            RefreshTokenORM: Созданный объект токена.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_token(
        self,
        token: str
    ) -> RefreshTokenORM | None:
        """
        Получает токен для проверки.

        Args:
            token (str): Строковое значение токена.

        Returns:
            Optional[RefreshTokenORM]: Объект токена или None, если не найден.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_refresh_token(self, token: str) -> None:
        """
        Удаляет токен из базы.

        Args:
            token (str): Строковое значение токена.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all_by_user_id(self, user_id: UUID) -> list[RefreshTokenORM]:
        """
        Получает все активные токены пользователя для истории сессий.

        Args:
            user_id (UUID): Идентификатор пользователя.

        Returns:
            list[RefreshTokenORM]: Список всех активных сессий пользователя.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_all_by_user_id(self, user_id: UUID) -> None:
        """Удаление всех refresh-токенов пользователя."""
        raise NotImplementedError


class RefreshTokenPostgreSQLRepository(
    RefreshTokensAbstractRepository,
    BasePostgreSQLRepository
):
    """
    Репозиторий для работы с refresh-токенами
    с использованием PostgreSQL и SQLAlchemy Async.
    """

    model = RefreshTokenORM

    async def create_refresh_token(
        self,
        token: str,
        user_id: UUID,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> RefreshTokenORM:
        return await self.add_one(
            token=token,
            user_id=user_id,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

    async def get_one_or_none_by_token(
            self,
            token: str
            ) -> RefreshTokenORM | None:
        return await self.get_one_or_none(token=token)

    async def delete_refresh_token(self, token: str) -> None:
        query = delete(self.model).where(self.model.token == token)
        await self._session.execute(query)

    async def get_all_by_user_id(self, user_id: UUID) -> list[RefreshTokenORM]:
        from sqlalchemy import select
        query = select(self.model).where(self.model.user_id == user_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def delete_all_by_user_id(self, user_id: UUID) -> None:
        query = delete(self.model).where(self.model.user_id == user_id)
        await self._session.execute(query)
