from abc import ABC, abstractmethod
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select, update

from src.models.subscriptions import SubscriptionORM
from src.models.user_subscriptions import UserSubscriptionORM
from src.models.users import UserORM
from src.repositories.base import BasePostgreSQLRepository


class UsersAbstractRepository(ABC):
    """
    Абстрактный репозиторий для работы с пользователями.

    Определяет базовые методы для:
    - добавления пользователя,
    - получения пользователя по email.
    """

    @abstractmethod
    async def create_user(
        self,
        email: str | None,
        phone: str | None,
        hashed_password: str,
        is_superuser: bool = False,
        timezone: str | None = None,
    ) -> UserORM:
        """
        Добавляет нового пользователя.
        Args:
            email (str): Электронная почта пользователя.
            hashed_password (str): Хэшированный пароль
            is_staff (bool): Есть ли права суперпользователя
            timezone (str): IANA-имя таймзоны пользователя.
        Returns:
            User: Созданный пользователь.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_email_or_phone(
        self, email: str | None, phone: str | None
    ) -> UserORM | None:
        """
        Получает пользователя по email.
        Args:
            email (str): Электронная почта пользователя.
            phone (str): Телефон пользователя.
        Returns:
            Optional[User]: Пользователь или None, если не найден.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_email(self, email: str) -> UserORM | None:
        """
        Получает пользователя по email.
        Args:
            email (str): Электронная почта пользователя.
        Returns:
            Optional[User]: Пользователь или None, если не найден.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none_by_id(self, id: UUID) -> UserORM | None:
        """
        Получает пользователя по его идентификатору.
        Args:
            id (UUID): Идентификатор пользователя.
        Returns:
            Optional[User]: Пользователь или None, если не найден.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_user_credentials(
        self, user_id: UUID, **kwargs
    ) -> UserORM:
        """
        Получает пользователя по его идентификатору.

        Args:
            id (UUID): Идентификатор пользователя.

        Returns:
            Optional[User]: Пользователь или None, если не найден.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id_for_update(self, user_id: UUID) -> UserORM | None:
        """Блокирует строку пользователя для UPDATE."""
        raise NotImplementedError

    @abstractmethod
    async def search_by_min_subscription_level(
        self, min_level: int | None, timezone_filter: str | None = None
    ) -> list[UUID]:
        """Возвращает id активных пользователей с уровнем подписки >= min_level.
        Все активные пользователи (min_level=None, без фильтра по подписки).
        timezone_filter — точный фильтр по IANA-таймзоне (без фильтра, если None);
        timezone_filter="UTC" дополнительно включает пользователей без заданной таймзоны.
        """
        raise NotImplementedError

    @abstractmethod
    async def search_distinct_timezones(
        self, min_level: int | None
    ) -> list[str]:
        """Возвращает уникальные таймзоны активных пользователей с уровнем
        подписки >= min_level. Пользователи без заданной таймзоны считаются 'UTC'.
        """
        raise NotImplementedError


class UsersPostgreSQLRepository(
    UsersAbstractRepository, BasePostgreSQLRepository
):
    """
    Репозиторий пользователей с использованием PostgreSQL и SQLAlchemy Async.
    """

    model = UserORM

    async def create_user(
        self,
        email: str | None,
        phone: str | None,
        hashed_password: str | None,
        is_superuser: bool = False,
        timezone: str | None = None,
    ) -> UserORM:
        return await self.add_one(
            email=email,
            hashed_password=hashed_password,
            is_superuser=is_superuser,
            phone=phone,
            timezone=timezone,
        )

    async def get_one_or_none_by_email_or_phone(
        self, email: str | None, phone: str | None
    ) -> UserORM | None:
        conditions = []
        if email:
            conditions.append(UserORM.email == email)
        if phone:
            conditions.append(UserORM.phone == phone)
        if not conditions:
            return None
        query = select(UserORM).where(or_(*conditions))
        result = await self._session.execute(query)
        return result.scalars().one_or_none()

    async def get_one_or_none_by_email(self, email: str) -> UserORM | None:
        return await self.get_one_or_none(email=email)

    async def get_one_or_none_by_id(self, id: UUID) -> UserORM | None:
        return await self.get_one_or_none(id=id)

    async def update_user_credentials(
        self, user_id: UUID, **kwargs
    ) -> UserORM:
        query = (
            update(self.model)
            .where(self.model.id == user_id)
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self._session.execute(query)
        return result.scalar_one()

    async def get_by_id_for_update(self, user_id: UUID) -> UserORM | None:
        stmt = (
            select(self.model)
            .where(self.model.id == user_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_by_min_subscription_level(
        self, min_level: int | None, timezone_filter: str | None = None
    ) -> list[UUID]:
        query = select(self.model.id).where(self.model.is_active.is_(True))
        if min_level is not None:
            now = datetime.now(timezone.utc)
            query = (
                query.outerjoin(
                    UserSubscriptionORM,
                    (UserSubscriptionORM.user_id == self.model.id)
                    & UserSubscriptionORM.is_active.is_(True)
                    & (UserSubscriptionORM.expires_at > now),
                )
                .outerjoin(
                    SubscriptionORM,
                    SubscriptionORM.id == UserSubscriptionORM.subscription_id,
                )
                .where(func.coalesce(SubscriptionORM.level, 0) >= min_level)
                .distinct()
            )
        if timezone_filter is not None:
            if timezone_filter == "UTC":
                query = query.where(
                    or_(
                        self.model.timezone == "UTC",
                        self.model.timezone.is_(None),
                    )
                )
            else:
                query = query.where(self.model.timezone == timezone_filter)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def search_distinct_timezones(
        self, min_level: int | None
    ) -> list[str]:
        tz_column = func.coalesce(self.model.timezone, "UTC")
        query = (
            select(tz_column)
            .where(self.model.is_active.is_(True))
            .distinct()
        )
        if min_level is not None:
            now = datetime.now(timezone.utc)
            query = query.outerjoin(
                UserSubscriptionORM,
                (UserSubscriptionORM.user_id == self.model.id)
                & UserSubscriptionORM.is_active.is_(True)
                & (UserSubscriptionORM.expires_at > now),
            ).outerjoin(
                SubscriptionORM,
                SubscriptionORM.id == UserSubscriptionORM.subscription_id,
            ).where(func.coalesce(SubscriptionORM.level, 0) >= min_level)
        result = await self._session.execute(query)
        return list(result.scalars().all())
