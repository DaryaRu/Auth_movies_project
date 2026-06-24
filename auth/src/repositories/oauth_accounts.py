from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy import delete, select

from src.models.oauth_accounts import OAuthAccountORM
from src.repositories.base import BasePostgreSQLRepository


class OAuthAccountsAbstractRepository(ABC):
    """
    Абстрактный репозиторий для работы с OAuth-аккаунтами.

    Определяет методы для:
    - получения аккаунта по провайдеру и идентификатору пользователя у провайдера;
    - создания нового OAuth-аккаунта;
    - получения всех аккаунтов пользователя;
    - получения аккаунта по пользователю и провайдеру;
    - удаления OAuth-аккаунта.
    """

    @abstractmethod
    async def get_by_provider_data(
        self, provider: str, provider_user_id: str
    ) -> OAuthAccountORM | None:
        """
        Возвращает OAuth-аккаунт по провайдеру и идентификатору у провайдера.

        Args:
            provider (str): Название провайдера (google, yandex, vk).
            provider_user_id (str): Идентификатор пользователя на стороне провайдера.

        Returns:
            OAuthAccountORM | None: Найденный аккаунт или None.
        """
        raise NotImplementedError

    @abstractmethod
    async def create_oauth_account(
        self, user_id: UUID, provider: str, provider_user_id: str
    ) -> OAuthAccountORM:
        """
        Создаёт новый OAuth-аккаунт и привязывает его к пользователю.

        Args:
            user_id (UUID): Идентификатор пользователя в системе.
            provider (str): Название провайдера (google, yandex, vk).
            provider_user_id (str): Идентификатор пользователя на стороне провайдера.

        Returns:
            OAuthAccountORM: Созданный OAuth-аккаунт.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all_by_user_id(self, user_id: UUID) -> list[OAuthAccountORM]:
        """
        Возвращает все привязанные соцсети пользователя.

        Args:
            user_id (UUID): Идентификатор пользователя в системе.

        Returns:
            list[OAuthAccountORM]: Список OAuth-аккаунтов пользователя.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_and_provider(
        self, user_id: UUID, provider: str
    ) -> OAuthAccountORM | None:
        """
        Находит конкретную соцсеть у определенного пользователя.

        Args:
            user_id (UUID): Идентификатор пользователя в системе.
            provider (str): Название провайдера (google, yandex, vk).

        Returns:
            OAuthAccountORM | None: Найденный аккаунт или None.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_oauth_account(self, account_id: UUID) -> None:
        """
        Удаляет запись OAuth-аккаунта из базы данных.

        Args:
            account_id (UUID): Идентификатор OAuth-аккаунта для удаления.
        """
        raise NotImplementedError


class OAuthAccountsPostgreSQLRepository(
    OAuthAccountsAbstractRepository, BasePostgreSQLRepository
):
    """Репозиторий OAuth-аккаунтов с использованием PostgreSQL и SQLAlchemy Async."""

    model = OAuthAccountORM

    async def get_by_provider_data(
        self, provider: str, provider_user_id: str
    ) -> OAuthAccountORM | None:
        return await self.get_one_or_none(
            provider=provider, provider_user_id=provider_user_id
        )

    async def create_oauth_account(
        self, user_id: UUID, provider: str, provider_user_id: str
    ) -> OAuthAccountORM:
        return await self.add_one(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
        )

    async def get_all_by_user_id(self, user_id: UUID) -> list[OAuthAccountORM]:
        stmt = select(self.model).where(self.model.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user_and_provider(
        self, user_id: UUID, provider: str
    ) -> OAuthAccountORM | None:
        return await self.get_one_or_none(user_id=user_id, provider=provider)

    async def delete_oauth_account(self, account_id: UUID) -> None:
        await self.delete_one(id=account_id)
