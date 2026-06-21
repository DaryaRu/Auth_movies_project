import logging
from typing import Generic, Iterable, TypeVar
from uuid import UUID

from asyncpg import ForeignKeyViolationError, UniqueViolationError
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import (
    ObjectAlreadyexistsException,
    ObjectNotFoundException,
)

ModelT = TypeVar("ModelT")


class BasePostgreSQLRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_one_or_none(self, **filters) -> ModelT | None:
        query = select(self.model).filter_by(**filters)
        result = await self._session.execute(query)
        return result.scalars().one_or_none()

    async def get_all(self) -> Iterable[ModelT]:
        query = select(self.model)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def update_one(self, id: UUID, **kwargs) -> ModelT:
        query = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self._session.execute(query)
        return result.scalar_one()

    async def delete_one(self, id: UUID) -> None:
        query = delete(self.model).where(self.model.id == id)
        await self._session.execute(query)

    async def add_one(self, **kwargs) -> ModelT:
        query = insert(self.model).values(**kwargs).returning(self.model)
        try:
            result = await self._session.execute(query)
            return result.scalar_one()
        except IntegrityError as ex:
            logging.exception(f"Не удалось добавить данные в БД,"
                              f"входные данные={kwargs}")
            if isinstance(ex.orig.__cause__, UniqueViolationError):
                raise ObjectAlreadyexistsException from ex
            elif isinstance(ex.orig.__cause__, ForeignKeyViolationError):
                raise ObjectNotFoundException from ex
            else:
                logging.exception(
                    f"Незнакомая ошибка: не удалось добавить данные в БД, "
                    f"входные данные={kwargs}"
                )
                raise ex
