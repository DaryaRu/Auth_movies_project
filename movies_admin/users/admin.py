import math

from django.contrib import admin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from users.api_client import APIError, UserProfileNotFoundError, api_client
from users.models import User

DEFAULT_PAGE_SIZE = 50
SORTABLE_FIELDS = ("full_name", "email")

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


def _next_sort(current_sort: str, field: str) -> str:
    """Значение параметра sort. Переключается кликом по заголовку поля."""
    return f"-{field}" if current_sort == field else field


def get_auth_token(request) -> str | None:
    """Получить JWT токен из сессии пользователя.

    Токен сохраняется в сессии после аутентификации через auth-сервис.
    """
    return request.session.get("jwt_token") or request.session.get(
        "access_token"
    )


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Только просмотр данных. Данные хранятся в auth-service, а не в локальной таблице User,
    поэтому changelist_view и change_view не используют стандартный Django-рендеринг."""

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
        if not _has_profile_view_permission(request):
            raise PermissionDenied

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

    def changelist_view(self, request, extra_context=None):
        """Список и поиск пользователей из auth-service (email, телефон, ФИО)."""
        if not _has_profile_view_permission(request):
            raise PermissionDenied

        auth_token = get_auth_token(request)
        request_id = request.headers.get("X-Request-Id")
        search_query = request.GET.get("q", "").strip()
        try:
            page_number = max(int(request.GET.get("p", 1)), 1)
        except ValueError:
            page_number = 1

        sort = request.GET.get("sort", "").strip()
        allowed_sorts = {*SORTABLE_FIELDS, *(f"-{f}" for f in SORTABLE_FIELDS)}
        if sort not in allowed_sorts:
            sort = ""

        items: list = []
        total = 0
        page_size = DEFAULT_PAGE_SIZE
        error_message = None
        try:
            result = api_client.list_users(
                auth_token,
                request_id,
                search=search_query or None,
                page_number=page_number,
                page_size=page_size,
                sort=sort or None,
            )
            items = result["items"]
            total = result["total"]
            page_number = result["page_number"]
            page_size = result["page_size"]
        except APIError as e:
            error_message = str(e)

        total_pages = math.ceil(total / page_size) if page_size else 1

        context = {
            "title": _("Users"),
            "items": items,
            "total": total,
            "page_number": page_number,
            "page_size": page_size,
            "total_pages": max(total_pages, 1),
            "search_query": search_query,
            "sort": sort,
            "sort_links": {
                field: _next_sort(sort, field) for field in SORTABLE_FIELDS
            },
            "error_message": error_message,
            "opts": self.model._meta,
            **(extra_context or {}),
            **self.admin_site.each_context(request),
        }
        return TemplateResponse(request, "admin/users/user_list.html", context)
