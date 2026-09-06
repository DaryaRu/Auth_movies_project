from src.repositories.oauth_accounts import OAuthAccountsPostgreSQLRepository
from src.repositories.permissions import PermissionsPostgreSQLRepository
from src.repositories.roles import RolesPostgreSQLRepository
from src.repositories.subscriptions import SubscriptionsPostgreSQLRepository
from src.repositories.user_notification_settings import (
    UserNotificationSettingsRepository,
)
from src.repositories.user_subscriptions import (
    UserSubscriptionsPostgreSQLRepository,
)
from src.repositories.users import UsersPostgreSQLRepository


class DBManager:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session = self.session_factory()
        self.users = UsersPostgreSQLRepository(self.session)
        self.roles = RolesPostgreSQLRepository(self.session)
        self.permissions = PermissionsPostgreSQLRepository(self.session)
        self.oauth_accounts = OAuthAccountsPostgreSQLRepository(self.session)
        self.subscriptions = SubscriptionsPostgreSQLRepository(self.session)
        self.user_subscriptions = UserSubscriptionsPostgreSQLRepository(self.session)
        self.user_notification_settings = UserNotificationSettingsRepository(
            self.session
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        except Exception:
            await self.session.rollback()
            raise
        finally:
            await self.session.close()
