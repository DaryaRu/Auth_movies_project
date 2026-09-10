"""API клиент для auth сервиса."""

import httpx
from django.conf import settings

USER_PROFILE_GET_URL = "/users/{user_id}/profile/"


def _error_detail(response: httpx.Response) -> str:
    """Достать detail из тела ответа FastAPI, если он там есть."""
    try:
        detail = response.json().get("detail")
        if detail:
            return str(detail)
    except (ValueError, AttributeError):
        pass
    return response.text


class AuthAPIClient:
    """Клиент для взаимодействия с API auth-сервиса.

    Токен авторизации передается динамически через заголовок Authorization
    из сессии пользователя в админ-панели.
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.AUTH_API_BASE_URL).rstrip("/")
        self.timeout = httpx.Timeout(30.0)

    def _get_headers(self, auth_token: str | None = None) -> dict:
        """Получить заголовки для запросов.

        Args:
            auth_token: JWT токен админа из сессии.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        return headers

    def _handle_response(self, response: httpx.Response) -> dict | list:
        """Обработать ответ API."""
        response.raise_for_status()
        if response.status_code == 204:
            return {}
        return response.json()

    def get_user_profile(
        self, user_id: str, auth_token: str | None = None
    ) -> dict:
        """Получить личные данные пользователя по id.

        Args:
            user_id: UUID пользователя.
            auth_token: JWT токен админа из сессии. Нужно право
                user:view_personal_data (или is_superuser) — проверяется
                на стороне auth-service через require_permission().
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}{USER_PROFILE_GET_URL.format(user_id=user_id)}",
                    headers=self._get_headers(auth_token),
                )
                result = self._handle_response(response)
                if not isinstance(result, dict):
                    raise APIError(f"Expected dict, got {type(result)}")
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise UserProfileNotFoundError(
                    f"User {user_id} not found"
                ) from e
            if e.response.status_code == 403:
                raise PermissionDeniedError(_error_detail(e.response)) from e
            raise APIError(f"Failed to get user profile: {e}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Failed to get user profile: {e}") from e


class APIError(Exception):
    """Ошибка API."""

    pass


class UserProfileNotFoundError(APIError):
    """Пользователь не найден."""

    pass


class PermissionDeniedError(APIError):
    """Недостаточно прав для просмотра личных данных."""

    pass


api_client = AuthAPIClient()
