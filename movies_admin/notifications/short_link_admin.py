"""Админ-страница для настройки redirect_url коротких ссылок.

Данные хранятся в БД short_links сервиса, управление через API.
"""

import logging
import os
from urllib.parse import urlparse

import httpx
from django.conf import settings
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

SHORT_LINKS_SETTINGS_REDIRECT_URL = "/settings/redirect-url/"
SHORT_LINKS_API_URL = "http://short-links-service:8000/api/v1"


class InvalidRedirectUrlError(ValueError):
    """Бросается при валидации недопустимого redirect_url."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def validate_redirect_url(url: str) -> str:
    """Валидирует redirect_url: абсолютный, схема http/https, хост в allowlist.

    Args:
        url: URL для валидации.

    Returns:
        Валидированный URL (без изменений).

    Raises:
        InvalidRedirectUrlError: Если URL не соответствует требованиям.
    """
    if not url:
        raise InvalidRedirectUrlError("redirect_url не может быть пустым")

    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        raise InvalidRedirectUrlError(
            "redirect_url должен быть абсолютным URL (https://...)"
        )

    if parsed.scheme not in ("http", "https"):
        raise InvalidRedirectUrlError(
            f"Недопустимая схема '{parsed.scheme}'. Разрешены: http, https"
        )

    host = parsed.hostname
    if not host:
        raise InvalidRedirectUrlError("redirect_url должен содержать хост")

    allowed_hosts = set()
    allowed_redirect_hosts = os.environ.get("ALLOWED_REDIRECT_HOSTS", "")
    if allowed_redirect_hosts:
        allowed_hosts = {h.strip() for h in allowed_redirect_hosts.split(",") if h.strip()}
    
    if not allowed_hosts:
        allowed_hosts = {os.environ.get("DEFAULT_REDIRECT_HOST", "localhost")}
    
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(
                f"{SHORT_LINKS_API_URL}{SHORT_LINKS_SETTINGS_REDIRECT_URL}",
                headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
                timeout=5,
            )
            if response.status_code == 200:
                allowed_hosts.add(host)
    except httpx.HTTPError:
        pass

    if host.lower() not in allowed_hosts:
        raise InvalidRedirectUrlError(
            f"Хост '{host}' не входит в разрешённый список. "
            f"Разрешены: {', '.join(sorted(allowed_hosts))}"
        )

    return url


class ShortLinkSettingsAdmin(admin.ModelAdmin):
    """Админ-страница для настройки redirect_url коротких ссылок."""

    change_list_template = "admin/notifications/short_link_settings.html"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "settings/",
                self.admin_site.admin_view(self.settings_view),
                name="notifications_shortlinksettings_settings",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        """Перенаправить на страницу настроек."""
        return HttpResponseRedirect(
            reverse("admin:notifications_shortlinksettings_settings")
        )

    def settings_view(self, request):
        """Страница настройки redirect_url."""
        error_message = None
        redirect_url = ""

        # GET текущее значение
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{SHORT_LINKS_API_URL}{SHORT_LINKS_SETTINGS_REDIRECT_URL}",
                    headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
                )
                if response.status_code == 200:
                    redirect_url = response.json().get("redirect_url", "")
                    logger.info(f"Получен redirect_url из API: {redirect_url}")
                else:
                    error_message = f"Ошибка API: {response.status_code}"
                    logger.error(f"Ошибка при получении redirect_url: {error_message}")
        except httpx.HTTPError as e:
            error_message = f"Не удалось подключиться к short-links-service: {e}"
            logger.error(f"Ошибка подключения к short-links-service: {e}")

        if request.method == "POST":
            new_url = request.POST.get("redirect_url", "").strip()
            if not new_url:
                error_message = "URL не может быть пустым"
            else:
                try:
                    validate_redirect_url(new_url)
                except InvalidRedirectUrlError as e:
                    error_message = f"Недопустимый URL: {e.message}"
                else:
                    try:
                        with httpx.Client(timeout=10.0) as client:
                            response = client.put(
                                f"{SHORT_LINKS_API_URL}{SHORT_LINKS_SETTINGS_REDIRECT_URL}",
                                json={"redirect_url": new_url},
                                headers={
                                    "X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET
                                },
                            )
                            if response.status_code == 200:
                                redirect_url = new_url
                                self.message_user(
                                    request,
                                    _("Redirect URL обновлён"),
                                    messages.SUCCESS,
                                )
                            else:
                                error_message = f"Ошибка API: {response.status_code}"
                    except httpx.HTTPError as e:
                        error_message = f"Не удалось обновить: {e}"

        context = {
            "title": _("Настройки коротких ссылок"),
            "redirect_url": redirect_url,
            "error_message": error_message,
            "opts": self.model._meta,
            **self.admin_site.each_context(request),
        }
        return TemplateResponse(
            request,
            "admin/notifications/short_link_settings_form.html",
            context,
        )