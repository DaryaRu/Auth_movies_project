"""Эндпоинты для триггеров уведомлений (Scheduled group)."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.repositories.notification_triggers import (
    NotificationTriggerRepository,
)
from src.repositories.templates import TemplateRepository
from src.schemas.triggers import NotificationTrigger, NotificationTriggerUpsert
from src.services.notifications import (
    InvalidPayloadError,
    TemplateNotFoundError,
)
from src.services.triggers import NotificationTriggerService

router = APIRouter(
    prefix="/notification-triggers", tags=["notification-triggers"]
)


def get_trigger_service() -> NotificationTriggerService:
    """Получить сервис триггеров уведомлений."""
    return NotificationTriggerService(
        NotificationTriggerRepository(), TemplateRepository()
    )


NotificationTriggerServiceDep = Depends(get_trigger_service)


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Upsert триггера уведомления",
    description=(
        "Для событий с множеством получателей, "
        "(например, вышла новая серия сериала). Публикует не готовое "
        "уведомление, а факт изменения (обновляет last_update). Реальная "
        "отправка произойдет, когда триггер проверит шедулер."
    ),
)
async def upsert_trigger(
    trigger: NotificationTriggerUpsert,
    trigger_service: NotificationTriggerService = NotificationTriggerServiceDep,
) -> NotificationTrigger:
    """Создать или обновить триггер уведомления по (content_id, notification_type)."""
    try:
        return await trigger_service.upsert(
            trigger.content_id,
            trigger.notification_type,
            trigger.template_id,
            trigger.payload,
        )
    except TemplateNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {e} not found or inactive",
        ) from e
    except InvalidPayloadError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"payload contains keys not allowed by template: {sorted(e.unknown_keys)}",
        ) from e
