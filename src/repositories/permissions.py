from abc import ABC, abstractmethod
from uuid import UUID

from src.models.permissions import PermissionORM
from src.repositories.base import BasePostgreSQLRepository


class PermissionsAbstractRepository(ABC):
    """
    Абстрактный репозиторий для работы с правами.

    Определяет базовые методы для создания, получения, обновления и удаления прав.
    """

    @abstractmethod
    async def create_permission(
        self, code: str, name: str, description: str | None, category: str
    ) -> PermissionORM:
        """
        Создаёт новое право доступа.

        Args:
            code (str): Уникальный код права.
            name (str): Название права.
            description (str | None): Описание того, что даёт право.
            category (str): Группа для фильтрации.

        Returns:
            PermissionORM: Созданное право.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_id(self, id: UUID) -> PermissionORM | None:
        """
        Получает право по идентификатору.

        Args:
            id (UUID): Идентификатор права.

        Returns:
            PermissionORM | None: Право или None, если не найдено.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_code(self, code: str) -> PermissionORM | None:
        """
        Получает право по коду.

        Args:
            code (str): Код права.

        Returns:
            PermissionORM | None: Право или None, если не найдено.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all(self) -> list[PermissionORM]:
        """
        Возвращает список всех прав.

        Returns:
            list[PermissionORM]: Список прав.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_permission(self, id: UUID, **kwargs) -> PermissionORM:
        """
        Обновляет поля права.

        Args:
            id (UUID): Идентификатор права.
            **kwargs: Поля для обновления.

        Returns:
            PermissionORM: Обновлённое право.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_permission(self, id: UUID) -> None:
        """
        Удаляет право по идентификатору.

        Args:
            id (UUID): Идентификатор права.
        """
        raise NotImplementedError


class PermissionsPostgreSQLRepository(
    PermissionsAbstractRepository, BasePostgreSQLRepository
):
    """
    Репозиторий прав доступа с использованием PostgreSQL и SQLAlchemy Async.
    """

    model = PermissionORM

    async def get_all(self) -> list[PermissionORM]:
        return list(await BasePostgreSQLRepository.get_all(self))

    async def create_permission(
        self,
        code: str,
        name: str,
        description: str | None = None,
        category: str = "general",
    ) -> PermissionORM:
        return await self.add_one(
            code=code, name=name, description=description, category=category
        )

    async def get_one_or_none_by_id(self, id: UUID) -> PermissionORM | None:
        return await self.get_one_or_none(id=id)

    async def get_one_or_none_by_code(self, code: str) -> PermissionORM | None:
        return await self.get_one_or_none(code=code)

    async def update_permission(self, id: UUID, **kwargs) -> PermissionORM:
        return await self.update_one(id=id, **kwargs)

    async def delete_permission(self, id: UUID) -> None:
        await self.delete_one(id=id)
