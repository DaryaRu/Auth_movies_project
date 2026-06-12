from src.repositories.permissions import PermissionsPostgreSQLRepository
from src.repositories.roles import RolesPostgreSQLRepository
from src.repositories.users import (
    UsersPostgreSQLRepository,
    RefreshTokenPostgreSQLRepository,
)


class DBManager:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session = self.session_factory()
        self.users = UsersPostgreSQLRepository(self.session)
        self.refresh_tokens = RefreshTokenPostgreSQLRepository(self.session)
        self.roles = RolesPostgreSQLRepository(self.session)
        self.permissions = PermissionsPostgreSQLRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()
