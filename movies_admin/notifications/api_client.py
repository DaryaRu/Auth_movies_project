"""API клиент для сервиса нотификаций."""

import httpx
from django.conf import settings
from django.core.cache import cache

TEMPLATES_LIST_GET_URL = '/notifications/templates/'
TEMPLATES_CREATE_POST_URL = '/notifications/templates/'
TEMPLATE_GET_URL = '/notifications/templates/{template_id}/'
TEMPLATE_UPDATE_PATCH_URL = '/notifications/templates/{template_id}/'


class NotificationsAPIClient:
    """Клиент для взаимодействия с API сервиса нотификаций.

    Токен авторизации передаётся динамически через заголовок Authorization
    из сессии пользователя в админ-панели.
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.NOTIFICATIONS_API_BASE_URL).rstrip('/')
        self.timeout = httpx.Timeout(30.0)

    def _get_headers(self, auth_token: str | None = None) -> dict:
        """Получить заголовки для запросов.

        Args:
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'
        return headers

    def _handle_response(self, response: httpx.Response) -> dict | list:
        """Обработать ответ API."""
        response.raise_for_status()
        if response.status_code == 204:
            return {}
        return response.json()

    def list_templates(self, auth_token: str | None = None) -> list[dict]:
        """Получить список всех шаблонов.

        Args:
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        cache_key = 'notifications_templates_list'
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f'{self.base_url}{TEMPLATES_LIST_GET_URL}',
                    headers=self._get_headers(auth_token)
                )
                result = self._handle_response(response)
                
                if not isinstance(result, list):
                    raise APIError(f"Unexpected response format: expected list, got {type(result)}")
                
                cache.set(cache_key, result, 60)
                return result
        except httpx.HTTPError as e:
            raise APIError(f'Failed to list templates: {e}') from e

    def get_template(self, template_id: str, auth_token: str | None = None) -> dict:
        """Получить шаблон по ID.

        Args:
            template_id: UUID шаблона.
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f'{self.base_url}{TEMPLATE_GET_URL.format(template_id=template_id)}',
                    headers=self._get_headers(auth_token)
                )
                result = self._handle_response(response)
                if not isinstance(result, dict):
                    raise APIError(f"Expected dict, got {type(result)}")
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise TemplateNotFoundError(f'Template {template_id} not found') from e
            raise APIError(f'Failed to get template: {e}') from e
        except httpx.HTTPError as e:
            raise APIError(f'Failed to get template: {e}') from e

    def create_template(self, data: dict, auth_token: str | None = None) -> dict:
        """Создать новый шаблон.

        Args:
            data: Данные шаблона.
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f'{self.base_url}{TEMPLATES_CREATE_POST_URL}',
                    json=data,
                    headers=self._get_headers(auth_token)
                )

                response.raise_for_status()
                
                result = self._handle_response(response)
                
                if not isinstance(result, dict):
                    raise APIError(f"Expected dict, got {type(result)}")
                
                cache.delete('notifications_templates_list')
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                raise DuplicateError('Template already exists') from e
            raise APIError(f'Failed to create template: {e}') from e
        except httpx.HTTPError as e:
            raise APIError(f'Failed to create template: {e}') from e


    def update_template(
        self, template_id: str, data: dict, auth_token: str | None = None
    ) -> dict:
        """Обновить шаблон.

        Args:
            template_id: UUID шаблона.
            data: Данные для обновления.
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.patch(
                    f'{self.base_url}{TEMPLATE_UPDATE_PATCH_URL.format(template_id=template_id)}',
                    json=data,
                    headers=self._get_headers(auth_token)
                )
                
                response.raise_for_status()
                
                result = self._handle_response(response)
                
                if not isinstance(result, dict):
                    raise APIError(f"Expected dict, got {type(result)}")
                
                cache.delete('notifications_templates_list')
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise TemplateNotFoundError(f'Template {template_id} not found') from e
            raise APIError(f'Failed to update template: {e}') from e
        except httpx.HTTPError as e:
            raise APIError(f'Failed to update template: {e}') from e


class APIError(Exception):
    """Ошибка API."""
    pass


class TemplateNotFoundError(APIError):
    """Шаблон не найден."""
    pass


class DuplicateError(APIError):
    """Дубликат шаблона."""
    pass

api_client = NotificationsAPIClient()