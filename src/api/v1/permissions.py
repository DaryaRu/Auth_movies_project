from uuid import UUID

from fastapi import APIRouter, status

from src.api.v1.dependiences import PermissionServiceDep, StaffUserDep
from src.exceptions import (
    PermissionAlreadyExistsException,
    PermissionAlreadyExistsHTTPException,
    PermissionNotFoundException,
    PermissionNotFoundHTTPException,
)
from src.schemas.permissions import (
    PermissionCreateScheme,
    PermissionResponseScheme,
    PermissionUpdateScheme,
)

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_permission(
    data: PermissionCreateScheme,
    permission_service: PermissionServiceDep,
    staff_user: StaffUserDep,
) -> PermissionResponseScheme:
    """Создание нового права доступа. Доступно только суперпользователям."""
    try:
        return await permission_service.create_permission(data)
    except PermissionAlreadyExistsException as exc:
        raise PermissionAlreadyExistsHTTPException(detail=exc.detail)


@router.get("/")
async def get_all_permissions(
    permission_service: PermissionServiceDep,
    staff_user: StaffUserDep,
) -> list[PermissionResponseScheme]:
    """Получение списка всех прав доступа. Доступно только суперпользователям."""
    return await permission_service.get_all_permissions()


@router.patch("/{permission_id}/")
async def update_permission(
    permission_id: UUID,
    data: PermissionUpdateScheme,
    permission_service: PermissionServiceDep,
    staff_user: StaffUserDep,
) -> PermissionResponseScheme:
    """Обновление права доступа. Доступно только суперпользователям."""
    try:
        return await permission_service.update_permission(permission_id, data)
    except PermissionNotFoundException as exc:
        raise PermissionNotFoundHTTPException(detail=exc.detail)
    except PermissionAlreadyExistsException as exc:
        raise PermissionAlreadyExistsHTTPException(detail=exc.detail)


@router.delete("/{permission_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: UUID,
    permission_service: PermissionServiceDep,
    staff_user: StaffUserDep,
) -> None:
    """Удаление права доступа по идентификатору. Доступно только суперпользователям."""
    try:
        await permission_service.delete_permission(permission_id)
    except PermissionNotFoundException as exc:
        raise PermissionNotFoundHTTPException(detail=exc.detail)
