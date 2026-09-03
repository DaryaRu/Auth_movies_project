from fastapi import APIRouter, Request

from src.api.v1.dependencies import CurrentUserDep, ProfileServiceDep
from src.core.config import settings
from src.core.limiter import limiter
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
