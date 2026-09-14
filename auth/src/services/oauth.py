"""Вход через OAuth-провайдеров."""

import logging
import secrets
from uuid import UUID

from redis.asyncio import Redis

from src.core.config import settings
from src.exceptions import (
    InvalidProviderException,
    LastAuthMethodRestrictionException,
    OAuthAccountNotLinkedException,
    OAuthStateException,
    ProviderException,
    UserNotFoundException,
)
from src.integrations.oauth.providers_factory import OAuthProviderFactory
from src.integrations.oauth.vk_provider import VkOAuthProvider
from src.models.users import UserORM
from src.schemas.oauth import AuthProvider, OAuthUserInfoScheme
from src.services.login_completion import LoginCompletionService
from src.services.registration import RegistrationService
from src.services.sessions import SessionService
from src.utils.db_manager import DBManager


class OAuthService:
    def __init__(
        self,
        provider_factory: OAuthProviderFactory,
        db: DBManager,
        registration_service: RegistrationService,
        login_completion_service: LoginCompletionService,
        session_service: SessionService,
        redis: Redis,
    ) -> None:
        self._provider_factory = provider_factory
        self._db = db
        self._registration_service = registration_service
        self._login_completion = login_completion_service
        self._session_service = session_service
        self._redis = redis

    async def get_auth_url(self, provider: AuthProvider) -> str:
        state = secrets.token_urlsafe(32)
        await self._redis.setex(
            f"oauth_state:{state}",
            settings.OAUTH_STATE_EXPIRE_SECONDS,
            provider.value,
        )
        strategy = self._provider_factory.get(provider)
        if provider == AuthProvider.VK:
            assert isinstance(strategy, VkOAuthProvider)
            auth_url = strategy.get_auth_url(state)
            code_verifier = strategy.get_code_verifier()
            if code_verifier:
                await self._redis.setex(
                    f"vk_pkce:{state}",
                    settings.OAUTH_STATE_EXPIRE_SECONDS,
                    code_verifier,
                )
        else:
            auth_url = strategy.get_auth_url(state)

        return auth_url

    async def authenticate(
        self,
        provider: AuthProvider,
        code: str,
        ip_address: str,
        user_agent: str,
        state: str,
        device_id: str | None = None,
    ) -> tuple[str, str]:
        stored_provider_key = f"oauth_state:{state}"
        stored_provider = await self._redis.get(stored_provider_key)
        if not stored_provider or stored_provider != provider.value:
            raise OAuthStateException()
        await self._redis.delete(stored_provider_key)

        strategy = self._provider_factory.get(provider)

        if provider == AuthProvider.VK:
            assert isinstance(strategy, VkOAuthProvider)
            code_verifier = await self._redis.get(f"vk_pkce:{state}")
            await self._redis.delete(f"vk_pkce:{state}")
            oauth_user = await strategy.get_user_info_with_pkce(
                code, state, code_verifier, device_id
            )
        else:
            oauth_user = await strategy.get_user_info(code)

        user = await self._get_or_create_oauth_user(oauth_user)
        return await self._login_completion.create_session(
            user, ip_address, user_agent, auth_method=oauth_user.provider
        )

    async def _get_or_create_oauth_user(
        self,
        user_info: OAuthUserInfoScheme,
    ) -> UserORM:
        oauth_account = await self._db.oauth_accounts.get_by_provider_data(
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
        )

        if oauth_account:
            user = await self._db.users.get_one_or_none_by_id(
                id=oauth_account.user_id
            )
            if user is None:
                raise UserNotFoundException()
            return user
        if not user_info.email and not user_info.phone:
            raise ProviderException()
        user = await self._db.users.get_one_or_none_by_email_or_phone(
            email=user_info.email, phone=user_info.phone
        )
        if not user:
            user = await self._db.users.create_user(
                email=user_info.email,
                phone=user_info.phone,
                hashed_password=None,
            )
            await self._registration_service.assign_free_subscription(user.id)

        await self._db.oauth_accounts.create_oauth_account(
            user_id=user.id,
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
        )
        return user

    async def unlink_account(
        self, user_id: UUID, provider_str: str, current_sid: str
    ) -> tuple[list[str], bool]:
        """
        Отвязывает аккаунт внешнего провайдера.

        Args:
            user_id (UUID): Идентификатор пользователя в системе.
            provider_str (str): Название провайдера (google, yandex, vk).
            current_sid (str): Идентификатор текущей активной сессии.

        Returns:
            tuple[list[str], bool]:
                - list[str]: Список названий привязанных провайдеров.
                - bool: True, если текущая сессия была аннулирована.

        Raises:
            UserNotFoundException: Если пользователь не найден.
            OAuthAccountNotLinkedException: Если провайдер не привязан.
            LastAuthMethodRestrictionException: Если это единственный
            способ входа.
        """
        try:
            AuthProvider(provider_str)
        except ValueError:
            logging.error(f"Неизвестный провайдер для отвязки: {provider_str}")
            raise InvalidProviderException() from None

        async with self._db as db:
            user = await db.users.get_by_id_for_update(user_id)
            if not user:
                raise UserNotFoundException()

            all_accounts = await db.oauth_accounts.get_all_by_user_id(user_id)

            target_account = next(
                (acc for acc in all_accounts if acc.provider == provider_str),
                None,
            )
            if not target_account:
                raise OAuthAccountNotLinkedException()

            has_password = bool(user.hashed_password)
            remaining_oauth_count = len(all_accounts) - 1

            if not has_password and remaining_oauth_count == 0:
                raise LastAuthMethodRestrictionException()

            await db.oauth_accounts.delete_oauth_account(target_account.id)

            remaining_providers = [
                acc.provider
                for acc in all_accounts
                if acc.provider != provider_str
            ]

        current_session_deleted = await self._delete_sessions_by_auth_method(
            user_id=user_id,
            auth_method=provider_str,
            current_sid=current_sid,
        )

        return remaining_providers, current_session_deleted

    async def _delete_sessions_by_auth_method(
        self,
        user_id: UUID,
        auth_method: str,
        current_sid: str,
    ) -> bool:
        """Аннулирует в Redis все активные сессии пользователя,
        созданные через определенный метод входа."""
        sessions = await self._session_service.get_active_sessions(
            user_id=user_id, current_sid=current_sid
        )

        current_session_deleted = False

        for session_info in sessions:
            sid = (
                session_info.get("sid")
                if isinstance(session_info, dict)
                else getattr(session_info, "sid", None)
            )
            if not sid:
                continue

            full_session = await self._session_service.get_session(sid)
            if not full_session:
                continue

            session_auth_method = (
                full_session.get("auth_method")
                if isinstance(full_session, dict)
                else getattr(full_session, "auth_method", None)
            )

            if session_auth_method == auth_method:
                await self._session_service.delete_session(sid)
                if str(sid) == str(current_sid):
                    current_session_deleted = True

        return current_session_deleted
