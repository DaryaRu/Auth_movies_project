from uuid import UUID

from fastapi import APIRouter, status

from src.api.v1.dependencies import (
    CurrentUserDep,
    StaffUserDep,
    UserSubscriptionServiceDep,
)
from src.exceptions import (
    SubscriptionInactiveException,
    SubscriptionInactiveHTTPException,
    SubscriptionNotFoundException,
    SubscriptionNotFoundHTTPException,
    UserNotFoundException,
    UserNotFoundHTTPException,
    UserSubscriptionNotFoundException,
    UserSubscriptionNotFoundHTTPException,
)
from src.schemas.user_subscriptions import (
    UserSubscriptionCreateScheme,
    UserSubscriptionResponseScheme,
)

router = APIRouter(prefix="/users", tags=["User Subscriptions"])


@router.post(
    "/{user_id}/subscription/",
    status_code=status.HTTP_201_CREATED,
    summary="Назначить подписку пользователю",
)
async def assign_subscription(
    user_id: UUID,
    data: UserSubscriptionCreateScheme,
    user_subscription_service: UserSubscriptionServiceDep,
    staff_user: StaffUserDep,
) -> UserSubscriptionResponseScheme:
    """Назначает подписку пользователю. Текущая активная подписка деактивируется. Доступно только суперпользователям."""
    try:
        return await user_subscription_service.assign_subscription(user_id, data)
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail)
    except SubscriptionNotFoundException as exc:
        raise SubscriptionNotFoundHTTPException(detail=exc.detail)
    except SubscriptionInactiveException as exc:
        raise SubscriptionInactiveHTTPException(detail=exc.detail)


@router.get(
    "/me/subscription/",
    summary="Моя текущая подписка",
)
async def get_my_subscription(
    current_user: CurrentUserDep,
    user_subscription_service: UserSubscriptionServiceDep,
) -> UserSubscriptionResponseScheme | None:
    """Возвращает активную подписку текущего пользователя."""
    return await user_subscription_service.get_active_subscription(current_user.id)


@router.get(
    "/{user_id}/subscription/",
    summary="Текущая подписка пользователя",
)
async def get_user_subscription(
    user_id: UUID,
    user_subscription_service: UserSubscriptionServiceDep,
    staff_user: StaffUserDep,
) -> UserSubscriptionResponseScheme | None:
    """Возвращает активную подписку пользователя. Доступно только суперпользователям."""
    return await user_subscription_service.get_active_subscription(user_id)


@router.get(
    "/me/subscription/history/",
    summary="История моих подписок",
)
async def get_my_subscription_history(
    current_user: CurrentUserDep,
    user_subscription_service: UserSubscriptionServiceDep,
) -> list[UserSubscriptionResponseScheme]:
    """Возвращает историю подписок текущего пользователя, новые первые."""
    return await user_subscription_service.get_subscription_history(current_user.id)


@router.get(
    "/{user_id}/subscription/history/",
    summary="История подписок пользователя",
)
async def get_user_subscription_history(
    user_id: UUID,
    user_subscription_service: UserSubscriptionServiceDep,
    staff_user: StaffUserDep,
) -> list[UserSubscriptionResponseScheme]:
    """Возвращает историю подписок пользователя. Доступно только суперпользователям."""
    return await user_subscription_service.get_subscription_history(user_id)


@router.delete(
    "/{user_id}/subscription/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отменить подписку пользователя",
)
async def cancel_subscription(
    user_id: UUID,
    user_subscription_service: UserSubscriptionServiceDep,
    staff_user: StaffUserDep,
) -> None:
    """Досрочно отменяет активную подписку пользователя. Доступно только суперпользователям."""
    try:
        await user_subscription_service.cancel_subscription(user_id)
    except UserSubscriptionNotFoundException as exc:
        raise UserSubscriptionNotFoundHTTPException(detail=exc.detail)
