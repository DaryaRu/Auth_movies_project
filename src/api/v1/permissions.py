from uuid import UUID

from fastapi import APIRouter, status

from src.api.v1.dependiences import PermissionServiceDep, StaffUserDep
from src.api.v1.responses import DUPLICATE, NOT_FOUND, AUTH_ERRORS
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
    responses={**AUTH_ERRORS, **DUPLICATE},
)
async def create_permission(
    data: PermissionCreateScheme,
    permission_service: PermissionServiceDep,
    staff_user: StaffUserDep,
) -> PermissionResponseScheme:
    """Создаёт новое право доступа. Доступно только суперпользователям."""
    try:
        return await permission_service.create_permission(data)
    except PermissionAlreadyExistsException as exc:
        raise PermissionAlreadyExistsHTTPException(detail=exc.detail)


@router.get(
    "/",
    summary="Список прав",
    responses={**AUTH_ERRORS},
)
async def get_all_permissions(
    permission_service: PermissionServiceDep,
    staff_user: StaffUserDep,
) -> list[PermissionResponseScheme]:
    """Возвращает список всех прав доступа. Доступно только суперпользователям."""
    return await permission_service.get_all_permissions()


@router.patch(
    "/{permission_id}/",
    summary="Обновить право",
    responses={**AUTH_ERRORS, **DUPLICATE, **NOT_FOUND},
)
async def update_permission(
    permission_id: UUID,
    data: PermissionUpdateScheme,
    permission_service: PermissionServiceDep,
    staff_user: StaffUserDep,
) -> PermissionResponseScheme:
    """Обновляет поля права доступа. Доступно только суперпользователям."""
    try:
        return await permission_service.update_permission(permission_id, data)
    except PermissionNotFoundException as exc:
        raise PermissionNotFoundHTTPException(detail=exc.detail)
    except PermissionAlreadyExistsException as exc:
        raise PermissionAlreadyExistsHTTPException(detail=exc.detail)


@router.delete(
    "/{permission_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить право",
    responses={**AUTH_ERRORS, **NOT_FOUND},
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
        raise PermissionNotFoundHTTPException(detail=exc.detail)
