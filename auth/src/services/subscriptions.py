"""Сервис управления типами подписок."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from src.exceptions import (
    ObjectAlreadyexistsException,
    SubscriptionAlreadyExistsException,
    SubscriptionInUseException,
    SubscriptionLevelAlreadyExistsException,
    SubscriptionNotFoundException,
)
from src.models.subscriptions import SubscriptionORM
from src.schemas.subscriptions import (
    SubscriptionCreateScheme,
    SubscriptionUpdateScheme,
)
from src.services.base import BaseService


class SubscriptionService(BaseService):
    """
    Сервис для управления подписками:
    - создание, получение, обновление и удаление типов подписок;
    - назначение подписки пользователю, получение текущей и истории.
    """

    async def create_subscription(
        self, data: SubscriptionCreateScheme
    ) -> SubscriptionORM:
        """
        Создаёт новый тип подписки.

        Args:
            data (SubscriptionCreateScheme): Данные для создания.
        """
        existing = await self._db.subscriptions.get_one_or_none_by_code(
            data.code
        )
        if existing:
            raise SubscriptionAlreadyExistsException()
        existing_level = await self._db.subscriptions.get_one_or_none_by_level(
            data.level
        )
        if existing_level:
            raise SubscriptionLevelAlreadyExistsException()
        return await self._db.subscriptions.create_subscription(
            code=data.code,
            level=data.level,
            description=data.description,
            is_active=data.is_active,
        )

    async def get_subscription_by_id(
        self, subscription_id: UUID
    ) -> SubscriptionORM:
        """
        Возвращает тип подписки по идентификатору.

        Args:
            subscription_id (UUID): Идентификатор подписки.
        """
        subscription = await self._db.subscriptions.get_one_or_none_by_id(
            subscription_id
        )
        if subscription is None:
            raise SubscriptionNotFoundException()
        return subscription

    async def get_subscription_by_code(self, code: str) -> SubscriptionORM:
        """
        Возвращает тип подписки по коду.

        Args:
            code (str): Код подписки.
        """
        subscription = await self._db.subscriptions.get_one_or_none_by_code(
            code
        )
        if subscription is None:
            raise SubscriptionNotFoundException()
        return subscription

    async def get_all_subscriptions(self) -> list[SubscriptionORM]:
        """Возвращает все типы подписок."""
        return await self._db.subscriptions.get_all()

    async def get_active_subscriptions(self) -> list[SubscriptionORM]:
        """Возвращает только активные типы подписок."""
        return await self._db.subscriptions.get_all_active()

    async def update_subscription(
        self, subscription_id: UUID, data: SubscriptionUpdateScheme
    ) -> SubscriptionORM:
        """
        Обновляет поля типа подписки.

        Args:
            subscription_id (UUID): Идентификатор подписки.
            data (SubscriptionUpdateScheme): Данные для обновления.
        """
        await self.get_subscription_by_id(subscription_id)
        update_data = data.model_dump(exclude_unset=True)
        if "level" in update_data:
            existing_level = await self._db.subscriptions.get_one_or_none_by_level(
                update_data["level"]
            )
            if existing_level and existing_level.id != subscription_id:
                raise SubscriptionLevelAlreadyExistsException()
        try:
            return await self._db.subscriptions.update_subscription(
                id=subscription_id, **update_data
            )
        except ObjectAlreadyexistsException:
            raise SubscriptionAlreadyExistsException()

    async def delete_subscription(self, subscription_id: UUID) -> None:
        """
        Удаляет тип подписки.

        Args:
            subscription_id (UUID): Идентификатор подписки.
        """
        await self.get_subscription_by_id(subscription_id)
        try:
            await self._db.subscriptions.delete_subscription(subscription_id)
        except IntegrityError:
            raise SubscriptionInUseException()

