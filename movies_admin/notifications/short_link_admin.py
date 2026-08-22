"""Админ-страница для настройки redirect_url коротких ссылок.

Данные хранятся в БД short_links сервиса, управление через API.
"""

import logging

import httpx
from django.conf import settings
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

SHORT_LINKS_API_URL = "http://short-links-service:8000/api/v1"


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
                    f"{SHORT_LINKS_API_URL}/settings/redirect-url/"
                )
                if response.status_code == 200:
                    redirect_url = response.json().get("redirect_url", "")
                else:
                    error_message = f"Ошибка API: {response.status_code}"
        except httpx.HTTPError as e:
            error_message = f"Не удалось подключиться к short-links-service: {e}"

        if request.method == "POST":
            new_url = request.POST.get("redirect_url", "").strip()
            if not new_url:
                error_message = "URL не может быть пустым"
            else:
                try:
                    with httpx.Client(timeout=10.0) as client:
                        response = client.put(
                            f"{SHORT_LINKS_API_URL}/settings/redirect-url/",
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