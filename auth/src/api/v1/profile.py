from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.api.v1.dependencies import (
    CurrentUserDep,
    DBDep,
    ProfileServiceDep,
    require_permission,
)
from src.core.config import settings
from src.core.limiter import limiter
from src.exceptions import UserNotFoundHTTPException
from src.models.users import UserORM
from src.schemas.users import UpdateFullNameRequestScheme, UserResponseScheme

router = APIRouter(tags=["Profile"])


@router.get(
    "/users/me/",
    response_model=UserResponseScheme,
    summary="Получить данные профиля",
)
@limiter.limit(settings.LIMIT_VALUE)
async def get_me_profile(user: CurrentUserDep, request: Request):
    """Данные текущего пользователя: email, телефон, ФИО, таймзона, статус верификации email."""
    return user


@router.patch(
    "/users/me/full-name/",
    response_model=UserResponseScheme,
    summary="Обновить ФИО",
)
@limiter.limit(settings.LIMIT_VALUE)
async def update_full_name(
    data: UpdateFullNameRequestScheme,
    profile_service: ProfileServiceDep,
    user: CurrentUserDep,
    request: Request,
):
    """Обновление ФИО текущего пользователя."""
    return await profile_service.update_full_name(user_id=user.id, data=data)


@router.get(
    "/users/{user_id}/profile/",
    response_model=UserResponseScheme,
    summary="Получить данные профиля пользователя (доступно админам с правом просмотра)",
)
@limiter.limit(settings.LIMIT_VALUE)
async def get_user_profile(
    user_id: UUID,
    db: DBDep,
    request: Request,
    _: UserORM = Depends(require_permission("user:view_personal_data")),
):
    """Личные данные пользователя по id: email, телефон, ФИО, таймзона,
    статус верификации email. Требует право user:view_personal_data
    (суперпользователь проходит без него)."""
    user = await db.users.get_one_or_none_by_id(user_id)
    if user is None:
        raise UserNotFoundHTTPException()
    return user
