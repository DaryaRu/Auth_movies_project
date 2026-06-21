from abc import ABC, abstractmethod

from src.schemas.oauth import OAuthUserInfoScheme


class OAuthBaseProvider(ABC):
    @abstractmethod
    def get_auth_url(self, state: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def get_user_info(self, code: str) -> OAuthUserInfoScheme:
        raise NotImplementedError
