"""Внутренние эндпоинты, вызываемые другими сервисами."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.api.v1.dependencies import DBDep, InternalServiceDep, get_db_manager
from src.core.config import settings
from src.core.limiter import limiter
from src.core.notification_defaults import notification_defaults
from src.exceptions import UserNotFoundHTTPException
from src.schemas.user_notification_settings import UserNotificationSettings
from src.schemas.users import (
    UserContactScheme,
    UserIdsRequest,
    UserSearchScheme,
)
from src.utils.db_manager import DBManager

router = APIRouter(tags=["Internal"])


@router.get(
    "/internal/users/{user_id}/",
    summary="Email пользователя по ID",
    response_model=UserContactScheme,
)
async def get_user_contact(user_id: UUID, db: DBDep, _: InternalServiceDep):
    """Получение контактов пользователя между сервисами."""
    user = await db.users.get_one_or_none_by_id(id=user_id)
    if user is None:
        raise UserNotFoundHTTPException()
    return UserContactScheme(user_id=user.id, email=user.email)


@router.get(
    "/internal/users/{user_id}/notification-settings",
    summary="Настройки уведомлений пользователя по ID",
    response_model=UserNotificationSettings,
)
async def get_user_notification_settings(
    user_id: UUID,
    db: DBDep,
    _: InternalServiceDep,
):
    """Получение настроек уведомлений пользователя между сервисами.

    Если у пользователя нет записи в user_notification_settings,
    возвращается объект с дефолтными значениями из notification_defaults."""
    user = await db.users.get_one_or_none_by_id(id=user_id)
    if user is None:
        raise UserNotFoundHTTPException()

    notif_settings = await db.user_notification_settings.get_by_user_id(
        user_id
    )
    if notif_settings is None:
        # Нет записи в БД — возвращаем дефолты
        return UserNotificationSettings(
            user_id=user_id,
            notifications_enabled=notification_defaults.NOTIFICATIONS_ENABLED,
            email_enabled=notification_defaults.EMAIL_ENABLED,
            sms_enabled=notification_defaults.SMS_ENABLED,
            push_enabled=notification_defaults.PUSH_ENABLED,
        )
    return UserNotificationSettings.model_validate(notif_settings)


@router.post(
    "/internal/users/search/",
    summary="Поиск пользователей по audience_filter (для рассылок)",
    response_model=list[UUID],
)
async def search_users(
    data: UserSearchScheme, db: DBDep, _: InternalServiceDep
):
    """Используется notifications-service (воркер). Возвращает id активных пользователей,
    подходящих под фильтр."""
    min_level = (
        data.subscription_level.gte
        if data.subscription_level is not None
        else None
    )
    return await db.users.search_by_min_subscription_level(
        min_level, timezone_filter=data.timezone
    )


@router.post(
    "/internal/users/search/timezones/",
    summary="Уникальные таймзоны пользователей (для рассылок)",
    response_model=list[str],
)
async def search_user_timezones(
    data: UserSearchScheme, db: DBDep, _: InternalServiceDep
):
    """Используется notifications-service для разбивки рассылок по таймзонам.
    Возвращает уникальные таймзоны активных пользователей.
    Пользователи без заданной таймзоны считаются 'UTC'."""
    min_level = (
        data.subscription_level.gte
        if data.subscription_level is not None
        else None
    )
    return await db.users.search_distinct_timezones(
        min_level, timezone_filter=data.timezone
    )


@router.post(
    "/internal/users/names",
    response_model=dict[str, dict[str, str | None]],
    summary="Пакетное получение имён пользователей",
    description="""Внутренний endpoint для user_actions-сервиса.
    Получает snapshot full_name и nickname для списка пользователей.
    Используется при создании рецензии для сохранения имени автора.
    """,
)
@limiter.limit(settings.LIMIT_VALUE)
async def get_users_names_batch(
    request: Request,
    body: UserIdsRequest,
    _: InternalServiceDep,
    db: DBManager = Depends(get_db_manager),
) -> dict[str, dict[str, str | None]]:
    """Возвращает dict: {str(user_id): {"full_name": ..., "nickname": ...}}."""
    async with db:
        result = await db.users.get_users_name_snapshots(body.user_ids)

    return {str(uid): data for uid, data in result.items()}