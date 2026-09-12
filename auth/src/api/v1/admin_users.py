from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.api.v1.dependencies import DBDep, PaginationDep, require_permission
from src.exceptions import UserNotFoundHTTPException
from src.models.users import UserORM
from src.schemas.users import AdminUserListResponse, UserResponseScheme

router = APIRouter(prefix="/admin/users", tags=["Admin: Users"])


@router.get(
    "/",
    response_model=AdminUserListResponse,
    summary="Список и поиск профилей пользователей (доступно админам с правом просмотра)",
)
async def list_users(
    db: DBDep,
    pagination: PaginationDep,
    search: str | None = None,
    sort: Literal["full_name", "-full_name", "email", "-email"] | None = Query(
        default=None,
        description=(
            "Поле для сортировки (full_name или email). Без параметра — "
            "сортировка по дате регистрации (сначала новые)."
        ),
    ),
    _: UserORM = Depends(require_permission("user:view_personal_data")),
):
    """Постраничный список пользователей с поиском по email, телефону и ФИО.
    Требует право user:view_personal_data (суперпользователь проходит без него)."""
    items, total = await db.users.search_users(
        search=search,
        limit=pagination.page_size,
        offset=(pagination.page_number - 1) * pagination.page_size,
        sort=sort,
    )
    return AdminUserListResponse(
        items=items,  # type: ignore[arg-type]
        total=total,
        page_number=pagination.page_number,
        page_size=pagination.page_size,
    )


@router.get(
    "/{user_id}/",
    response_model=UserResponseScheme,
    summary="Получить данные профиля пользователя (доступно админам с правом просмотра)",
)
async def get_user_profile(
    user_id: UUID,
    db: DBDep,
    _: UserORM = Depends(require_permission("user:view_personal_data")),
):
    """Личные данные пользователя по id: email, телефон, ФИО, таймзона,
    статус верификации email. Требует право user:view_personal_data
    (суперпользователь проходит без него)."""
    user = await db.users.get_one_or_none_by_id(user_id)
    if user is None:
        raise UserNotFoundHTTPException()
    return user
