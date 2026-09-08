"""Сервис управления настройками уведомлений пользователя."""

from uuid import UUID

from src.models.user_notification_settings import UserNotificationSettingsORM
from src.schemas.user_notification_settings import NotificationSettingsUpdate
from src.services.base import BaseService


class UserNotificationSettingsService(BaseService):
    """
    Сервис для управления настройками уведомлений пользователя:
    - получение, создание, обновление настроек.
    """

    async def get_by_user_id(self, user_id: UUID) -> UserNotificationSettingsORM | None:
        """Получить настройки пользователя. Если записи нет — возвращает None."""
        return await self._db.user_notification_settings.get_by_user_id(user_id)

    async def update_or_create(
        self, user_id: UUID, data: NotificationSettingsUpdate
    ) -> UserNotificationSettingsORM:
        """Обновляет или создает настройки уведомлений пользователя."""
        update_data = data.model_dump(exclude_unset=True)

        return await self._db.user_notification_settings.upsert(
            user_id=user_id,
            notifications_enabled=update_data.get("notifications_enabled"),
            email_enabled=update_data.get("email_enabled"),
            sms_enabled=update_data.get("sms_enabled"),
            push_enabled=update_data.get("push_enabled"),
        )
