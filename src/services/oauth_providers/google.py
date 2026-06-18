from src.core.config import settings
from src.services.oauth_providers.base import OAuthUserInfo

google_provider = {
    "client_id": settings.GOOGLE_CLIENT_ID,
    "client_secret": settings.GOOGLE_CLIENT_SECRET,
    "authorize_url": "https://accounts.google.com/o/oauth2/auth",
    "token_url": "https://oauth2.googleapis.com/token",
    "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
    "scope": "openid email",
    "parse_user_info": lambda provider, data: OAuthUserInfo(
        provider=provider,
        provider_user_id=str(data["sub"]),
        email=data.get("email"),
    ),
}
