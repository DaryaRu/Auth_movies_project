from src.core.config import settings
from src.services.oauth_providers.base import OAuthUserInfo

# Эндпоинты взяты из Google OAuth Discovery Document:
# https://accounts.google.com/.well-known/openid-configuration
google_provider = {
    # ID OAuth-клиента из Google Console
    "client_id": settings.GOOGLE_CLIENT_ID,
    # Секрет OAuth-клиента из Google Console
    "client_secret": settings.GOOGLE_CLIENT_SECRET,
    # authorization_endpoint - URL страницы входа Google, куда перенаправляется пользователь
    "authorize_url": "https://accounts.google.com/o/oauth2/auth",
    # token_endpoint - URL обмена authorization code на access token
    "token_url": "https://oauth2.googleapis.com/token",
    # userinfo_endpoint - URL получения данных пользователя;
    # Authlib автоматически подставляет токен в заголовок запроса
    "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
    # openid - включает поле sub (уникальный ID пользователя у Google)
    # email - включает поля email и email_verified
    "scope": "openid email",
    # data["sub"] - уникальный ID пользователя на стороне Google
    "parse_user_info": lambda provider, data: OAuthUserInfo(
        provider=provider,
        provider_user_id=str(data["sub"]),
        email=data.get("email"),
    ),
}
