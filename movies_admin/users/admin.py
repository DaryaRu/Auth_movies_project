from django.contrib import admin
from django.contrib.auth.models import Group

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
    readonly_fields = (
        "id",
        "email",
        "phone",
        "is_active",
        "is_staff",
        "is_superuser",
        "created",
        "modified",
    )

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
