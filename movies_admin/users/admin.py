from django.contrib import admin
from django.contrib.auth.models import Group
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from users.api_client import APIError, UserProfileNotFoundError, api_client
from users.models import User

admin.site.unregister(Group)

# Код права, дающего доступ к просмотру личных данных пользователей.
PROFILE_VIEW_PERMISSION_CODE = "user:view_personal_data"


def _has_profile_view_permission(request) -> bool:
    """Суперпользователь может просматривать всегда, а остальные только по наличию права из сессии."""
    if request.user.is_superuser:
        return True
    return PROFILE_VIEW_PERMISSION_CODE in request.session.get(
        "permission_codes", []
    )


def get_auth_token(request) -> str | None:
    """Получить JWT токен из сессии пользователя.

    Токен сохраняется в сессии после аутентификации через auth-сервис.
    """
    return request.session.get("jwt_token") or request.session.get(
        "access_token"
    )


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Только просмотр данных."""

    list_display = (
        "email",
        "phone",
        "is_active",
        "is_staff",
        "is_superuser",
        "created",
    )
    search_fields = ("email", "phone")
    ordering = ("-created",)

    def has_module_permission(self, request):
        return _has_profile_view_permission(request)

    def has_view_permission(self, request, obj=None):
        return _has_profile_view_permission(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Личные данные пользователя из auth-service (email, phone, full_name, timezone)."""
        auth_token = get_auth_token(request)
        request_id = request.headers.get("X-Request-Id")
        profile = None
        error_message = None

        try:
            profile = api_client.get_user_profile(
                str(object_id), auth_token, request_id
            )
        except (UserProfileNotFoundError, APIError) as e:
            error_message = str(e)

        context = {
            "title": _("User profile"),
            "profile": profile,
            "error_message": error_message,
            "object_id": object_id,
            "opts": self.model._meta,
            **self.admin_site.each_context(request),
        }
        return TemplateResponse(
            request, "admin/users/user_change_form.html", context
        )
