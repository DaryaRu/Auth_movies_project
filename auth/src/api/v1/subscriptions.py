from uuid import UUID

from fastapi import APIRouter, status

from src.api.v1.dependencies import StaffUserDep, SubscriptionServiceDep
from src.exceptions import (
    SubscriptionAlreadyExistsException,
    SubscriptionAlreadyExistsHTTPException,
    SubscriptionInUseException,
    SubscriptionInUseHTTPException,
    SubscriptionNotFoundException,
    SubscriptionNotFoundHTTPException,
)
from src.schemas.subscriptions import (
    SubscriptionCreateScheme,
    SubscriptionResponseScheme,
    SubscriptionUpdateScheme,
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Создать тип подписки",
)
async def create_subscription(
    data: SubscriptionCreateScheme,
    subscription_service: SubscriptionServiceDep,
    staff_user: StaffUserDep,
) -> SubscriptionResponseScheme:
    """Создаёт новый тип подписки. Доступно только суперпользователям."""
    try:
        return await subscription_service.create_subscription(data)
    except SubscriptionAlreadyExistsException as exc:
        raise SubscriptionAlreadyExistsHTTPException(detail=exc.detail)


@router.get(
    "/",
    summary="Список типов подписок",
)
async def get_all_subscriptions(
    subscription_service: SubscriptionServiceDep,
    staff_user: StaffUserDep,
) -> list[SubscriptionResponseScheme]:
    """Возвращает все типы подписок. Доступно только суперпользователям."""
    return await subscription_service.get_all_subscriptions()


@router.get(
    "/{subscription_id}/",
    summary="Информация о типе подписки",
)
async def get_subscription(
    subscription_id: UUID,
    subscription_service: SubscriptionServiceDep,
    staff_user: StaffUserDep,
) -> SubscriptionResponseScheme:
    """Возвращает тип подписки по идентификатору. Доступно только суперпользователям."""
    try:
        return await subscription_service.get_subscription_by_id(subscription_id)
    except SubscriptionNotFoundException as exc:
        raise SubscriptionNotFoundHTTPException(detail=exc.detail)


@router.patch(
    "/{subscription_id}/",
    summary="Обновить тип подписки",
)
async def update_subscription(
    subscription_id: UUID,
    data: SubscriptionUpdateScheme,
    subscription_service: SubscriptionServiceDep,
    staff_user: StaffUserDep,
) -> SubscriptionResponseScheme:
    """Обновляет поля типа подписки. Доступно только суперпользователям."""
    try:
        return await subscription_service.update_subscription(subscription_id, data)
    except SubscriptionNotFoundException as exc:
        raise SubscriptionNotFoundHTTPException(detail=exc.detail)
    except SubscriptionAlreadyExistsException as exc:
        raise SubscriptionAlreadyExistsHTTPException(detail=exc.detail)


@router.delete(
    "/{subscription_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить тип подписки",
)
async def delete_subscription(
    subscription_id: UUID,
    subscription_service: SubscriptionServiceDep,
    staff_user: StaffUserDep,
) -> None:
    """Удаляет тип подписки. Доступно только суперпользователям."""
    try:
        await subscription_service.delete_subscription(subscription_id)
    except SubscriptionNotFoundException as exc:
        raise SubscriptionNotFoundHTTPException(detail=exc.detail)
    except SubscriptionInUseException as exc:
        raise SubscriptionInUseHTTPException(detail=exc.detail)
