import http
import logging
from functools import lru_cache
from typing import Any, NamedTuple

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from jose import JWTError, jwt

User = get_user_model()


class LoginResult(NamedTuple):
    """Результат входа для start_login/complete_two_factor_login."""

    user: Any = None
    two_fa_required: bool = False


class CustomBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        """Если у аккаунта включена 2FA по телефону, auth-service вернет
        two_fa_required без токенов, в один шаг завершить вход нельзя,
        метод возвращает None, как при неверном пароле.
        Двухшаговый вход с кодом из СМС через start_login()/complete_two_factor_login(),
        которые вызывает отдельный view.
        """
        if username is None or password is None:
            return None
        return self.start_login(request, username, password).user

    def start_login(self, request, email: str, password: str) -> LoginResult:
        """Первый шаг входа: email с паролем."""
        request_id = request.headers.get("X-Request-Id") if request else None
        data = self._request(
            settings.AUTH_API_LOGIN_URL,
            {"email": email, "password": password},
            request_id,
        )
        if data is None:
            return LoginResult()
        if data.get("two_fa_required"):
            return LoginResult(two_fa_required=True)
        access_token = data.get("access_token")
        if access_token is None:
            logging.error(
                "Login response has neither access_token nor two_fa_required"
            )
            return LoginResult()
        user = self._build_session(request, access_token, email, request_id)
        return LoginResult(user=user)

    def complete_two_factor_login(
        self, request, email: str, code: str
    ) -> LoginResult:
        """Второй шаг входа: код из СМС, отправленный после start_login()."""
        request_id = request.headers.get("X-Request-Id") if request else None
        data = self._request(
            f"{settings.AUTH_API_BASE_URL}/login/verify-phone/",
            {"email": email, "code": code},
            request_id,
        )
        if data is None:
            return LoginResult()
        access_token = data.get("access_token")
        if access_token is None:
            logging.error("Verify-phone response has no access_token")
            return LoginResult()
        user = self._build_session(request, access_token, email, request_id)
        return LoginResult(user=user)

    @staticmethod
    def _request(
        url: str, payload: dict, request_id: str | None
    ) -> dict | None:
        """POST к auth-service. None при сетевой ошибке или ответе не 200."""
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=5,
                headers={"X-Request-Id": request_id or ""},
            )
        except requests.RequestException:
            logging.error(f"Auth API unavailable: {url}")
            return None
        if response.status_code != http.HTTPStatus.OK:
            logging.error(f"Auth API status code - {response.status_code}")
            logging.error(f"Auth API error - {response.text}")
            return None
        return response.json()

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def _build_session(
        self,
        request,
        access_token: str,
        email: str,
        request_id: str | None = None,
    ):
        """Собирает локального Django-пользователя и сохраняет токен и права в
        сессию по полученному access_token.
        Общая часть для обычного входа и для второго шага 2FA-логина.
        """
        public_key = self._get_public_key()
        if public_key is None:
            return None

        try:
            payload = self._get_token_payload(access_token, public_key)
        except (JWTError, AttributeError) as exc:
            logging.error(f"Decode token error: {exc}")
            self._get_public_key.cache_clear()
            public_key = self._get_public_key()
            if public_key is None:
                return None
            try:
                payload = self._get_token_payload(access_token, public_key)
            except Exception as exc:
                logging.error(f"Second decode token failed: {exc}")
                return None

        is_superuser = bool(payload.get("is_superuser"))
        permission_codes = self._get_permission_codes(access_token, request_id)
        if not is_superuser and not permission_codes:
            # Пускаем в админку либо суперпользователя, либо админа,
            # у которого есть хотя бы одно назначенное право.
            # Конкретные права на конкретные разделы (просмотр профилей,
            # редактирование фильмов и т.д.) проверяются уже внутри.
            return None

        user_id = payload["sub"]

        user, _ = User.objects.update_or_create(
            id=user_id,
            defaults={
                "email": email,
                "phone": None,
                "is_superuser": is_superuser,
                "is_staff": True,
                "is_active": True,
            },
        )

        # Сохраняем токен (для последующих API вызовов) и права (чтобы не дергать auth-service заново)
        # в сессию. Обновляются заново при следующем логине.
        if request:
            request.session["access_token"] = access_token
            request.session["permission_codes"] = permission_codes or []
            request.session.modified = True

        return user

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_public_key() -> str | None:
        try:
            response = requests.get(
                settings.AUTH_API_PUBLIC_KEY_URL,
                timeout=5,
            )
        except requests.RequestException:
            logging.error("Public key API unavailable")
            return None
        if response.status_code != http.HTTPStatus.OK:
            logging.error(f"Public key status code - {response.status_code}")
            logging.error(f"Public key error - {response.text}")
            return None

        try:
            data = response.json()
        except ValueError:
            logging.error("Public key response is not valid JSON")
            return None

        public_key = data.get("public_key")
        if not public_key:
            logging.error("Public key field missing in response")
            return None

        return public_key

    @staticmethod
    def _get_token_payload(
        access_token: str, public_key: str
    ) -> dict[str, Any]:
        return jwt.decode(
            access_token,
            public_key,
            algorithms=settings.JWT_ALGORITHM,
        )

    @staticmethod
    def _get_permission_codes(
        access_token: str, request_id: str | None = None
    ) -> list[str] | None:
        """Получение прав пользователя через auth-service (None при ошибке запроса).

        X-Request-Id обязателен на стороне auth-service (иначе вернет 400 без него).
        """
        try:
            response = requests.get(
                f"{settings.AUTH_API_BASE_URL}/users/me/permissions/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Request-Id": request_id or "",
                },
                timeout=5,
            )
        except requests.RequestException:
            logging.error("Auth API unavailable while checking permissions")
            return None
        if response.status_code != http.HTTPStatus.OK:
            logging.error(
                f"Permissions check status code - {response.status_code}"
            )
            return None
        return [p["code"] for p in response.json()]
