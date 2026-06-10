from abc import ABC, abstractmethod
from uuid import UUID

from src.models.permissions import PermissionORM
from src.repositories.base import BasePostgreSQLRepository


class PermissionsAbstractRepository(ABC):
    @abstractmethod
    async def create_permission(
        self, code: str, name: str, description: str | None, category: str
    ) -> PermissionORM:
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_id(self, id: UUID) -> PermissionORM | None:
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_code(self, code: str) -> PermissionORM | None:
        raise NotImplementedError

    @abstractmethod
    async def get_all(self) -> list[PermissionORM]:
        raise NotImplementedError

    @abstractmethod
    async def update_permission(self, id: UUID, **kwargs) -> PermissionORM:
        raise NotImplementedError

    @abstractmethod
    async def delete_permission(self, id: UUID) -> None:
        raise NotImplementedError


class PermissionsPostgreSQLRepository(PermissionsAbstractRepository, BasePostgreSQLRepository):
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
        return await self.add_one(code=code, name=name, description=description, category=category)

    async def get_one_or_none_by_id(self, id: UUID) -> PermissionORM | None:
        return await self.get_one_or_none(id=id)

    async def get_one_or_none_by_code(self, code: str) -> PermissionORM | None:
        return await self.get_one_or_none(code=code)

    async def update_permission(self, id: UUID, **kwargs) -> PermissionORM:
        return await self.update_one(id=id, **kwargs)

    async def delete_permission(self, id: UUID) -> None:
        await self.delete_one(id=id)
