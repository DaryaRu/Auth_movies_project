from abc import ABC, abstractmethod
from uuid import UUID

from asyncpg import UniqueViolationError
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.exceptions import ObjectAlreadyexistsException
from src.models.associations import role_permissions_table, user_roles_table
from src.models.permissions import PermissionORM
from src.models.roles import RoleORM
from src.repositories.base import BasePostgreSQLRepository


class RolesAbstractRepository(ABC):
    """
    Абстрактный репозиторий для работы с ролями.

    Определяет базовые методы для:
    - создания, получения, обновления и удаления ролей,
    - назначения и снятия ролей у пользователей,
    - назначения и снятия прав у ролей,
    - получения всех прав пользователя.
    """

    @abstractmethod
    async def create_role(
        self, name: str, description: str | None, is_active: bool
    ) -> RoleORM:
        """
        Создаёт новую роль.

        Args:
            name (str): Название роли.
            description (str | None): Описание роли.
            is_active (bool): Активна ли роль.

        Returns:
            RoleORM: Созданная роль.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_id(self, id: UUID) -> RoleORM | None:
        """
        Получает роль по id.

        Args:
            id (UUID): Идентификатор роли.

        Returns:
            RoleORM | None: Роль или None, если не найдена.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_name(self, name: str) -> RoleORM | None:
        """
        Получает роль по названию.

        Args:
            name (str): Название роли.

        Returns:
            RoleORM | None: Роль или None, если не найдена.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_role_with_permissions(self, id: UUID) -> RoleORM | None:
        """
        Получает роль вместе со связанными правами.

        Args:
            id (UUID): Идентификатор роли.

        Returns:
            RoleORM | None: Роль с загруженными правами или None, если не найдена.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all(self) -> list[RoleORM]:
        """
        Возвращает список всех ролей.

        Returns:
            list[RoleORM]: Список ролей.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_role(self, id: UUID, **kwargs) -> RoleORM:
        """
        Обновляет поля роли.

        Args:
            id (UUID): Идентификатор роли.
            **kwargs: Поля для обновления.

        Returns:
            RoleORM: Обновлённая роль.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_role(self, id: UUID) -> None:
        """
        Удаляет роль по id.

        Args:
            id (UUID): Идентификатор роли.
        """
        raise NotImplementedError

    @abstractmethod
    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> None:
        """
        Назначает роль пользователю.

        Args:
            user_id (UUID): Идентификатор пользователя.
            role_id (UUID): Идентификатор роли.
        """
        raise NotImplementedError

    @abstractmethod
    async def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> None:
        """
        Снимает роль с пользователя.

        Args:
            user_id (UUID): Идентификатор пользователя.
            role_id (UUID): Идентификатор роли.
        """
        raise NotImplementedError

    @abstractmethod
    async def has_role(self, user_id: UUID, role_id: UUID) -> bool:
        """
        Проверяет, назначена ли роль пользователю.

        Args:
            user_id (UUID): Идентификатор пользователя.
            role_id (UUID): Идентификатор роли.

        Returns:
            bool: True, если роль назначена пользователю.
        """
        raise NotImplementedError

    @abstractmethod
    async def assign_permission_to_role(
        self, role_id: UUID, permission_id: UUID
    ) -> None:
        """
        Добавляет право к роли.

        Args:
            role_id (UUID): Идентификатор роли.
            permission_id (UUID): Идентификатор права.
        """
        raise NotImplementedError

    @abstractmethod
    async def remove_permission_from_role(
        self, role_id: UUID, permission_id: UUID
    ) -> None:
        """
        Убирает право из роли.

        Args:
            role_id (UUID): Идентификатор роли.
            permission_id (UUID): Идентификатор права.
        """
        raise NotImplementedError

    @abstractmethod
    async def has_permission(self, role_id: UUID, permission_id: UUID) -> bool:
        """
        Проверяет, есть ли у роли указанное право.

        Args:
            role_id (UUID): Идентификатор роли.
            permission_id (UUID): Идентификатор права.

        Returns:
            bool: True, если право назначено для роли.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_user_permissions(self, user_id: UUID) -> list[PermissionORM]:
        """
        Возвращает все права пользователя через его роли.

        Args:
            user_id (UUID): Идентификатор пользователя.

        Returns:
            list[PermissionORM]: Список прав пользователя.
        """
        raise NotImplementedError


class RolesPostgreSQLRepository(RolesAbstractRepository, BasePostgreSQLRepository):
    """Репозиторий ролей."""

    model = RoleORM

    async def get_all(self) -> list[RoleORM]:
        return list(await BasePostgreSQLRepository.get_all(self))

    async def create_role(
        self, name: str, description: str | None = None, is_active: bool = True
    ) -> RoleORM:
        return await self.add_one(
            name=name, description=description, is_active=is_active
        )

    async def get_one_or_none_by_id(self, id: UUID) -> RoleORM | None:
        return await self.get_one_or_none(id=id)

    async def get_one_or_none_by_name(self, name: str) -> RoleORM | None:
        return await self.get_one_or_none(name=name)

    async def get_role_with_permissions(self, id: UUID) -> RoleORM | None:
        query = (
            select(RoleORM)
            .where(RoleORM.id == id)
            .options(selectinload(RoleORM.permissions))
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def update_role(self, id: UUID, **kwargs) -> RoleORM:
        return await self.update_one(id=id, **kwargs)

    async def delete_role(self, id: UUID) -> None:
        await self.delete_one(id=id)

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> None:
        query = insert(user_roles_table).values(user_id=user_id, role_id=role_id)
        try:
            await self._session.execute(query)
        except IntegrityError as ex:
            if isinstance(ex.orig.__cause__, UniqueViolationError):
                raise ObjectAlreadyexistsException from ex
            raise

    async def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> None:
        query = delete(user_roles_table).where(
            user_roles_table.c.user_id == user_id,
            user_roles_table.c.role_id == role_id,
        )
        await self._session.execute(query)

    async def has_role(self, user_id: UUID, role_id: UUID) -> bool:
        query = select(user_roles_table).where(
            user_roles_table.c.user_id == user_id,
            user_roles_table.c.role_id == role_id,
        )
        result = await self._session.execute(query)
        return result.first() is not None

    async def assign_permission_to_role(
        self, role_id: UUID, permission_id: UUID
    ) -> None:
        query = insert(role_permissions_table).values(
            role_id=role_id, permission_id=permission_id
        )
        try:
            await self._session.execute(query)
        except IntegrityError as ex:
            if isinstance(ex.orig.__cause__, UniqueViolationError):
                raise ObjectAlreadyexistsException from ex
            raise

    async def remove_permission_from_role(
        self, role_id: UUID, permission_id: UUID
    ) -> None:
        query = delete(role_permissions_table).where(
            role_permissions_table.c.role_id == role_id,
            role_permissions_table.c.permission_id == permission_id,
        )
        await self._session.execute(query)

    async def has_permission(self, role_id: UUID, permission_id: UUID) -> bool:
        query = select(role_permissions_table).where(
            role_permissions_table.c.role_id == role_id,
            role_permissions_table.c.permission_id == permission_id,
        )
        result = await self._session.execute(query)
        return result.first() is not None

    async def get_user_permissions(self, user_id: UUID) -> list[PermissionORM]:
        query = (
            select(PermissionORM)
            .join(
                role_permissions_table,
                PermissionORM.id == role_permissions_table.c.permission_id,
            )
            .join(RoleORM, RoleORM.id == role_permissions_table.c.role_id)
            .join(user_roles_table, RoleORM.id == user_roles_table.c.role_id)
            .where(user_roles_table.c.user_id == user_id)
            .distinct()
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())
