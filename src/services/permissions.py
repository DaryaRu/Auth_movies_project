from uuid import UUID

from src.exceptions import (
    ObjectAlreadyexistsException,
    PermissionAlreadyExistsException,
    PermissionNotFoundException,
)
from src.models.permissions import PermissionORM
from src.schemas.permissions import PermissionCreateScheme, PermissionUpdateScheme
from src.services.base import BaseService


class PermissionService(BaseService):
    """
    Сервис для работы с правами доступа.

    Содержит бизнес-логику, связанную с правами:
    - создание, получение, обновление и удаление прав.
    """

    async def create_permission(self, data: PermissionCreateScheme) -> PermissionORM:
        """
        Создаёт новое право. Проверяет уникальность кода права.

        Args:
            data (PermissionCreateScheme): Данные для создания права.

        Returns:
            PermissionORM: Созданное право.
        """
        existing = await self._db.permissions.get_one_or_none_by_code(data.code)
        if existing:
            raise PermissionAlreadyExistsException()
        return await self._db.permissions.create_permission(
            code=data.code,
            name=data.name,
            description=data.description,
            category=data.category,
        )

    async def get_all_permissions(self) -> list[PermissionORM]:
        """
        Возвращает список всех прав.

        Returns:
            list[PermissionORM]: Список прав.
        """
        return await self._db.permissions.get_all()

    async def get_permission_by_id(self, permission_id: UUID) -> PermissionORM:
        """
        Возвращает право по идентификатору. Выбрасывает исключение, если не найдено.

        Args:
            permission_id (UUID): Идентификатор права.

        Returns:
            PermissionORM: Найденное право.
        """
        permission = await self._db.permissions.get_one_or_none_by_id(permission_id)
        if permission is None:
            raise PermissionNotFoundException()
        return permission

    async def update_permission(
        self, permission_id: UUID, data: PermissionUpdateScheme
    ) -> PermissionORM:
        """
        Обновляет поля права.

        Args:
            permission_id (UUID): Идентификатор права.
            data (PermissionUpdateScheme): Данные для обновления.

        Returns:
            PermissionORM: Обновлённое право.
        """
        await self.get_permission_by_id(permission_id)
        update_data = data.model_dump(exclude_unset=True)
        try:
            return await self._db.permissions.update_permission(
                id=permission_id, **update_data
            )
        except ObjectAlreadyexistsException:
            raise PermissionAlreadyExistsException()

    async def delete_permission(self, permission_id: UUID) -> None:
        """
        Удаляет право по идентификатору.

        Args:
            permission_id (UUID): Идентификатор права.
        """
        await self.get_permission_by_id(permission_id)
        await self._db.permissions.delete_permission(permission_id)
