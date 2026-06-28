import base64
import hashlib
import secrets
import logging
from urllib.parse import urlencode
from typing import Optional

from authlib.integrations.httpx_client import AsyncOAuth2Client

from src.core.config import settings
from src.exceptions import ProviderException
from src.integrations.oauth.base_provider import OAuthBaseProvider
from src.schemas.oauth import AuthProvider, OAuthUserInfoScheme

logger = logging.getLogger(__name__)


class VkOAuthProvider(OAuthBaseProvider):
    _REDIRECT_URI = (
        f"{settings.OAUTH_REDIRECT_BASE_URL}"
        f"{settings.API_V1_PREFIX}/auth/"
        f"{AuthProvider.VK.value}/callback/"
    )

    _AUTHORIZE_URL = "https://id.vk.ru/authorize"
    _TOKEN_URL = "https://id.vk.ru/oauth2/auth"
    _USER_INFO_URL = "https://id.vk.ru/oauth2/user_info"
    _REVOKE_URL = "https://id.vk.ru/oauth2/revoke"

    def __init__(self):
        self._pending_verifier = None

    @staticmethod
    def _generate_code_verifier() -> str:
        return secrets.token_urlsafe(64)[:128]

    @staticmethod
    def _generate_code_challenge(code_verifier: str) -> str:
        hashed = hashlib.sha256(code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(hashed).decode().replace("=", "")

    def get_auth_url(self, state: str) -> str:
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)

        self._pending_verifier = code_verifier

        params = {
            "client_id": settings.VK_CLIENT_ID,
            "redirect_uri": self._REDIRECT_URI,
            "scope": "email phone vkid.personal_info",
            "response_type": "code",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "lang_id": 0,
            "scheme": "light",
        }
        return self._AUTHORIZE_URL + "?" + urlencode(params)

    def get_code_verifier(self) -> Optional[str]:
        return getattr(self, "_pending_verifier", None)

    async def get_user_info(self, code: str) -> OAuthUserInfoScheme:
        """Базовый метод для BaseProvider (нужен для совместимости)"""
        raise NotImplementedError(
            "VK requires state and code_verifier. Use get_user_info_with_pkce"
        )

    async def get_user_info_with_pkce(
        self,
        code: str,
        state: str,
        code_verifier: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> OAuthUserInfoScheme:
        try:
            if not code_verifier:
                logger.error("Missing code_verifier for VK PKCE")
                raise ProviderException()

            token_params = {
                "code": code,
                "redirect_uri": self._REDIRECT_URI,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
                "client_id": settings.VK_CLIENT_ID,
            }

            if device_id:
                token_params["device_id"] = device_id
                logger.info(f"VK: using device_id: {device_id[:20]}...")
            else:
                logger.error("VK: device_id is required but not provided")
                raise ProviderException()

            logger.info(f"VK: token_params keys: {list(token_params.keys())}")

            async with AsyncOAuth2Client(
                client_id=settings.VK_CLIENT_ID,
                client_secret=settings.VK_CLIENT_SECRET,
            ) as client:
                token_data = await client.fetch_token(
                    self._TOKEN_URL,
                    **token_params,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                )

                if "error" in token_data:
                    error_msg = token_data.get(
                        "error_description", token_data.get("error")
                    )
                    logger.error(f"VK token error: {error_msg}")
                    raise ProviderException()

                access_token = token_data.get("access_token")
                if not access_token:
                    logger.error(f"VK missing access_token: {token_data}")
                    raise ProviderException()

                resp = await client.post(
                    self._USER_INFO_URL,
                    data={
                        "client_id": settings.VK_CLIENT_ID,
                        "access_token": access_token,
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                )

                user_data = resp.json()

                if "error" in user_data:
                    error_msg = user_data.get(
                        "error_description", user_data.get("error")
                    )
                    logger.error(f"VK user_info error: {error_msg}")
                    raise ProviderException()

                user_info = user_data.get("user", {})
                user_id = user_info.get("user_id")
                email = user_info.get("email")
                phone = user_info.get("phone")

                if not user_id:
                    logger.error(f"VK missing user_id: {user_info}")
                    raise ProviderException()

                if not email and not phone:
                    email = f"vk_{user_id}@vk.com"
                    logger.info(
                        f"VK: no email or phone, using generated: {email}"
                        )
                elif not email and phone:
                    logger.info(
                        f"VK: using phone for registration: {phone}"
                        )

                return OAuthUserInfoScheme(
                    provider=AuthProvider.VK,
                    provider_user_id=str(user_id),
                    email=email,
                    phone=phone
                )

        except ProviderException:
            raise
        except Exception as e:
            logger.error(f"VK OAuth error: {e}", exc_info=True)
            raise ProviderException()

    async def revoke_token(self, token: str) -> None:
        try:
            async with AsyncOAuth2Client(
                client_id=settings.VK_CLIENT_ID,
                client_secret=settings.VK_CLIENT_SECRET,
            ) as client:
                await client.post(
                    self._REVOKE_URL,
                    data={
                        "client_id": settings.VK_CLIENT_ID,
                        "access_token": token,
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    timeout=5.0,
                )
                logger.info("VK token revoked successfully")
        except Exception as e:
            logger.warning(f"Failed to revoke VK token: {e}")
