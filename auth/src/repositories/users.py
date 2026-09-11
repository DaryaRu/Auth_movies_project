from abc import ABC, abstractmethod
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select, update

from src.models.subscriptions import SubscriptionORM
from src.models.user_notification_settings import UserNotificationSettingsORM
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
        full_name: str | None = None,
    ) -> UserORM:
        """
        Добавляет нового пользователя.
        Args:
            email (str): Электронная почта пользователя.
            hashed_password (str): Хэшированный пароль
            is_staff (bool): Есть ли права суперпользователя
            timezone (str): IANA-имя таймзоны пользователя.
            full_name (str): ФИО пользователя.
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
        self, min_level: int | None, timezone_filter: str | None = None
    ) -> list[str]:
        """Возвращает уникальные таймзоны активных пользователей с уровнем
        подписки >= min_level. Пользователи без заданной таймзоны считаются 'UTC'.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_user_timezone(
        self, user_id: UUID, timezone: str | None
    ) -> UserORM:
        """
        Обновляет таймзону пользователя.
        Args:
            user_id (UUID): Идентификатор пользователя.
            timezone (str): IANA-имя таймзоны.
        Returns:
            UserORM: Обновленный пользователь.
        """
        raise NotImplementedError

    @abstractmethod
    async def search_users(
        self,
        search: str | None,
        limit: int,
        offset: int,
        sort: str | None = None,
    ) -> tuple[list[UserORM], int]:
        """Постраничный поиск пользователей по email, телефону и ФИО (для админки).

        Args:
            search (str | None): Подстрока для поиска (без учета регистра) по
                email, телефону и ФИО.
            limit (int): Максимум записей на странице.
            offset (int): Смещение от начала выборки.
            sort (str | None): Поле сортировки по "full_name"/"email".
                None - по created_at по убыванию.
        Returns:
            tuple[list[UserORM], int]: Страница пользователей и общее число
                найденных (без учета limit/offset).
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
        full_name: str | None = None,
    ) -> UserORM:
        return await self.add_one(
            email=email,
            hashed_password=hashed_password,
            is_superuser=is_superuser,
            phone=phone,
            timezone=timezone,
            full_name=full_name,
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

    async def update_user_timezone(
        self, user_id: UUID, timezone: str | None
    ) -> UserORM:
        query = (
            update(self.model)
            .where(self.model.id == user_id)
            .values(timezone=timezone)
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

    _SORT_COLUMNS = {
        "full_name": "full_name",
        "email": "email",
    }

    async def search_users(
        self,
        search: str | None,
        limit: int,
        offset: int,
        sort: str | None = None,
    ) -> tuple[list[UserORM], int]:
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)
        if search:
            pattern = f"%{search}%"
            condition = or_(
                self.model.email.ilike(pattern),
                self.model.phone.ilike(pattern),
                self.model.full_name.ilike(pattern),
            )
            query = query.where(condition)
            count_query = count_query.where(condition)

        total = (await self._session.execute(count_query)).scalar_one()

        field_name = (sort or "").lstrip("-")
        column = self._SORT_COLUMNS.get(field_name)
        if column is not None:
            order_column = getattr(self.model, column)
            order_clause = (
                order_column.desc()
                if (sort or "").startswith("-")
                else order_column.asc()
            )
            query = query.order_by(order_clause, self.model.id)
        else:
            query = query.order_by(self.model.created_at.desc(), self.model.id)

        query = query.limit(limit).offset(offset)
        result = await self._session.execute(query)
        return list(result.scalars().all()), total

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
        # Exclude users with notifications disabled
        query = query.outerjoin(
            UserNotificationSettingsORM,
            UserNotificationSettingsORM.user_id == self.model.id,
        ).where(
            or_(
                UserNotificationSettingsORM.user_id.is_(None),
                UserNotificationSettingsORM.notifications_enabled.is_(True),
            )
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def search_distinct_timezones(
        self, min_level: int | None, timezone_filter: str | None = None
    ) -> list[str]:
        tz_column = func.coalesce(self.model.timezone, "UTC")
        query = (
            select(tz_column).where(self.model.is_active.is_(True)).distinct()
        )
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
        # Exclude users with notifications disabled
        query = query.outerjoin(
            UserNotificationSettingsORM,
            UserNotificationSettingsORM.user_id == self.model.id,
        ).where(
            or_(
                UserNotificationSettingsORM.user_id.is_(None),
                UserNotificationSettingsORM.notifications_enabled.is_(True),
            )
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())
