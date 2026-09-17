from django.contrib.admin.sites import site as admin_site
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import login as auth_login
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from core.backends import CustomBackend

PENDING_2FA_EMAIL_SESSION_KEY = "pending_2fa_email"
PENDING_2FA_NEXT_SESSION_KEY = "pending_2fa_next"
BACKEND_PATH = "core.backends.CustomBackend"


def _safe_next_url(request, raw_next: str | None) -> str | None:
    """Возвращает raw_next (если безопасный локальный редирект), иначе None."""
    if not raw_next:
        return None
    if url_has_allowed_host_and_scheme(
        raw_next,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return raw_next
    return None


def admin_login(request):
    """Вход в movies_admin: пароль, затем код из СМС вторым шагом (если 2FA по
    телефону).

    Состояние ожидания кода из email хранится в анонимной Django-сессии,
    до успешного второго шага django.contrib.auth.login() не вызывается.
    ?restart=1 сбрасывает состояние и возвращает на первый шаг.
    """
    next_url = _safe_next_url(
        request, request.GET.get(REDIRECT_FIELD_NAME)
    ) or reverse("admin:index")

    if request.user.is_authenticated:
        return redirect(next_url)

    if request.GET.get("restart"):
        request.session.pop(PENDING_2FA_EMAIL_SESSION_KEY, None)
        request.session.pop(PENDING_2FA_NEXT_SESSION_KEY, None)
        return redirect(reverse("admin:login"))

    backend = CustomBackend()
    pending_email = request.session.get(PENDING_2FA_EMAIL_SESSION_KEY)
    error_message = None

    if request.method == "POST":
        if pending_email:
            code = request.POST.get("code", "").strip()
            result = backend.complete_two_factor_login(
                request, pending_email, code
            )
            if result.user is not None:
                redirect_to = request.session.get(
                    PENDING_2FA_NEXT_SESSION_KEY, next_url
                )
                del request.session[PENDING_2FA_EMAIL_SESSION_KEY]
                request.session.pop(PENDING_2FA_NEXT_SESSION_KEY, None)
                auth_login(request, result.user, backend=BACKEND_PATH)
                return redirect(redirect_to)
            error_message = (
                "Неверный код или сервис недоступен. Попробуйте еще раз."
            )
        else:
            email = request.POST.get("username", "").strip()
            password = request.POST.get("password", "")
            posted_next = _safe_next_url(
                request, request.POST.get(REDIRECT_FIELD_NAME)
            )
            result = backend.start_login(request, email, password)
            if result.user is not None:
                auth_login(request, result.user, backend=BACKEND_PATH)
                return redirect(posted_next or next_url)
            if result.two_fa_required:
                request.session[PENDING_2FA_EMAIL_SESSION_KEY] = email
                if posted_next:
                    request.session[PENDING_2FA_NEXT_SESSION_KEY] = posted_next
                request.session.modified = True
                pending_email = email
            else:
                error_message = "Неверный email или пароль."

    context = {
        **admin_site.each_context(request),
        "title": "Код из СМС" if pending_email else "Вход",
        "pending_email": pending_email,
        "error_message": error_message,
        REDIRECT_FIELD_NAME: next_url,
    }
    return TemplateResponse(request, "admin/custom_login.html", context)
