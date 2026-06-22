from urllib.parse import urlencode

from authlib.integrations.httpx_client import AsyncOAuth2Client

from src.core.config import settings
from src.exceptions import ProviderException
from src.integrations.oauth.base_provider import OAuthBaseProvider
from src.schemas.oauth import AuthProvider, OAuthUserInfoScheme


class GoogleOAuthProvider(OAuthBaseProvider):
    _REDIRECT_URI = f"{settings.OAUTH_REDIRECT_BASE_URL}{settings.API_V1_PREFIX}/auth/{AuthProvider.GOOGLE.value}/callback/"
    
    def get_auth_url(self, state: str) -> str:
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": self._REDIRECT_URI,
            "scope": "openid email",
            "response_type": "code",
            "state": state,
        }
        return "https://accounts.google.com/o/oauth2/auth?" + urlencode(params)
        

    async def get_user_info(self, code: str) -> OAuthUserInfoScheme:
        try:
            async with AsyncOAuth2Client(
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            ) as client:
                await client.fetch_token(
                    "https://oauth2.googleapis.com/token",
                    code=code,
                    redirect_uri=self._REDIRECT_URI,
                )
                resp = await client.get("https://www.googleapis.com/oauth2/v3/userinfo")
                google_user = resp.json()
        except Exception:
            raise ProviderException()
        return OAuthUserInfoScheme(
            provider=AuthProvider.GOOGLE,
            provider_user_id=str(google_user["sub"]),
            email=google_user.get("email"),
        )
