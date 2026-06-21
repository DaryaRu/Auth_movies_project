from dataclasses import dataclass


@dataclass
class OAuthUserInfo:
    """Данные пользователя, полученные от OAuth-провайдера."""

    provider: str
    provider_user_id: str
    email: str | None
