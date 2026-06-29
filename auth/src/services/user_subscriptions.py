"""Сервис управления подписками пользователей."""

from datetime import UTC, datetime
from uuid import UUID

from src.exceptions import (
    SubscriptionInactiveException,
    UserNotFoundException,
    UserSubscriptionNotFoundException,
)
from src.models.user_subscriptions import UserSubscriptionORM
from src.schemas.user_subscriptions import UserSubscriptionCreateScheme
from src.services.base import BaseService
from src.services.subscriptions import SubscriptionService


class UserSubscriptionService(BaseService):
    """
    Сервис для управления подписками пользователей:
    - назначение подписки, получение текущей, истории, отмена.
    """

    async def assign_subscription(
        self, user_id: UUID, data: UserSubscriptionCreateScheme
    ) -> UserSubscriptionORM:
        """
        Назначает подписку пользователю. Если есть активная, то она деактивируется.

        Args:
            user_id (UUID): Идентификатор пользователя.
            data (UserSubscriptionCreateScheme): Код подписки и дата окончания.
        """
        user = await self._db.users.get_one_or_none_by_id(user_id)
        if user is None:
            raise UserNotFoundException()

        subscription_service = SubscriptionService(self._db)
        subscription = await subscription_service.get_subscription_by_code(
            data.subscription_code
        )
        if not subscription.is_active:
            raise SubscriptionInactiveException()

        current = await self._db.user_subscriptions.get_active(user_id)
        if current is not None:
            await self._db.user_subscriptions.deactivate(current.id)

        started_at = datetime.now(UTC)
        expires_at = datetime(
            data.expires_at.year,
            data.expires_at.month,
            data.expires_at.day,
            tzinfo=UTC,
        )

        return await self._db.user_subscriptions.create(
            user_id=user_id,
            subscription_id=subscription.id,
            started_at=started_at,
            expires_at=expires_at,
        )

    async def get_active_subscription(
        self, user_id: UUID
    ) -> UserSubscriptionORM | None:
        """
        Возвращает активную подписку пользователя или None, если её нет.

        Args:
            user_id (UUID): Идентификатор пользователя.
        """
        return await self._db.user_subscriptions.get_active(user_id)

    async def get_subscription_history(
        self, user_id: UUID
    ) -> list[UserSubscriptionORM]:
        """
        Возвращает историю подписок пользователя, новые первые.

        Args:
            user_id (UUID): Идентификатор пользователя.
        """
        return await self._db.user_subscriptions.get_history(user_id)

    async def cancel_subscription(self, user_id: UUID) -> None:
        """
        Досрочно отменяет активную подписку пользователя.
        Выбрасывает исключение, если активной подписки нет.

        Args:
            user_id (UUID): Идентификатор пользователя.
        """
        current = await self._db.user_subscriptions.get_active(user_id)
        if current is None:
            raise UserSubscriptionNotFoundException()
        await self._db.user_subscriptions.deactivate(current.id)
