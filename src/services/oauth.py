from urllib.parse import urlencode
from uuid import uuid4

from authlib.integrations.httpx_client import AsyncOAuth2Client

from src.core.config import settings
from src.exceptions import (
    OAuthEmailNotFoundException,
    OAuthProviderNotFoundException,
)
from src.services.base import BaseService
from src.services.oauth_providers import PROVIDERS, OAuthUserInfo
from src.services.sessions import SessionService
from src.utils.db_manager import DBManager
from src.utils.tokens import JWTTokenService


class OAuthService(BaseService):
    """
    Сервис для аутентификации пользователей через OAuth 2.0.

    Отвечает за:
    - формирование URL редиректа на страницу авторизации провайдера;
    - обмен кода авторизации на данные пользователя;
    - поиск или создание пользователя по данным провайдера;
    - выдачу пары JWT-токенов.
    """

    def __init__(
        self,
        token_service: JWTTokenService,
        session_service: SessionService,
        db: DBManager,
    ) -> None:
        super().__init__(db)
        self._token_service = token_service
        self._session_service = session_service

    def get_provider_config(self, provider: str) -> dict:
        config = PROVIDERS.get(provider)
        if not config:
            raise OAuthProviderNotFoundException()
        return config

    def get_redirect_url(self, provider: str, state: str) -> str:
        """
        Строит URL для редиректа пользователя на страницу авторизации провайдера.

        Args:
            provider (str): Название провайдера (google, yandex, vk).
            state (str): Случайная строка для защиты от CSRF.

        Returns:
            str: URL авторизации с параметрами запроса.
        """
        config = self.get_provider_config(provider)
        params = {
            "client_id": config["client_id"],
            "redirect_uri": f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/auth/{provider}/callback/",
            "scope": config["scope"],
            "response_type": "code",
            "state": state,
        }
        return f"{config['authorize_url']}?{urlencode(params)}"

    async def get_user_info(
        self, provider: str, code: str, redirect_uri: str
    ) -> OAuthUserInfo:
        """
        Отправляет код авторизации провайдеру, получает access-токен.
        Authlib сохраняет его внутри клиента.
        Запрашивает данные пользователя, автоматически подставляя сохранённый токен в заголовок.
        Возвращает OAuthUserInfo через parse_user_info из конфига провайдера.

        Args:
            provider (str): Название провайдера (google, yandex, vk).
            code (str): Код авторизации, полученный от провайдера в callback.
            redirect_uri (str): URI, на который провайдер вернул пользователя.

        Returns:
            OAuthUserInfo: Данные пользователя от провайдера.
        """
        config = self.get_provider_config(provider)
        async with AsyncOAuth2Client(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
        ) as client:
            await client.fetch_token(
                config["token_url"],
                code=code,
                redirect_uri=redirect_uri,
            )
            resp = await client.get(config["userinfo_url"])
            data = resp.json()

        return config["parse_user_info"](provider, data)

    async def _get_or_create_user(self, user_info: OAuthUserInfo):
        # Ищем привязанный OAuth-аккаунт по provider, provider_user_id
        oauth_account = await self._db.oauth_accounts.get_by_provider_data(
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
        )

        if oauth_account:
            return await self._db.users.get_one_or_none_by_id(
                oauth_account.user_id
            )

        # Аккаунт не найден - нужен email для поиска или создания пользователя
        if not user_info.email:
            raise OAuthEmailNotFoundException()

        user = await self._db.users.get_one_or_none_by_email(user_info.email)
        if not user:
            user = await self._db.users.create_user(
                email=user_info.email,
                hashed_password=None,
            )

        # Привязываем OAuth-аккаунт к пользователю
        await self._db.oauth_accounts.create_oauth_account(
            user_id=user.id,
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
        )
        return user

    async def authenticate(
        self,
        provider: str,
        code: str,
        redirect_uri: str,
        ip_address: str,
        user_agent: str,
    ) -> tuple[str, str]:
        # Обмен code на токен провайдера и получение данных пользователя
        user_info = await self.get_user_info(provider, code, redirect_uri)

        # Поиск или создание пользователя по данным провайдера
        user = await self._get_or_create_user(user_info)

        # Получаем права пользователя и формируем JWT payload
        permissions = await self._db.roles.get_user_permissions(user.id)
        permission_codes = [p.code for p in permissions]
        sid = uuid4()

        access_token, refresh_token = (
            self._token_service.create_access_and_refresh_tokens(
                {
                    "sub": str(user.id),
                    "is_superuser": user.is_superuser,
                    "sid": str(sid),
                    "permissions": permission_codes,
                }
            )
        )

        # Сохраняем сессию в Redis
        await self._session_service.add_session(
            user_id=user.id,
            user_agent=user_agent,
            ip=ip_address,
            refresh_token=refresh_token,
            sid=sid,
        )

        return access_token, refresh_token
