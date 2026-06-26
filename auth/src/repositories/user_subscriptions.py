"""Репозиторий подписок пользователей."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update

from src.models.user_subscriptions import UserSubscriptionORM
from src.repositories.base import BasePostgreSQLRepository


class UserSubscriptionsAbstractRepository(ABC):

    @abstractmethod
    async def create(
        self,
        user_id: UUID,
        subscription_id: UUID,
        started_at: datetime,
        expires_at: datetime,
    ) -> UserSubscriptionORM:
        raise NotImplementedError

    @abstractmethod
    async def get_active(self, user_id: UUID) -> UserSubscriptionORM | None:
        raise NotImplementedError

    @abstractmethod
    async def get_history(self, user_id: UUID) -> list[UserSubscriptionORM]:
        raise NotImplementedError

    @abstractmethod
    async def deactivate(self, id: UUID) -> None:
        raise NotImplementedError


class UserSubscriptionsPostgreSQLRepository(
    UserSubscriptionsAbstractRepository, BasePostgreSQLRepository
):
    model = UserSubscriptionORM

    async def create(
        self,
        user_id: UUID,
        subscription_id: UUID,
        started_at: datetime,
        expires_at: datetime,
    ) -> UserSubscriptionORM:
        return await self.add_one(
            user_id=user_id,
            subscription_id=subscription_id,
            started_at=started_at,
            expires_at=expires_at,
            is_active=True,
        )

    async def get_active(self, user_id: UUID) -> UserSubscriptionORM | None:
        query = select(self.model).where(
            self.model.user_id == user_id,
            self.model.is_active.is_(True),
        )
        result = await self._session.execute(query)
        return result.scalars().one_or_none()

    async def get_history(self, user_id: UUID) -> list[UserSubscriptionORM]:
        query = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(self.model.started_at.desc())
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def deactivate(self, id: UUID) -> None:
        query = (
            update(self.model)
            .where(self.model.id == id)
            .values(is_active=False)
        )
        await self._session.execute(query)
