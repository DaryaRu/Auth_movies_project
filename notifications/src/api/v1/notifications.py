"""API endpoints для персональных уведомлений."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.repositories.templates import TemplateRepository
from src.schemas.notifications import NotificationCreate
from src.services.notifications import (
    InvalidPayloadError,
    NotificationService,
    TemplateNotFoundError,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service() -> NotificationService:
    """Получить сервис уведомлений."""
    return NotificationService(TemplateRepository())


NotificationServiceDep = Depends(get_notification_service)


@router.post(
    "/",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Создать персональное уведомление",
    description=(
        "Для случаев, когда получатель известен вызывающему сервису "
        "(например, лайк на рецензию). Публикуется в "
        "notification-ready."
    ),
)
async def create_notification(
    notification: NotificationCreate,
    notification_service: NotificationService = NotificationServiceDep,
) -> None:
    """Принять персональное уведомление и опубликовать его в Kafka."""
    try:
        await notification_service.create_notification(
            notification.user_id,
            notification.template_id,
            notification.payload,
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
