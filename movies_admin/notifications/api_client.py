"""API клиент для сервиса нотификаций."""

import httpx
from django.conf import settings
from django.core.cache import cache

TEMPLATES_LIST_GET_URL = "/notifications/templates/"
TEMPLATES_CREATE_POST_URL = "/notifications/templates/"
TEMPLATE_GET_URL = "/notifications/templates/{template_id}/"
TEMPLATE_UPDATE_PATCH_URL = "/notifications/templates/{template_id}/"
TEMPLATE_PREVIEW_POST_URL = "/notifications/templates/{template_id}/preview/"
TEMPLATE_BY_CODE_GET_URL = "/notifications/templates/by-code/{code}/"
NOTIFICATION_TRIGGERS_UPSERT_URL = "/notification-triggers/"
MAILINGS_LIST_URL = "/admin-mailings/"
MAILING_CREATE_URL = "/admin-mailings/"
MAILING_GET_URL = "/admin-mailings/{mailing_id}/"


def _error_detail(response: httpx.Response) -> str:
    """Достать detail из тела ответа FastAPI, если он там есть."""
    try:
        detail = response.json().get("detail")
        if detail:
            return str(detail)
    except (ValueError, AttributeError):
        pass
    return response.text


class NotificationsAPIClient:
    """Клиент для взаимодействия с API сервиса нотификаций.

    Токен авторизации передаётся динамически через заголовок Authorization
    из сессии пользователя в админ-панели.
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = (
            base_url or settings.NOTIFICATIONS_API_BASE_URL
        ).rstrip("/")
        self.timeout = httpx.Timeout(30.0)

    def _get_headers(self, auth_token: str | None = None) -> dict:
        """Получить заголовки для запросов.

        Args:
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET,
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

    def list_templates(self, auth_token: str | None = None) -> list[dict]:
        """Получить список всех шаблонов.

        Args:
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        cache_key = "notifications_templates_list"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}{TEMPLATES_LIST_GET_URL}",
                    headers=self._get_headers(auth_token),
                )
                result = self._handle_response(response)

                if not isinstance(result, list):
                    raise APIError(
                        f"Unexpected response format: expected list, got {type(result)}"
                    )

                cache.set(cache_key, result, 60)
                return result
        except httpx.HTTPError as e:
            raise APIError(f"Failed to list templates: {e}") from e

    def get_template(
        self, template_id: str, auth_token: str | None = None
    ) -> dict:
        """Получить шаблон по ID.

        Args:
            template_id: UUID шаблона.
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}{TEMPLATE_GET_URL.format(template_id=template_id)}",
                    headers=self._get_headers(auth_token),
                )
                result = self._handle_response(response)
                if not isinstance(result, dict):
                    raise APIError(f"Expected dict, got {type(result)}")
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise TemplateNotFoundError(
                    f"Template {template_id} not found"
                ) from e
            raise APIError(f"Failed to get template: {e}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Failed to get template: {e}") from e

    def create_template(
        self, data: dict, auth_token: str | None = None
    ) -> dict:
        """Создать новый шаблон.

        Args:
            data: Данные шаблона.
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}{TEMPLATES_CREATE_POST_URL}",
                    json=data,
                    headers=self._get_headers(auth_token),
                )

                response.raise_for_status()

                result = self._handle_response(response)

                if not isinstance(result, dict):
                    raise APIError(f"Expected dict, got {type(result)}")

                cache.delete("notifications_templates_list")
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                raise DuplicateError("Template already exists") from e
            raise APIError(f"Failed to create template: {e}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Failed to create template: {e}") from e

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
                    f"{self.base_url}{TEMPLATE_UPDATE_PATCH_URL.format(template_id=template_id)}",
                    json=data,
                    headers=self._get_headers(auth_token),
                )

                response.raise_for_status()

                result = self._handle_response(response)

                if not isinstance(result, dict):
                    raise APIError(f"Expected dict, got {type(result)}")

                cache.delete("notifications_templates_list")
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise TemplateNotFoundError(
                    f"Template {template_id} not found"
                ) from e
            raise APIError(f"Failed to update template: {e}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Failed to update template: {e}") from e

    def preview_template(
        self, template_id: str, payload: dict, auth_token: str | None = None
    ) -> dict:
        """Отрендерить шаблон с тестовым payload через сервис нотификаций.

        Args:
            template_id: UUID шаблона.
            payload: Тестовые данные для подстановки в плейсхолдеры.
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}{TEMPLATE_PREVIEW_POST_URL.format(template_id=template_id)}",
                    json={"payload": payload},
                    headers=self._get_headers(auth_token),
                )
                result = self._handle_response(response)
                if not isinstance(result, dict):
                    raise APIError(f"Expected dict, got {type(result)}")
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise TemplateNotFoundError(
                    f"Template {template_id} not found"
                ) from e
            if e.response.status_code == 422:
                raise TemplatePreviewError(_error_detail(e.response)) from e
            raise APIError(f"Failed to preview template: {e}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Failed to preview template: {e}") from e

    def get_template_by_code(
        self, code: str, auth_token: str | None = None
    ) -> dict:
        """Получить шаблон по code (например 'new_episode').

        Args:
            code: Уникальный код шаблона.
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}{TEMPLATE_BY_CODE_GET_URL.format(code=code)}",
                    headers=self._get_headers(auth_token),
                )
                result = self._handle_response(response)
                if not isinstance(result, dict):
                    raise APIError(f"Expected dict, got {type(result)}")
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise TemplateNotFoundError(
                    f"Template with code={code} not found"
                ) from e
            raise APIError(f"Failed to get template by code: {e}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Failed to get template by code: {e}") from e

    def upsert_notification_trigger(
        self,
        content_id: str,
        notification_type: str,
        template_id: str,
        payload: dict,
        auth_token: str | None = None,
    ) -> dict:
        """Создать/обновить триггер уведомления (Scheduled group) по (content_id, notification_type).

        Args:
            content_id: UUID сущности, на изменение которой реагирует уведомление.
            notification_type: Тип уведомления, определяет резолв аудитории воркером.
            template_id: UUID шаблона для рендера.
            payload: Данные для рендера на момент этого изменения.
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}{NOTIFICATION_TRIGGERS_UPSERT_URL}",
                    json={
                        "content_id": content_id,
                        "notification_type": notification_type,
                        "template_id": template_id,
                        "payload": payload,
                    },
                    headers=self._get_headers(auth_token),
                )
                result = self._handle_response(response)
                if not isinstance(result, dict):
                    raise APIError(f"Expected dict, got {type(result)}")
                return result
        except httpx.HTTPError as e:
            raise APIError(f"Failed to upsert notification trigger: {e}") from e

    def list_mailings(self, auth_token: str | None = None) -> list[dict]:
        """Получить список всех рассылок.

        Args:
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        cache_key = "notifications_mailings_list"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}{MAILINGS_LIST_URL}",
                    headers=self._get_headers(auth_token),
                )
                result = self._handle_response(response)

                if not isinstance(result, list):
                    raise APIError(
                        f"Unexpected response format: expected list, got {type(result)}"
                    )

                cache.set(cache_key, result, 60)
                return result
        except httpx.HTTPError as e:
            raise APIError(f"Failed to list mailings: {e}") from e

    def create_mailing(
        self, data: dict, auth_token: str | None = None
    ) -> list[dict]:
        """Создать рассылку.

        Возвращает список рассылок: один элемент — обычная рассылка (сразу),
        несколько — если scheduled_local_datetime разбил аудиторию по
        таймзонам (по одной рассылке на каждую таймзону).

        Args:
            data: Данные рассылки (template_id, audience_filter, payload,
                scheduled_local_datetime, created_by).
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}{MAILING_CREATE_URL}",
                    json=data,
                    headers=self._get_headers(auth_token),
                )

                response.raise_for_status()

                result = self._handle_response(response)

                if not isinstance(result, list):
                    raise APIError(f"Expected list, got {type(result)}")

                cache.delete("notifications_mailings_list")
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise MailingTemplateNotFoundError(
                    _error_detail(e.response)
                ) from e
            if e.response.status_code == 422:
                raise MailingValidationError(
                    _error_detail(e.response)
                ) from e
            raise APIError(f"Failed to create mailing: {e}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Failed to create mailing: {e}") from e

    def get_mailing(self, mailing_id: str, auth_token: str | None = None) -> dict:
        """Получить рассылку по ID.

        Args:
            mailing_id: UUID рассылки.
            auth_token: JWT токен пользователя из auth-сервиса.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}{MAILING_GET_URL.format(mailing_id=mailing_id)}",
                    headers=self._get_headers(auth_token),
                )
                result = self._handle_response(response)
                if not isinstance(result, dict):
                    raise APIError(f"Expected dict, got {type(result)}")
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise MailingNotFoundError(
                    f"Mailing {mailing_id} not found"
                ) from e
            raise APIError(f"Failed to get mailing: {e}") from e
        except httpx.HTTPError as e:
            raise APIError(f"Failed to get mailing: {e}") from e


class APIError(Exception):
    """Ошибка API."""

    pass


class TemplateNotFoundError(APIError):
    """Шаблон не найден."""

    pass


class DuplicateError(APIError):
    """Дубликат шаблона."""

    pass


class TemplatePreviewError(APIError):
    """payload не подходит для рендера шаблона (лишний ключ или не хватает переменной)."""

    pass

class MailingNotFoundError(APIError):
    """Рассылка не найдена."""

    pass


class MailingTemplateNotFoundError(APIError):
    """Шаблон для рассылки не найден или неактивен."""

    pass


class MailingValidationError(APIError):
    """Ошибка валидации рассылки (payload, scheduled_at)."""

    pass


api_client = NotificationsAPIClient()