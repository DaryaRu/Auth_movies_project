import logging
from urllib.parse import urlencode

import aiohttp
from jose import jwt

from src.core.config import settings
from src.exceptions import ProviderException
from src.integrations.oauth.base_provider import OAuthProvider
from src.schemas.oauth import OAuthUserInfoScheme, AuthProvider


class YandexOAuthProvider(OAuthProvider):
    def get_auth_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": settings.YANDEX_CLIENT_ID,
            "redirect_uri": settings.YANDEX_REDIRECT_URI,
            "state": state
        }
        return "https://oauth.yandex.ru/authorize?" + urlencode(params)

    async def get_user_info(self, code: str) -> OAuthUserInfoScheme:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://oauth.yandex.ru/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.YANDEX_CLIENT_ID,
                    "client_secret": settings.YANDEX_CLIENT_SECRET,
                },
            ) as response:
                if response.status >= 400:
                    detail = await response.text()
                    logging.error(
                        "Не удалось получить токен доступа Yandex: "
                        f"status_code={response.status}, {detail=}"
                    )
                    raise ProviderException()

                token_data = await response.json()

            access_token = token_data["access_token"]

            async with session.get(
                "https://login.yandex.ru/info",
                headers={
                    "Authorization": f"OAuth {access_token}",
                },
                params={
                    "format": "jwt",
                },
            ) as response:
                if response.status >= 400:
                    detail = await response.text()
                    logging.error(
                        "Не удалось получить данные пользователя от Yandex: "
                        f"status_code={response.status}, {detail=}"
                    )
                    raise ProviderException()

                jwt_token = await response.text()
                yandex_user = jwt.decode(
                    jwt_token,
                    key=settings.YANDEX_CLIENT_SECRET,
                    algorithms=["HS256"],
                    issuer="login.yandex.ru",
                )
        return OAuthUserInfoScheme(
            email=yandex_user.get("default_email"),
            provider_user_id=str(yandex_user["uid"]),
            phone=yandex_user["default_phone"]["number"] if yandex_user.get("default_phone") else None,
            provider=AuthProvider.YANDEX,
        )
