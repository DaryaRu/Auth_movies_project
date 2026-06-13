from uuid import UUID

from src.exceptions import (
    ObjectAlreadyexistsException,
    PermissionNotFoundException,
    RoleAlreadyExistsException,
    RoleNotFoundException,
    RolePermissionAlreadyExistsException,
    RolePermissionNotFoundException,
    SystemRoleCannotBeDeletedException,
    UserNotFoundException,
    UserRoleAlreadyExistsException,
    UserRoleNotFoundException,
)
from src.models.permissions import PermissionORM
from src.models.roles import RoleORM
from src.schemas.roles import RoleCreateScheme, RoleUpdateScheme
from src.services.base import BaseService


class RoleService(BaseService):
    """
    Сервис для работы с ролями и правами доступа.

    Содержис бизнес-логику, связанную с ролями:
    - создание, получение, обновление и удаление ролей;
    - назначение и снятие ролей у пользователей;
    - назначение и снятие прав у ролей;
    - получение всех прав пользователя через его роли.
    """

    async def create_role(self, data: RoleCreateScheme) -> RoleORM:
        """
        Создаёт новую роль. Проверяет уникальность названия.

        Args:
            data (RoleCreateScheme): Данные для создания роли.

        Returns:
            RoleORM: Созданная роль.
        """
        existing = await self._db.roles.get_one_or_none_by_name(data.name)
        if existing:
            raise RoleAlreadyExistsException()
        return await self._db.roles.create_role(
            name=data.name,
            description=data.description,
            is_active=data.is_active,
        )

    async def get_all_roles(self) -> list[RoleORM]:
        """
        Возвращает список всех ролей.

        Returns:
            list[RoleORM]: Список ролей.
        """
        return await self._db.roles.get_all()

    async def get_role_by_id(self, role_id: UUID) -> RoleORM:
        """
        Возвращает роль по идентификатору. Выбрасывает исключение, если роль не найдена.

        Args:
            role_id (UUID): Идентификатор роли.

        Returns:
            RoleORM: Найденная роль.
        """
        role = await self._db.roles.get_one_or_none_by_id(role_id)
        if role is None:
            raise RoleNotFoundException()
        return role

    async def get_role_detail(self, role_id: UUID) -> RoleORM:
        """
        Возвращает роль со списком прав.

        Args:
            role_id (UUID): Идентификатор роли.

        Returns:
            RoleORM: Роль с загруженными правами.
        """
        role = await self._db.roles.get_role_with_permissions(role_id)
        if role is None:
            raise RoleNotFoundException()
        return role

    async def update_role(self, role_id: UUID, data: RoleUpdateScheme) -> RoleORM:
        """
        Обновляет поля роли.

        Args:
            role_id (UUID): Идентификатор роли.
            data (RoleUpdateScheme): Данные для обновления.

        Returns:
            RoleORM: Обновлённая роль.
        """
        await self.get_role_by_id(role_id)
        update_data = data.model_dump(exclude_unset=True)
        try:
            return await self._db.roles.update_role(id=role_id, **update_data)
        except ObjectAlreadyexistsException:
            raise RoleAlreadyExistsException()

    async def delete_role(self, role_id: UUID) -> None:
        """
        Удаляет роль. Системные роли удалить нельзя.

        Args:
            role_id (UUID): Идентификатор роли.
        """
        role = await self.get_role_by_id(role_id)
        if role.is_system:
            raise SystemRoleCannotBeDeletedException()
        await self._db.roles.delete_role(role_id)

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> None:
        """
        Назначает роль пользователю. Проверяет существование пользователя и роли.

        Args:
            user_id (UUID): Идентификатор пользователя.
            role_id (UUID): Идентификатор роли.
        """
        user = await self._db.users.get_one_or_none_by_id(user_id)
        if user is None:
            raise UserNotFoundException()
        await self.get_role_by_id(role_id)
        try:
            await self._db.roles.assign_role_to_user(user_id=user_id, role_id=role_id)
        except ObjectAlreadyexistsException:
            raise UserRoleAlreadyExistsException()

    async def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> None:
        """
        Снимает роль с пользователя. Проверяет, что роль действительно назначена.

        Args:
            user_id (UUID): Идентификатор пользователя.
            role_id (UUID): Идентификатор роли.
        """
        user = await self._db.users.get_one_or_none_by_id(user_id)
        if user is None:
            raise UserNotFoundException()
        await self.get_role_by_id(role_id)
        if not await self._db.roles.has_role(user_id=user_id, role_id=role_id):
            raise UserRoleNotFoundException()
        await self._db.roles.remove_role_from_user(user_id=user_id, role_id=role_id)

    async def assign_permission_to_role(
        self, role_id: UUID, permission_id: UUID
    ) -> None:
        """
        Добавляет право к роли. Проверяет существование роли и права.

        Args:
            role_id (UUID): Идентификатор роли.
            permission_id (UUID): Идентификатор права.
        """
        await self.get_role_by_id(role_id)
        permission = await self._db.permissions.get_one_or_none_by_id(permission_id)
        if permission is None:
            raise PermissionNotFoundException()
        try:
            await self._db.roles.assign_permission_to_role(
                role_id=role_id, permission_id=permission_id
            )
        except ObjectAlreadyexistsException:
            raise RolePermissionAlreadyExistsException()

    async def remove_permission_from_role(
        self, role_id: UUID, permission_id: UUID
    ) -> None:
        """
        Убирает право из роли. Проверяет, что право действительно назначено.

        Args:
            role_id (UUID): Идентификатор роли.
            permission_id (UUID): Идентификатор права.
        """
        await self.get_role_by_id(role_id)
        permission = await self._db.permissions.get_one_or_none_by_id(permission_id)
        if permission is None:
            raise PermissionNotFoundException()
        if not await self._db.roles.has_permission(
            role_id=role_id, permission_id=permission_id
        ):
            raise RolePermissionNotFoundException()
        await self._db.roles.remove_permission_from_role(
            role_id=role_id, permission_id=permission_id
        )

    async def get_user_permissions(
        self, user_id: UUID, is_superuser: bool = False
    ) -> list[PermissionORM]:
        """
        Возвращает все права пользователя через его роли.
        Суперпользователю возвращает все права из БД.

        Args:
            user_id (UUID): Идентификатор пользователя.
            is_superuser (bool): Флаг суперпользователя.

        Returns:
            list[PermissionORM]: Список уникальных прав пользователя.
        """
        if is_superuser:
            return await self._db.permissions.get_all()
        return await self._db.roles.get_user_permissions(user_id=user_id)
