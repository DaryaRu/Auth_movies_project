from uuid import UUID

from fastapi import APIRouter, status

from src.api.v1.dependiences import RoleServiceDep, StaffUserDep
from src.exceptions import (
    PermissionNotFoundException,
    PermissionNotFoundHTTPException,
    RoleAlreadyExistsException,
    RoleAlreadyExistsHTTPException,
    RoleNotFoundException,
    RoleNotFoundHTTPException,
    RolePermissionAlreadyExistsException,
    RolePermissionAlreadyExistsHTTPException,
    RolePermissionNotFoundException,
    RolePermissionNotFoundHTTPException,
    SystemRoleCannotBeDeletedException,
    SystemRoleCannotBeDeletedHTTPException,
    UserNotFoundError,
    UserNotFoundHTTPException,
    UserRoleAlreadyExistsException,
    UserRoleAlreadyExistsHTTPException,
    UserRoleNotFoundException,
    UserRoleNotFoundHTTPException,
)
from src.schemas.roles import (
    RoleCreateScheme,
    RoleDetailScheme,
    RoleResponseScheme,
    RoleUpdateScheme,
)

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Создать роль",
)
async def create_role(
    data: RoleCreateScheme,
    role_service: RoleServiceDep,
    staff_user: StaffUserDep,
) -> RoleResponseScheme:
    """Создаёт новую роль. Доступно только суперпользователям."""
    try:
        return await role_service.create_role(data)
    except RoleAlreadyExistsException as exc:
        raise RoleAlreadyExistsHTTPException(detail=exc.detail)


@router.get(
    "/",
    summary="Список ролей",
)
async def get_all_roles(
    role_service: RoleServiceDep,
    staff_user: StaffUserDep,
) -> list[RoleResponseScheme]:
    """Возвращает список всех ролей. Доступно только суперпользователям."""
    return await role_service.get_all_roles()


@router.get(
    "/{role_id}/",
    summary="Информация о роли",
)
async def get_role(
    role_id: UUID,
    role_service: RoleServiceDep,
    staff_user: StaffUserDep,
) -> RoleDetailScheme:
    """Возвращает роль по идентификатору вместе со списком прав. Доступно только суперпользователям."""
    try:
        return await role_service.get_role_detail(role_id)
    except RoleNotFoundException as exc:
        raise RoleNotFoundHTTPException(detail=exc.detail)


@router.patch(
    "/{role_id}/",
    summary="Обновить роль",
)
async def update_role(
    role_id: UUID,
    data: RoleUpdateScheme,
    role_service: RoleServiceDep,
    staff_user: StaffUserDep,
) -> RoleResponseScheme:
    """Обновляет поля роли. Доступно только суперпользователям."""
    try:
        return await role_service.update_role(role_id, data)
    except RoleNotFoundException as exc:
        raise RoleNotFoundHTTPException(detail=exc.detail)
    except RoleAlreadyExistsException as exc:
        raise RoleAlreadyExistsHTTPException(detail=exc.detail)


@router.delete(
    "/{role_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить роль",
)
async def delete_role(
    role_id: UUID,
    role_service: RoleServiceDep,
    staff_user: StaffUserDep,
) -> None:
    """Удаляет роль. Системные роли удалить нельзя. Доступно только суперпользователям."""
    try:
        await role_service.delete_role(role_id)
    except RoleNotFoundException as exc:
        raise RoleNotFoundHTTPException(detail=exc.detail)
    except SystemRoleCannotBeDeletedException as exc:
        raise SystemRoleCannotBeDeletedHTTPException(detail=exc.detail)


@router.post(
    "/{role_id}/users/{user_id}/",
    status_code=status.HTTP_201_CREATED,
    summary="Назначить роль пользователю",
)
async def assign_role_to_user(
    role_id: UUID,
    user_id: UUID,
    role_service: RoleServiceDep,
    staff_user: StaffUserDep,
) -> None:
    """Назначает роль пользователю. Доступно только суперпользователям."""
    try:
        await role_service.assign_role_to_user(
            user_id=user_id, role_id=role_id
        )
    except UserNotFoundError as exc:
        raise UserNotFoundHTTPException(detail=exc.detail)
    except RoleNotFoundException as exc:
        raise RoleNotFoundHTTPException(detail=exc.detail)
    except UserRoleAlreadyExistsException as exc:
        raise UserRoleAlreadyExistsHTTPException(detail=exc.detail)


@router.delete(
    "/{role_id}/users/{user_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Снять роль с пользователя",
)
async def remove_role_from_user(
    role_id: UUID,
    user_id: UUID,
    role_service: RoleServiceDep,
    staff_user: StaffUserDep,
) -> None:
    """Снимает роль с пользователя. Доступно только суперпользователям."""
    try:
        await role_service.remove_role_from_user(
            user_id=user_id, role_id=role_id
        )
    except UserNotFoundError as exc:
        raise UserNotFoundHTTPException(detail=exc.detail)
    except RoleNotFoundException as exc:
        raise RoleNotFoundHTTPException(detail=exc.detail)
    except UserRoleNotFoundException as exc:
        raise UserRoleNotFoundHTTPException(detail=exc.detail)


@router.post(
    "/{role_id}/permissions/{permission_id}/",
    status_code=status.HTTP_201_CREATED,
    summary="Назначить право роли",
)
async def assign_permission_to_role(
    role_id: UUID,
    permission_id: UUID,
    role_service: RoleServiceDep,
    staff_user: StaffUserDep,
) -> None:
    """Добавляет право к роли. Доступно только суперпользователям."""
    try:
        await role_service.assign_permission_to_role(
            role_id=role_id, permission_id=permission_id
        )
    except RoleNotFoundException as exc:
        raise RoleNotFoundHTTPException(detail=exc.detail)
    except PermissionNotFoundException as exc:
        raise PermissionNotFoundHTTPException(detail=exc.detail)
    except RolePermissionAlreadyExistsException as exc:
        raise RolePermissionAlreadyExistsHTTPException(detail=exc.detail)


@router.delete(
    "/{role_id}/permissions/{permission_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Снять право с роли",
)
async def remove_permission_from_role(
    role_id: UUID,
    permission_id: UUID,
    role_service: RoleServiceDep,
    staff_user: StaffUserDep,
) -> None:
    """Удаляет право из роли. Доступно только суперпользователям."""
    try:
        await role_service.remove_permission_from_role(
            role_id=role_id, permission_id=permission_id
        )
    except RoleNotFoundException as exc:
        raise RoleNotFoundHTTPException(detail=exc.detail)
    except PermissionNotFoundException as exc:
        raise PermissionNotFoundHTTPException(detail=exc.detail)
    except RolePermissionNotFoundException as exc:
        raise RolePermissionNotFoundHTTPException(detail=exc.detail)
