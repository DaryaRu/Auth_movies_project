"""Репозиторий типов подписок."""

from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy import select

from src.models import SubscriptionORM
from src.repositories.base import BasePostgreSQLRepository


class SubscriptionsAbstractRepository(ABC):
    """Абстрактный репозиторий для работы с подписками."""

    @abstractmethod
    async def create_subscription(
        self, code: str, level: int, description: str | None, is_active: bool = True
    ) -> SubscriptionORM:
        """
        Создание новой подписки.

        Args:
            code: Уникальный код подписки, например, "free", "base", "premium".
            level: Числовое значение для сравнения доступа.
            description: Описание подписки, необязательно.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_id(self, id: UUID) -> SubscriptionORM | None:
        """
        Возврат подписки по идентификатору.

        Args:
            id: UUID подписки.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_code(
        self, code: str
    ) -> SubscriptionORM | None:
        """
        Возврат подписки по коду.

        Args:
            code: Уникальный код подписки.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_level(
        self, level: int
    ) -> SubscriptionORM | None:
        raise NotImplementedError

    @abstractmethod
    async def get_all(self) -> list[SubscriptionORM]:
        """
        Возврат всех подписок.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all_active(self) -> list[SubscriptionORM]:
        """
        Возврат только активных подписок.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_subscription(self, id: UUID, **kwargs) -> SubscriptionORM:
        """
        Обновление полей подписки.

        Args:
            id: UUID подписки.
            **kwargs: Поля для обновления.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_subscription(self, id: UUID) -> None:
        """
        Удалить подписку по идентификатору.

        Args:
            id: UUID подписки.
        """
        raise NotImplementedError


class SubscriptionsPostgreSQLRepository(
    SubscriptionsAbstractRepository, BasePostgreSQLRepository
):
    """Репозиторий подписок на основе PostgreSQL и SQLAlchemy Async."""

    model = SubscriptionORM

    async def create_subscription(
        self,
        code: str,
        level: int,
        description: str | None = None,
        is_active: bool = True,
    ) -> SubscriptionORM:
        return await self.add_one(
            code=code, level=level, description=description, is_active=is_active
        )

    async def get_one_or_none_by_id(self, id: UUID) -> SubscriptionORM | None:
        return await self.get_one_or_none(id=id)

    async def get_one_or_none_by_code(
        self, code: str
    ) -> SubscriptionORM | None:
        return await self.get_one_or_none(code=code)

    async def get_one_or_none_by_level(
        self, level: int
    ) -> SubscriptionORM | None:
        return await self.get_one_or_none(level=level)

    async def get_all(self) -> list[SubscriptionORM]:
        return list(await BasePostgreSQLRepository.get_all(self))

    async def get_all_active(self) -> list[SubscriptionORM]:
        query = select(self.model).where(SubscriptionORM.is_active.is_(True))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def update_subscription(self, id: UUID, **kwargs) -> SubscriptionORM:
        return await self.update_one(id=id, **kwargs)

    async def delete_subscription(self, id: UUID) -> None:
        await self.delete_one(id=id)
