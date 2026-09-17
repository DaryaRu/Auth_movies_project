from core.views import admin_login
from django.conf import settings
from django.contrib import admin
from django.urls import path

# Подменяем view логина сайта админки на свою с сдвухшаговым входом:
# пароль, затем код из СМС при включенной 2FA.
admin.site.login = admin_login

urlpatterns = [
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
