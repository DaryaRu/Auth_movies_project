"""API endpoints для управления настройками уведомлений пользователя."""

from fastapi import APIRouter, status

from src.api.v1.dependencies import (
    CurrentUserDep,
    UserNotificationSettingsServiceDep,
)
from src.core.notification_defaults import notification_defaults
from src.schemas.user_notification_settings import (
    NotificationSettingsUpdate,
    UserNotificationSettings,
)
from src.utils.notifications import invalidate_notification_settings_cache

router = APIRouter(prefix="/users/me/notification-settings", tags=["notification-settings"])


@router.get(
    "/",
    summary="Получить настройки уведомлений",
    response_model=UserNotificationSettings,
)
async def get_notification_settings(
    current_user: CurrentUserDep,
    user_notification_settings_service: UserNotificationSettingsServiceDep,
) -> UserNotificationSettings:
    """Получить настройки уведомлений для текущего пользователя.

    Если записи нет в БД — возвращает дефолтные значения (без создания записи).
    """
    settings = await user_notification_settings_service.get_by_user_id(
        current_user.id
    )
    if settings is None:
        return UserNotificationSettings(
            user_id=current_user.id,
            notifications_enabled=notification_defaults.NOTIFICATIONS_ENABLED,
            email_enabled=notification_defaults.EMAIL_ENABLED,
            sms_enabled=notification_defaults.SMS_ENABLED,
            push_enabled=notification_defaults.PUSH_ENABLED,
        )
    return UserNotificationSettings.model_validate(settings)


@router.patch(
    "/",
    summary="Обновить настройки уведомлений",
    response_model=UserNotificationSettings,
    responses={
        status.HTTP_201_CREATED: {"description": "Настройки созданы"},
        status.HTTP_200_OK: {"description": "Настройки обновлены"},
    },
)
async def update_notification_settings(
    current_user: CurrentUserDep,
    settings_update: NotificationSettingsUpdate,
    user_notification_settings_service: UserNotificationSettingsServiceDep,
) -> UserNotificationSettings:
    """Обновить или создать настройки уведомлений для текущего пользователя.

    Создает запись, если её еще нет.
    Инвалидирует Redis-кэш воркера для перезапроса настроек.
    """
    settings = await user_notification_settings_service.update_or_create(
        user_id=current_user.id,
        data=settings_update,
    )
    await invalidate_notification_settings_cache(current_user.id)
    return UserNotificationSettings.model_validate(settings)
