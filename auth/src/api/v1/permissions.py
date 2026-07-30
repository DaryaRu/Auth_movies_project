from uuid import UUID

from fastapi import APIRouter, status

from src.api.v1.dependencies import PermissionServiceDep, StaffUserDep
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


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Создать право",
)
async def create_permission(
    data: PermissionCreateScheme,
    permission_service: PermissionServiceDep,
    staff_user: StaffUserDep,
) -> PermissionResponseScheme:
    """Создаёт новое право доступа. Доступно только суперпользователям."""
    try:
        return await permission_service.create_permission(data)  # type: ignore[return-value]
    except PermissionAlreadyExistsException as exc:
        raise PermissionAlreadyExistsHTTPException(detail=exc.detail) from exc


@router.get(
    "/",
    summary="Список прав",
)
async def get_all_permissions(
    permission_service: PermissionServiceDep,
    staff_user: StaffUserDep,
) -> list[PermissionResponseScheme]:
    """Возвращает список всех прав доступа. Доступно только суперпользователям."""
    return await permission_service.get_all_permissions()  # type: ignore[return-value]


@router.patch(
    "/{permission_id}/",
    summary="Обновить право",
)
async def update_permission(
    permission_id: UUID,
    data: PermissionUpdateScheme,
    permission_service: PermissionServiceDep,
    staff_user: StaffUserDep,
) -> PermissionResponseScheme:
    """Обновляет поля права доступа. Доступно только суперпользователям."""
    try:
        return await permission_service.update_permission(permission_id, data)  # type: ignore[return-value]
    except PermissionNotFoundException as exc:
        raise PermissionNotFoundHTTPException(detail=exc.detail) from exc
    except PermissionAlreadyExistsException as exc:
        raise PermissionAlreadyExistsHTTPException(detail=exc.detail) from exc


@router.delete(
    "/{permission_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить право",
)
async def delete_permission(
    permission_id: UUID,
    permission_service: PermissionServiceDep,
    staff_user: StaffUserDep,
) -> None:
    """Удаляет право доступа по идентификатору. Доступно только суперпользователям."""
    try:
        await permission_service.delete_permission(permission_id)
    except PermissionNotFoundException as exc:
        raise PermissionNotFoundHTTPException(detail=exc.detail) from exc
