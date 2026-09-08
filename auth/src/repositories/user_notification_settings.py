"""Репозиторий для настроек уведомлений пользователя."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.core.notification_defaults import notification_defaults
from src.models.user_notification_settings import UserNotificationSettingsORM
from src.repositories.base import BasePostgreSQLRepository

_NOTIFICATION_FIELDS: dict[str, bool] = {
    "notifications_enabled": notification_defaults.NOTIFICATIONS_ENABLED,
    "email_enabled": notification_defaults.EMAIL_ENABLED,
    "sms_enabled": notification_defaults.SMS_ENABLED,
    "push_enabled": notification_defaults.PUSH_ENABLED,
}


class UserNotificationSettingsRepository(BasePostgreSQLRepository):
    """Репозиторий для user_notification_settings."""

    async def get_by_user_id(self, user_id: UUID) -> UserNotificationSettingsORM | None:
        """Получить настройки пользователя для уведомлений из БД."""
        stmt = select(UserNotificationSettingsORM).where(
            UserNotificationSettingsORM.user_id == user_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _build_insert_data(
        user_id: UUID,
        notifications_enabled: bool | None,
        email_enabled: bool | None,
        sms_enabled: bool | None,
        push_enabled: bool | None,
    ) -> dict:
        """Собрать данные для INSERT: переданные значения или дефолты."""
        provided = {
            "notifications_enabled": notifications_enabled,
            "email_enabled": email_enabled,
            "sms_enabled": sms_enabled,
            "push_enabled": push_enabled,
        }
        return {
            "user_id": user_id,
            **{k: provided[k] if provided[k] is not None else default for k, default in _NOTIFICATION_FIELDS.items()},
        }

    @staticmethod
    def _build_set_data(
        notifications_enabled: bool | None,
        email_enabled: bool | None,
        sms_enabled: bool | None,
        push_enabled: bool | None,
    ) -> dict:
        """Собрать данные для UPDATE: только явно переданные (не None)."""
        provided = {
            "notifications_enabled": notifications_enabled,
            "email_enabled": email_enabled,
            "sms_enabled": sms_enabled,
            "push_enabled": push_enabled,
        }
        return {k: v for k, v in provided.items() if v is not None}

    async def upsert(
        self,
        user_id: UUID,
        notifications_enabled: bool | None = None,
        email_enabled: bool | None = None,
        sms_enabled: bool | None = None,
        push_enabled: bool | None = None,
    ) -> UserNotificationSettingsORM:
        """Создать или обновить настройки пользователя (идемпотентно через ON CONFLICT).

        При UPDATE меняются ТОЛЬКО явно переданные поля (не None).
        Остальные поля сохраняют свои текущие значения в БД.
        При INSERT используются дефолтные значения для отсутствующих полей.
        """
        insert_data = self._build_insert_data(
            user_id, notifications_enabled, email_enabled, sms_enabled, push_enabled
        )
        set_data = self._build_set_data(
            notifications_enabled, email_enabled, sms_enabled, push_enabled
        )

        if set_data:
            upsert_stmt = (
                pg_insert(UserNotificationSettingsORM)
                .values(**insert_data)
                .on_conflict_do_update(
                    constraint="user_notification_settings_user_id_key",
                    set_=set_data,
                )
                .returning(UserNotificationSettingsORM)
            )
        else:
            upsert_stmt = (
                pg_insert(UserNotificationSettingsORM)
                .values(**insert_data)
                .on_conflict_do_nothing()
                .returning(UserNotificationSettingsORM)
            )

        result = await self._session.execute(upsert_stmt)
        await self._session.flush()

        row = result.scalar_one_or_none()
        if row is None:
            return await self.get_by_user_id(user_id)
        return row
