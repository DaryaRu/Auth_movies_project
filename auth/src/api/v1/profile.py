"""Профиль пользователя (данные, ФИО, права)."""

from fastapi import APIRouter, Request

from src.api.v1.dependencies import (
    CurrentUserDep,
    ProfileServiceDep,
    RoleServiceDep,
)
from src.core.config import settings
from src.core.limiter import limiter
from src.schemas.permissions import PermissionResponseScheme
from src.schemas.users import (
    UpdateFullNameRequestScheme,
    UpdateNicknameRequestScheme,
    UserResponseScheme,
)

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
    "/users/me/permissions/",
    summary="Права текущего пользователя",
    response_model=list[PermissionResponseScheme],
)
@limiter.limit(settings.LIMIT_VALUE)
async def get_my_permissions(
    current_user: CurrentUserDep,
    role_service: RoleServiceDep,
    request: Request,
):
    """Возвращает список прав доступа, назначенных текущему пользователю через его роли."""
    return await role_service.get_user_permissions(
        user_id=current_user.id,
        is_superuser=current_user.is_superuser,
    )

@router.patch(
    "/users/me/nickname/",
    response_model=UserResponseScheme,
    summary="Обновить никнейм",
)
@limiter.limit(settings.LIMIT_VALUE)
async def update_nickname(
    data: UpdateNicknameRequestScheme,
    profile_service: ProfileServiceDep,
    user: CurrentUserDep,
    request: Request,
):
    """Обновление никнейма текущего пользователя."""
    return await profile_service.update_nickname(user_id=user.id, data=data)
